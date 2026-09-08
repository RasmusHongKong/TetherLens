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

from .nlg_connector_mechanism import _dedupe_claims, _html_evidence_clauses
from .nlg_declared_compatibility import NLGAdapter as BaseNLGAdapter


_INTERFACE_REF = "lanyard_anchor_d_ring"
_D_RING = r"d[\s-]?ring(?!s\b)"
_D_RING_NP = rf"(?:a|an|one|single|the)\s+(?:[\w®™+.-]+\s+){{0,4}}{_D_RING}"
_LANYARD = r"(?:tool\s+)?lanyards?"

_POSITIVE_RELATIONS = (
    re.compile(
        rf"\b(?P<relation>{_D_RING_NP}\s+for\s+"
        rf"(?:(?:quick\s+and\s+easy|easy|secure|direct)\s+)?"
        rf"{_LANYARD}\s+attachment)\b",
        re.I,
    ),
    re.compile(
        rf"\b(?P<relation>{_D_RING_NP}\s+to\s+"
        rf"(?:attach|connect|clip|hook)\w*\s+(?:a\s+|the\s+|your\s+)?{_LANYARD})\b",
        re.I,
    ),
    re.compile(
        rf"\b(?P<relation>(?:attach|connect|clip|hook)\w*\s+"
        rf"(?:a\s+|the\s+|your\s+)?{_LANYARD}\s+(?:directly\s+)?to\s+{_D_RING_NP})\b",
        re.I,
    ),
)

# V1 materializes one singular target only. Explicit plural D-ring/lanyard wording is
# evidence for a repeated interface set, not permission to collapse that set into one
# anonymous target.
_PLURAL_D_RING_LANYARD = re.compile(
    rf"(?:\bd[\s-]?rings\b[^.!?;]{{0,120}}\b{_LANYARD}\b|"
    rf"\b{_LANYARD}\b[^.!?;]{{0,120}}\bd[\s-]?rings\b)",
    re.I,
)

# Negation is checked only at the local relation boundary. Unrelated wording such as
# ``does not contain metal and utilises a D Ring...`` must not suppress a later
# affirmative interface statement.
_NEGATED_RELATION_PREFIX = re.compile(
    r"(?:"
    r"\b(?:do|does|did|must|should|shall|may|can)\s+not(?:\s+(?:use|using))?|"
    r"\bcannot(?:\s+(?:use|using))?|"
    r"\bnever(?:\s+(?:use|using))?|"
    r"\bavoid(?:\s+(?:use|using))?|"
    r"\b(?:prohibited|forbidden)\s+to"
    r")\s*$",
    re.I,
)
_POST_RELATION_PROHIBITION = re.compile(
    r"^\s*(?:,?\s*(?:but|yet|however)\b)?[^.!?;]{0,80}"
    r"\b(?:"
    r"(?:must|should|shall|may|can)\s+not|"
    r"cannot|can't|"
    r"(?:do|does|did)\s+not|"
    r"never"
    r")\b[^.!?;]{0,60}\b(?:use|attach|connect|clip|hook)\w*\b",
    re.I,
)


class NLGAdapter(BaseNLGAdapter):
    """Add evidence-backed physical form for singular anchor-side D-ring targets.

    The layer deliberately does not upgrade generic rings or plural D-ring sets. It
    emits a concrete anchor-side interface only when first-party wording directly binds
    one singular D-ring to lanyard attachment on an AnchorAttachment product. The
    resulting ``ring_form`` attribute is consumed by the existing generic resolver and
    manufacturer-declared compatibility binder; no SKU-pair rule is introduced here.
    """

    extractor = "nlg.v0.14"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.ANCHOR_ATTACHMENT:
            return claims

        for artifact in artifacts:
            if "json" in artifact.content_type:
                continue
            evidence = _singular_anchor_d_ring_evidence(artifact.body)
            if evidence is None:
                continue
            claims.extend(
                _anchor_d_ring_claims(
                    evidence=evidence,
                    source_url=artifact.url,
                    extractor=self.extractor,
                )
            )

        return _dedupe_claims(claims)


def _singular_anchor_d_ring_evidence(html: str) -> str | None:
    """Return one direct singular D-ring/lanyard relation, failing closed on plural sets."""

    clauses = _html_evidence_clauses(html)
    if any(_PLURAL_D_RING_LANYARD.search(clause) for clause in clauses):
        return None

    for clause in clauses:
        if clause.rstrip().endswith("?"):
            continue
        for pattern in _POSITIVE_RELATIONS:
            match = pattern.search(clause)
            if match is None:
                continue
            if _NEGATED_RELATION_PREFIX.search(clause[: match.start()]):
                continue
            if _POST_RELATION_PROHIBITION.search(clause[match.end() :]):
                continue
            return match.group("relation").strip()
    return None


def _anchor_d_ring_claims(
    *,
    evidence: str,
    source_url: str,
    extractor: str,
) -> list[CandidateClaim]:
    values = (
        ("interface.role", "anchor_attachment_tether_side"),
        ("interface.type", "ring"),
        ("interface.attribute.ring_form", "d_ring"),
    )
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=_INTERFACE_REF,
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
