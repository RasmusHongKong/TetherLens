from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    SourceArtifact,
)

from .nlg_cinch_loop import NLGAdapter as BaseNLGAdapter
from .nlg_connector_mechanism import _dedupe_claims, _html_evidence_clauses


_DECLARATION_REF = "quick_clip_to_d_ring_anchor"
_CONNECTOR_SPEC_REF = "quick_clip"
_CONNECTOR_SPEC_REF_KEY = "connection_compatibility.connector_spec_ref"
_SOURCE_INTERFACE_TYPE_KEY = "connection_compatibility.source_interface_type"
_TARGET_INTERFACE_TYPE_KEY = "connection_compatibility.target_interface_type"
_TARGET_ROLE_KEY = "connection_compatibility.target_role"
_TARGET_RING_FORM_KEY = "connection_compatibility.target_attribute.ring_form"
_ISSUER_MANUFACTURER_KEY = "connection_compatibility.issuer_manufacturer"
_SCOPE_KEY = "connection_compatibility.scope"
_SCOPE = "Quick Clip to D-ring anchor point"


class NLGAdapter(BaseNLGAdapter):
    """Add accepted NLG connector/interface declarations above endpoint semantics.

    This layer does not infer connector-family equivalence or endpoint direction. It
    records only a tightly bound first-party Quick Clip -> D-ring anchor relationship
    as reusable interface primitives. The resulting declaration can later be bound to
    concrete candidate interfaces without creating persistent SKU-pair compatibility.
    """

    extractor = "nlg.v0.13"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))

        for artifact in artifacts:
            evidence = _quick_clip_d_ring_compatibility_evidence(artifact.body)
            if evidence is None:
                continue
            claims.extend(
                _declaration_claims(
                    issuer_manufacturer=identity.manufacturer,
                    evidence=evidence,
                    source_url=artifact.url,
                    extractor=self.extractor,
                )
            )

        return _dedupe_claims(claims)


def _quick_clip_d_ring_compatibility_evidence(text: str) -> str | None:
    """Return one local positive manufacturer Quick Clip -> D-ring assertion."""

    quick_clip = r"Quick\s*Clip(?:s)?\b™?"
    quick_clip_attachment = rf"{quick_clip}\s+Attachment\b"
    d_ring = r"D[\s-]?Ring"

    direct_relation = re.compile(
        rf"\b{quick_clip}\s+"
        rf"(?:can\s+be\s+|is\s+|are\s+)?"
        rf"(?:(?:quickly|easily|securely)\s+(?:and\s+(?:quickly|easily|securely)\s+)*)?"
        rf"attached\s+to\s+(?:an?\s+|the\s+)?{d_ring}\b",
        re.I,
    )
    featuring_relation = re.compile(
        rf"\bFeaturing\s+(?:the\s+)?{quick_clip}\s*,?\s*"
        rf"(?:it|the\s+attachment)\s+can\s+be\s+"
        rf"(?:(?:quickly|easily|securely)\s+(?:and\s+(?:quickly|easily|securely)\s+)*)?"
        rf"attached\s+to\s+(?:an?\s+|the\s+)?{d_ring}\b",
        re.I,
    )
    designed_relation = re.compile(
        rf"\b{quick_clip_attachment}\s+"
        rf"(?:has\s+been\s+|is\s+)?(?:specifically\s+)?designed\s+to\s+"
        rf"(?:securely\s+)?anchor\b.{{0,100}}?\bto\s+"
        rf"(?:an?\s+|the\s+)?{d_ring}(?:\s+style\s+anchor\s+point)?\b",
        re.I,
    )
    negation = re.compile(
        r"\b(?:not|never|cannot|can't|should\s+not|must\s+not|do\s+not|does\s+not|without)\b",
        re.I,
    )

    for clause in _html_evidence_clauses(text):
        if clause.rstrip().endswith("?"):
            continue
        for relation in (direct_relation, featuring_relation, designed_relation):
            match = relation.search(clause)
            if match is None:
                continue
            if negation.search(match.group(0)) is not None:
                continue
            return clause.strip()
    return None


def _declaration_claims(
    *,
    issuer_manufacturer: str,
    evidence: str,
    source_url: str,
    extractor: str,
) -> list[CandidateClaim]:
    values = (
        (_CONNECTOR_SPEC_REF_KEY, _CONNECTOR_SPEC_REF),
        (_SOURCE_INTERFACE_TYPE_KEY, "clip"),
        (_TARGET_INTERFACE_TYPE_KEY, "ring"),
        (_TARGET_ROLE_KEY, "anchor_attachment_tether_side"),
        (_TARGET_RING_FORM_KEY, "d_ring"),
        (_ISSUER_MANUFACTURER_KEY, issuer_manufacturer.strip()),
        (_SCOPE_KEY, _SCOPE),
    )
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.CONNECTION_COMPATIBILITY,
            subject_ref=_DECLARATION_REF,
            property_key=property_key,
            value=value,
            raw_value=evidence,
            source_url=source_url,
            evidence_method="manufacturer_stated",
            extractor=extractor,
            claim_type=ClaimType.DIRECT,
        )
        for property_key, value in values
    ]
