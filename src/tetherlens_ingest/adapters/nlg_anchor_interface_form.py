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
_D_RING_NP = rf"(?:a|an|one|single|the|this|its)\s+(?:[\w®™+.-]+\s+){{0,4}}{_D_RING}"
_REFERENTIAL_D_RING_NP = rf"(?:the|this|its)\s+(?:[\w®™+.-]+\s+){{0,4}}{_D_RING}"
_LANYARD = r"(?:tool\s+)?lanyards?"
_AFFIRMATIVE_PROVISION = (
    r"(?:"
    r"utili[sz](?:e|es)|"
    r"features?|includes?|incorporates?|provides?|has|"
    r"comes?\s+with|is\s+equipped\s+with"
    r")"
)

# A noun phrase such as ``a D Ring for lanyard attachment`` is not sufficient by
# itself: it can sit under denial or an external requirement. These provision shapes
# therefore include the governing affirmative verb in the match. Direct use wording is
# kept separate and requires a referential target rather than an arbitrary ``a D Ring``.
_POSITIVE_RELATIONS = (
    re.compile(
        rf"\b(?P<relation>{_AFFIRMATIVE_PROVISION}\s+{_D_RING_NP}\s+for\s+"
        rf"(?:(?:quick\s+and\s+easy|easy|secure|direct)\s+)?"
        rf"{_LANYARD}\s+attachment)\b",
        re.I,
    ),
    re.compile(
        rf"\b(?P<relation>{_AFFIRMATIVE_PROVISION}\s+{_D_RING_NP}\s+to\s+"
        rf"(?:attach|connect|clip|hook)\w*\s+(?:a\s+|the\s+|your\s+)?{_LANYARD})\b",
        re.I,
    ),
    re.compile(
        rf"\b(?P<relation>(?:attach|connect|clip|hook)\w*\s+"
        rf"(?:a\s+|the\s+|your\s+)?{_LANYARD}\s+(?:directly\s+)?to\s+"
        rf"{_REFERENTIAL_D_RING_NP})\b",
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

# Polarity is checked against the local predicate prefix, not the whole clause. That
# preserves a later coordinated positive predicate (``requires no drilling and includes
# a D Ring...``) while rejecting ``does not include...`` and ``can't attach...``.
_NEGATED_RELATION_PREFIX = re.compile(
    r"(?:"
    r"\b(?:do|does|did|must|should|shall|may|can)\s+not(?:\s+(?:use|using))?|"
    r"\b(?:don't|doesn't|didn't|can't|couldn't|shouldn't|mustn't|won't|wouldn't)|"
    r"\bcannot(?:\s+(?:use|using))?|"
    r"\bnever(?:\s+(?:use|using))?|"
    r"\bavoid(?:\s+(?:use|using))?|"
    r"\b(?:is|are|was|were)\s+not\s+(?:permitted|allowed|safe)\s+to|"
    r"\b(?:prohibited|forbidden)\s+to"
    r")\s*$",
    re.I,
)

# Reject a provision/use relation when its local governor explicitly frames another
# item as required. This is intentionally bounded to the current predicate span so an
# unrelated earlier requirement does not suppress a later affirmative coordinated
# provision claim.
_EXTERNAL_REQUIREMENT_PREFIX = re.compile(
    r"\b(?:requires?|needs?|depends?\s+on|must\s+(?:have|include|use)|"
    r"(?:used|works?|compatible)\s+with)\b[^.!?;]{0,80}$",
    re.I,
)

_POST_RELATION_PROHIBITION = re.compile(
    r"(?:"
    r"^\s*(?:,?\s*(?:but|yet|however)\b)?[^.!?;]{0,80}"
    r"\b(?:"
    r"(?:must|should|shall|may|can)\s+not|"
    r"cannot|can't|"
    r"(?:do|does|did)\s+not|"
    r"never"
    r")\b[^.!?;]{0,60}\b(?:use|attach|connect|clip|hook)\w*\b"
    r"|^\s*(?:,?\s*)?(?:should|must)\s+be\s+(?:avoided|prohibited|forbidden)\b"
    r")",
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
            local_prefix = _local_predicate_prefix(clause[: match.start()])
            if _NEGATED_RELATION_PREFIX.search(local_prefix):
                continue
            if _EXTERNAL_REQUIREMENT_PREFIX.search(local_prefix):
                continue
            if _POST_RELATION_PROHIBITION.search(clause[match.end() :]):
                continue
            return match.group("relation").strip()
    return None


def _local_predicate_prefix(prefix: str) -> str:
    """Return the prefix owned by the current coordinated predicate.

    ``and``/``but`` delimit a new coordinated predicate for the narrow purposes of the
    polarity/requirement guard. Strong punctuation is already split by the shared HTML
    clause renderer; the final segment is enough to distinguish ``requires X that
    includes...`` from ``requires no drilling and includes...``.
    """

    parts = re.split(r"\b(?:and|but)\b", prefix, flags=re.I)
    return parts[-1].strip(" ,")


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
