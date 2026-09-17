from __future__ import annotations

import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import mass_to_kg

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "three_m.v0.2"
_QUICK_SPIN_MANUAL = (
    "https://multimedia.3m.com/mws/media/1300988O/"
    "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
)
_D_RING_CORD_MANUAL = (
    "https://multimedia.3m.com/mws/media/1300990O/"
    "ifu-5903828-python-d-ring-cord-a3-a3-size-instructions-manual.pdf"
)
_QUICK_SPIN_SKUS = frozenset({"1500027", "1500028", "1500029", "1500030"})
_D_RING_CORD_SKUS = frozenset({"1500009"})
_PRODUCT_DETAIL_PATH = re.compile(r"/p/d/(?P<product_id>v\d+)(?:/|$)", re.I)
_PRODUCT_NUMBER = re.compile(
    r"\b3m\s+product\s+(?:number|no\.?)\s*[:#]?\s*(?P<sku>\d+)\b",
    re.I,
)

_SLIDES_ON_HANDLE = re.compile(
    r"\bsimply\s+slides?\s+onto\s+the\s+handle\s+of\s+a\s+tool\b",
    re.I,
)
_QUICK_SPIN_CAPACITY = re.compile(
    r"\bquick\s+spin\s*,?\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>kg|kgs?|lb|lbs?)\s*\([^)]*\)\s*capacity\b",
    re.I,
)
_TIGHT_HANDLE = re.compile(
    r"\bquick\s+spin\s+will\s+fit\s+tightly\s+on\s+a\s+handle\b",
    re.I,
)
_SNUG_FIT_REQUIRED = re.compile(
    r"\b(?:if\s+a\s+snug\s+fit\s+on\s+the\s+tool\s+cannot\s+be\s+secured|"
    r"some\s+force\s+should\s+be\s+necessary\s+to\s+create\s+a\s+snug\s+fit|"
    r"ensure\s+that\s+the\s+quick\s+spin\s+is\s+firmly\s+in\s+place\s+before\s+use)\b",
    re.I,
)
_TAPERED_SURFACE_PROHIBITION = re.compile(
    r"\bnever\s+attach\s+tool\s+lanyards?\s+or\s+attachment\s+points?\s+to\s+a\s+tapered\s+surface\b",
    re.I,
)
_ATTACHMENT_POINT = re.compile(
    r"\b(?:reusable,?\s+)?non[-\s]?(?:metallic|conductive)\s+attachment\s+point"
    r"(?:\s+is\s+needed)?\b",
    re.I,
)

_D_RING_CORD_SELECTION = re.compile(
    r"\bpass\s+the\s+loop\s+end\s+of\s+a\s+d[-\s]?ring\s+cord\s+through\s+a\s+"
    r"pre[-\s]?drilled\s+hole\s+or\s+(?:a\s+)?closed\s+handle\b",
    re.I,
)
_D_RING_CORD_CAPACITY = re.compile(
    r"\bon\s+tools\s+weighing\s+up\s+to\s+(?P<lb>\d+(?:\.\d+)?)\s*lbs?\s*"
    r"\(\s*(?P<kg>\d+(?:\.\d+)?)\s*kg\s*\)",
    re.I,
)
_D_RING_CORD_CINCH = re.compile(
    r"\bpull\s+tightly\s+to\s+cinch\s+and\s+create\s+a\s+secure\s+connection\b",
    re.I,
)
_D_RING_CORD_ATTACHMENT_POINT = re.compile(
    r"\b(?:create|creates?)\s+(?:an?\s+)?(?:instant\s+|quick\s+)?attachment\s+point\b",
    re.I,
)
_D_RING_CORD_TITLE = re.compile(r"\bd[-\s]?ring\s+cord\s+attachment\b", re.I)


