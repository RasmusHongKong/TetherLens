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

from .anchor_attachment_common import (
    claim as anchor_claim,
    installation_method_claim,
    installation_path_claim,
)
from .base import ManufacturerAdapter
from .common import page_text


class KleinAdapter(ManufacturerAdapter):
    """Klein adapter for normalized interface and AnchorAttachment facts.

    Tool extraction remains wording/geometry based rather than SKU based. A manufacturer-
    described tether hole is normalized as one captive through-opening. AnchorAttachment
    bucket-hook evidence is likewise normalized only to the explicit hook-on bucket-lip
    family; a published nominal lip size remains a feature class rather than becoming an
    inferred numeric fit envelope.
    """

    manufacturer = "Klein Tools"
    extractor = "klein.v0.3"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type == ProductType.ANCHOR_ATTACHMENT:
            return self._extract_anchor_attachment(artifacts)
        if identity.product_type != ProductType.TOOL:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            tether_hole = _tether_hole_evidence(text)
            if tether_hole is None:
                continue

            subject_ref = "tether_hole"
            claims.extend(
                [
                    self._feature_claim(
                        subject_ref,
                        "feature.kind",
                        "through_opening",
                        tether_hole,
                        artifact.url,
                    ),
                    self._feature_claim(
                        subject_ref,
                        "feature.role",
                        "tether_interface",
                        tether_hole,
                        artifact.url,
                    ),
                    self._feature_claim(
                        subject_ref,
                        "feature.captive_state",
                        "captive",
                        tether_hole,
                        artifact.url,
                    ),
                ]
            )
            if _handle_location(tether_hole):
                claims.append(
                    self._feature_claim(
                        subject_ref,
                        "feature.location_description",
                        "handle",
                        tether_hole,
                        artifact.url,
                    )
                )

        return _dedupe(claims)

    def _extract_anchor_attachment(
        self,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            target = _bucket_lip_evidence(text)
            install = _bucket_hook_installation(text)
            if target is not None and install is not None:
                claims.extend(
                    [
                        installation_method_claim(
                            "hook_on",
                            raw_value=install,
                            source_url=artifact.url,
                            extractor=self.extractor,
                        ),
                        installation_path_claim(
                            "bucket_lip",
                            "anchor_installation.feature_kind",
                            "bucket_lip",
                            raw_value=target,
                            source_url=artifact.url,
                            extractor=self.extractor,
                        ),
                        installation_path_claim(
                            "bucket_lip",
                            "anchor_installation.attribute.nominal_lip_size",
                            "3_in",
                            raw_value=target,
                            source_url=artifact.url,
                            extractor=self.extractor,
                        ),
                    ]
                )

            tether_point = _BUCKET_TETHER_POINT.search(text)
            if tether_point is not None:
                claims.append(
                    anchor_claim(
                        "interface.role",
                        "anchor_attachment_tether_side",
                        raw_value=tether_point.group(0),
                        source_url=artifact.url,
                        extractor=self.extractor,
                        subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                        subject_ref="bucket_hook_tether_connection",
                    )
                )

        return _dedupe(claims)

    def _feature_claim(
        self,
        subject_ref: str,
        property_key: str,
        value: str,
        raw_value: str,
        source_url: str,
    ) -> CandidateClaim:
        return CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref=subject_ref,
            property_key=property_key,
            value=value,
            raw_value=raw_value,
            source_url=source_url,
            evidence_method="manufacturer_stated",
            extractor=self.extractor,
            claim_type=ClaimType.DIRECT,
        )


_BUCKET_LIP_SIZE = re.compile(
    r"\b3[-\s]?Inch\s*\(\s*7\.6\s*cm\s*\)\s+lip\s+aerial\s+buckets?\b",
    re.I,
)
_BUCKET_HOOK_ATTACH = re.compile(
    r"\b(?:easily\s+)?attaching\s+the\s+hook\s+to\s+(?:a\s+)?3[-\s]?Inch\s*"
    r"\(\s*7\.6\s*cm\s*\)\s+lip\s+aerial\s+bucket\b",
    re.I,
)
_BUCKET_HOOK_ATTACHES = re.compile(
    r"\b(?:quickly\s+)?attaches\s+to\s+(?:standard\s+)?3[-\s]?Inch\s*"
    r"\(\s*7\.6\s*cm\s*\)\s+lip\s+aerial\s+buckets?\b",
    re.I,
)
_BUCKET_TETHER_POINT = re.compile(r"\btether(?:\s+rated)?\s+attachment\s+point\b", re.I)


