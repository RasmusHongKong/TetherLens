from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)

from .nlg_connector_mechanism import (
    NLGAdapter as BaseNLGAdapter,
    _dedupe_claims,
    _html_evidence_clauses,
)


_ENGAGEMENT_METHOD_KEY = "connector.attribute.engagement_method"
_CINCH = "cinch"
_DEFAULT_CINCH_LOOP_SPEC_REF = "cinch_loop"


class NLGAdapter(BaseNLGAdapter):
    """Add evidence-backed cinching-loop endpoint semantics above the NLG stack.

    ``loop`` remains the tether endpoint form. A separate connector-spec attribute
    records that accepted manufacturer evidence identifies cinching as the endpoint's
    engagement method. The adapter does not infer that every loop cinches, that every
    closed target is compatible, or that a successful field check is catalogue proof.
    """

    extractor = "nlg.v0.12"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TETHER:
            return claims

        loop_endpoint_refs = sorted(
            {
                claim.subject_ref
                for claim in claims
                if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
                and claim.property_key == "connection_point.interface_type"
                and claim.value == "loop"
            }
        )
        # Do not broadcast one cinching statement across multiple loop endpoints whose
        # individual mechanism identity has not been established.
        if len(loop_endpoint_refs) != 1:
            return claims

        loop_endpoint_ref = loop_endpoint_refs[0]
        existing_spec_refs = {
            str(claim.value)
            for claim in claims
            if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
            and claim.subject_ref == loop_endpoint_ref
            and claim.property_key == "connection_point.connector_spec_ref"
        }
        if len(existing_spec_refs) > 1:
            return claims
        connector_spec_ref = (
            next(iter(existing_spec_refs))
            if existing_spec_refs
            else _DEFAULT_CINCH_LOOP_SPEC_REF
        )

        evidence: tuple[str, str] | None = None
        for artifact in artifacts:
            if clause := _cinch_loop_evidence(artifact.body):
                evidence = (clause, artifact.url)
                break
        if evidence is None:
            return claims

        raw_value, source_url = evidence
        if not existing_spec_refs:
            claims.append(
                CandidateClaim(
                    subject_type=ClaimSubjectType.TETHER_CONNECTION_POINT,
                    subject_ref=loop_endpoint_ref,
                    property_key="connection_point.connector_spec_ref",
                    value=connector_spec_ref,
                    raw_value=raw_value,
                    source_url=source_url,
                    evidence_method="manufacturer_stated",
                    extractor=self.extractor,
                    claim_type=ClaimType.DIRECT,
                )
            )

        claims.append(
            CandidateClaim(
                subject_type=ClaimSubjectType.CONNECTOR_SPEC,
                subject_ref=connector_spec_ref,
                property_key=_ENGAGEMENT_METHOD_KEY,
                value=_CINCH,
                raw_value=raw_value,
                source_url=source_url,
                evidence_method="manufacturer_stated",
                extractor=self.extractor,
                claim_type=ClaimType.DIRECT,
            )
        )
        return _dedupe_claims(claims)


def _cinch_loop_evidence(html: str) -> str | None:
    """Return a locally bound positive assertion that the tether loop itself cinches."""

    loop_subject = (
        r"\b(?:rugged\s+|tough\s+|durable\s+|ultra[-\s]?durable\s+)?"
        r"(?:(?:climbing\s+cord|dyneema®?|cord|webbing)\s+)?loop\b"
    )
    relation = re.compile(
        rf"(?:"
        rf"\bcinching\s+{loop_subject}"
        rf"|{loop_subject}\s+(?:allows?|enables?|provides?|supports?|facilitates?)\s+"
        rf"(?:(?:quick|easy|secure|safe|simple)(?:\s+and\s+(?:quick|easy|secure|safe|simple))?\s+)*"
        rf"\bcinching\b"
        rf"|{loop_subject}\s+(?:can\s+be\s+|is\s+)?cinched\b"
        rf"|{loop_subject}\s+cinches\b"
        rf")",
        re.I,
    )

    for clause in _html_evidence_clauses(html):
        if clause.rstrip().endswith("?"):
            continue
        match = relation.search(clause)
        if match is None or _relation_is_locally_negated(clause, match.start()):
            continue
        return clause.strip()
    return None


def _relation_is_locally_negated(clause: str, relation_start: int) -> bool:
    """Reject nearby explicit negation without widening into general NLP inference."""

    prefix = clause[max(0, relation_start - 64) : relation_start]
    negation = re.compile(
        r"(?:\b(?:not|never|no|cannot)\b|"
        r"\b(?:isn|aren|wasn|weren|doesn|don|can)['’]?t\b)"
        r"(?:\s+\w+){0,3}\s*$",
        re.I,
    )
    return negation.search(prefix) is not None