class ThreeMAdapter(ManufacturerAdapter):
    """Extract conservative 3M DBI-SALA ToolAttachment semantics.

    Family-specific evidence stays locally scoped. Quick Spin nominal diameter is not
    interpreted as a permitted tool-handle envelope. D-Ring Cord 1500009 uses the
    manufacturer-published closed-handle/pre-drilled-hole topology directly rather than
    an evidence-bound SKU pairing or inferred geometry.
    """

    manufacturer = "3M"

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []

        if (
            identity.sku in _QUICK_SPIN_SKUS
            and _is_verified_quick_spin_primary(identity, source_artifact)
        ):
            return [
                SourceRequest(
                    url=_QUICK_SPIN_MANUAL,
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    metadata={"role": "quick_spin_installation_instructions"},
                )
            ]

        if (
            identity.sku in _D_RING_CORD_SKUS
            and _is_verified_d_ring_cord_primary(identity, source_artifact)
        ):
            return [
                SourceRequest(
                    url=_D_RING_CORD_MANUAL,
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    metadata={"role": "d_ring_cord_installation_instructions"},
                )
            ]

        return []

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []

        if identity.sku in _QUICK_SPIN_SKUS:
            if not any(
                _is_verified_quick_spin_primary(identity, artifact)
                for artifact in artifacts
            ):
                return []
            return _extract_quick_spin_claims(artifacts)

        if identity.sku in _D_RING_CORD_SKUS:
            if not any(
                _is_verified_d_ring_cord_primary(identity, artifact)
                for artifact in artifacts
            ):
                return []
            return _extract_d_ring_cord_claims(identity, artifacts)

        return []