def _bucket_lip_evidence(text: str) -> str | None:
    match = _BUCKET_LIP_SIZE.search(text)
    return match.group(0) if match is not None else None


def _bucket_hook_installation(text: str) -> str | None:
    for pattern in (_BUCKET_HOOK_ATTACH, _BUCKET_HOOK_ATTACHES):
        match = pattern.search(text)
        if match is not None:
            return match.group(0)
    return None


def _tether_hole_evidence(text: str) -> str | None:
    """Return affirmative tether-hole evidence within one statement boundary."""

    statement_gap = r"[^.!?;\n]"
    patterns = (
        rf"{statement_gap}{{0,80}}\b(?:integrated|built[-\s]?in|dedicated)?\s*tether(?:ing)?\s+hole\b{statement_gap}{{0,100}}",
        rf"{statement_gap}{{0,80}}\bhole\b{statement_gap}{{0,50}}\bfor\s+(?:tool\s+)?tether(?:ing)?\b{statement_gap}{{0,100}}",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        evidence = re.sub(r"\s+", " ", match.group(0)).strip()
        if _negates_tether_hole_statement(evidence):
            continue
        return evidence
    return None


def _negates_tether_hole_statement(evidence: str) -> bool:
    """Reject explicit absence without treating unrelated negative wording as negation."""

    tether_feature = (
        r"(?:tether(?:ing)?\s+hole|"
        r"hole[^.!?;\n]{0,40}\bfor\s+(?:tool\s+)?tether(?:ing)?)"
    )
    modifier = r"(?:an?\s+|any\s+)?(?:integrated\s+|built[-\s]?in\s+|dedicated\s+)?"
    negations = (
        rf"\b(?:does?|did)(?:\s+not|n't)\s+"
        rf"(?:have|include|feature|incorporate|provide|contain)\s+{modifier}{tether_feature}\b",
        rf"\b(?:has|have|had|includes?|features?|incorporates?|provides?|contains?)\s+"
        rf"no\s+{modifier}{tether_feature}\b",
        rf"\bwithout\s+{modifier}{tether_feature}\b",
        rf"\bno\s+{modifier}{tether_feature}\b",
        rf"\bnot\s+(?:equipped|fitted|supplied|provided)\s+with\s+"
        rf"{modifier}{tether_feature}\b",
        rf"\b{tether_feature}\b\s*(?::|=|-)?\s*"
        rf"(?:no|none|false|absent|not\s+(?:available|present|provided|included)|n/?a)\b",
        rf"\b{tether_feature}\b[^.!?;\n]{{0,20}}\b(?:is\s+)?not\s+"
        rf"(?:available|present|provided|included)\b",
    )
    return any(re.search(pattern, evidence, re.I) for pattern in negations)


def _handle_location(evidence: str) -> bool:
    """Require the tether-hole phrase itself to be explicitly located in the handle."""

    tether_hole = r"tether(?:ing)?\s+hole"
    direct_location = (
        rf"\b{tether_hole}\b\s+(?:is\s+)?(?:located\s+)?(?:in|on|within|through)\s+(?:the\s+)?handle\b",
        rf"\b(?:an?\s+)?{tether_hole}\b\s+(?:is\s+)?(?:built|integrated|formed|provided)\s+(?:in|into|on|within|through)\s+(?:the\s+)?handle\b",
        rf"\bhandle\b\s+(?:has|includes?|incorporates?|features?)\s+(?:an?\s+)?(?:integrated\s+|built[-\s]?in\s+)?{tether_hole}\b",
    )
    return any(re.search(pattern, evidence, re.I) for pattern in direct_location)


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_ref, claim.property_key, str(claim.value))
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