def _extract_quick_spin_claims(artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for artifact in artifacts:
        text = page_text(artifact.body)

        handle = _SLIDES_ON_HANDLE.search(text)
        if handle is not None:
            claims.extend([
                _claim(
                    "attachment_selection_class",
                    "handle_attachment",
                    raw_value=handle.group(0),
                    source_url=artifact.url,
                ),
                _claim(
                    "attachment_method_code",
                    "mechanical_capture",
                    raw_value=handle.group(0),
                    source_url=artifact.url,
                ),
            ])

        # Only an explicit product capacity is normalized. The adjacent nominal
        # diameter remains descriptive evidence and is never emitted as min/max fit.
        capacity = _QUICK_SPIN_CAPACITY.search(text)
        if capacity is not None:
            claims.append(_claim(
                "rated_capacity_kg",
                mass_to_kg(float(capacity.group("value")), capacity.group("unit")),
                unit="kg",
                raw_value=capacity.group(0),
                source_url=artifact.url,
            ))

        secure_fit = _SNUG_FIT_REQUIRED.search(text) or _TIGHT_HANDLE.search(text)
        if secure_fit is not None:
            claims.append(_claim(
                "secure_attachment_fit_required",
                True,
                raw_value=secure_fit.group(0),
                source_url=artifact.url,
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                operator=ConstraintOperator.REQUIRES,
            ))

        tapered = _TAPERED_SURFACE_PROHIBITION.search(text)
        if tapered is not None:
            claims.append(_claim(
                "prohibited_surface_profile",
                "tapered",
                raw_value=tapered.group(0),
                source_url=artifact.url,
                claim_type=ClaimType.DECLARED_CONSTRAINT,
                operator=ConstraintOperator.PROHIBITS,
            ))

        point = _ATTACHMENT_POINT.search(text)
        if point is not None:
            # Quick Spin clearly creates an attachment point, but the reviewed
            # first-party text does not establish a normalized ring/carabiner form.
            claims.append(_claim(
                "interface.role",
                "tool_attachment_tether_side",
                raw_value=point.group(0),
                source_url=artifact.url,
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref="quick_spin_tether_connection",
            ))

    return _dedupe(claims)


def _extract_d_ring_cord_claims(
    identity: ProductIdentity,
    artifacts: list[SourceArtifact],
) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for artifact in artifacts:
        if not _is_verified_d_ring_cord_manual(identity, artifact):
            continue

        text = page_text(artifact.body)

        selection = _D_RING_CORD_SELECTION.search(text)
        if selection is not None:
            claims.append(_claim(
                "attachment_selection_class",
                "captive_feature_attachment",
                raw_value=selection.group(0),
                source_url=artifact.url,
            ))

        capacity = _D_RING_CORD_CAPACITY.search(text)
        if capacity is not None:
            # 3M publishes both units. Retain its explicit SI value rather than
            # deriving a slightly different value by converting the rounded 5 lb label.
            claims.append(_claim(
                "rated_capacity_kg",
                float(capacity.group("kg")),
                unit="kg",
                raw_value=capacity.group(0),
                source_url=artifact.url,
            ))

        cinch = _D_RING_CORD_CINCH.search(text)
        if cinch is not None:
            claims.append(_claim(
                "attachment_method_code",
                "cinch",
                raw_value=cinch.group(0),
                source_url=artifact.url,
            ))

        point = _D_RING_CORD_ATTACHMENT_POINT.search(text)
        title = _D_RING_CORD_TITLE.search(text)
        if point is not None and title is not None:
            claims.extend([
                _claim(
                    "interface.role",
                    "tool_attachment_tether_side",
                    raw_value=point.group(0),
                    source_url=artifact.url,
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref="d_ring_tether_connection",
                ),
                _claim(
                    "interface.type",
                    "ring",
                    raw_value=title.group(0),
                    source_url=artifact.url,
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref="d_ring_tether_connection",
                ),
                _claim(
                    "interface.attribute.ring_form",
                    "d_ring",
                    raw_value=title.group(0),
                    source_url=artifact.url,
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref="d_ring_tether_connection",
                ),
            ])

    return _dedupe(claims)


def _is_verified_quick_spin_primary(
    identity: ProductIdentity,
    artifact: SourceArtifact,
) -> bool:
    if not _is_verified_product_primary(identity, artifact):
        return False

    soup = BeautifulSoup(artifact.body, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        return False
    return re.search(r"\bquick\s+spin\b", " ".join(heading.stripped_strings), re.I) is not None


def _is_verified_d_ring_cord_primary(
    identity: ProductIdentity,
    artifact: SourceArtifact,
) -> bool:
    if not _is_verified_product_primary(identity, artifact):
        return False

    soup = BeautifulSoup(artifact.body, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        return False
    heading_text = " ".join(heading.stripped_strings)
    return (
        re.search(r"\bd[-\s]?ring\b", heading_text, re.I) is not None
        and re.search(r"\bcord\b", heading_text, re.I) is not None
    )


def _is_verified_product_primary(
    identity: ProductIdentity,
    artifact: SourceArtifact,
) -> bool:
    """Require identity evidence from the resolved target 3M product-detail record.

    3M aggregate/category pages can contain several SKUs and product-number labels, so
    finding the expected SKU somewhere in flattened page text is insufficient. Require
    the resolved detail-page key to match the requested product URL, require the primary
    page heading itself to name the expected SKU, and reject pages whose explicit 3M
    product-number labels identify any other record. Family verifiers add their own
    heading semantics above this shared exact-product boundary.
    """

    if artifact.source_type != SourceType.MANUFACTURER_WEBPAGE:
        return False
    if str(artifact.metadata.get("role") or "primary") != "primary":
        return False
    if not identity.sku:
        return False

    requested_detail = _product_detail_key(identity.url)
    resolved_detail = _product_detail_key(artifact.url)
    if requested_detail is None or resolved_detail != requested_detail:
        return False

    soup = BeautifulSoup(artifact.body, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        return False
    heading_text = " ".join(heading.stripped_strings)
    if re.search(rf"(?<!\d){re.escape(identity.sku)}(?!\d)", heading_text) is None:
        return False

    product_numbers = {
        match.group("sku")
        for match in _PRODUCT_NUMBER.finditer(page_text(artifact.body))
    }
    return product_numbers == {identity.sku}


def _is_verified_d_ring_cord_manual(
    identity: ProductIdentity,
    artifact: SourceArtifact,
) -> bool:
    if identity.sku not in _D_RING_CORD_SKUS:
        return False
    if artifact.source_type != SourceType.MANUFACTURER_DOCUMENT:
        return False
    if urlsplit(artifact.url).path != urlsplit(_D_RING_CORD_MANUAL).path:
        return False

    text = page_text(artifact.body)
    return (
        re.search(rf"(?<!\d){re.escape(identity.sku)}(?!\d)", text) is not None
        and _D_RING_CORD_TITLE.search(text) is not None
    )


def _product_detail_key(url: str) -> str | None:
    match = _PRODUCT_DETAIL_PATH.search(urlsplit(url).path)
    return match.group("product_id").lower() if match else None


def _claim(
    property_key: str,
    value,
    *,
    raw_value: str | None,
    source_url: str,
    unit: str | None = None,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
    claim_type: ClaimType = ClaimType.DIRECT,
    operator: ConstraintOperator | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        unit=unit,
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=_EXTRACTOR,
        claim_type=claim_type,
        constraint_operator=operator,
    )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str, str | None, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit,
            claim.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
