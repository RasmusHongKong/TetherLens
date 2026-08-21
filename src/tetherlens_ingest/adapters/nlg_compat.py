from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from .common import page_text
from .nlg import NLGAdapter as BaseNLGAdapter


class NLGAdapter(BaseNLGAdapter):
    """NLG adapter extension for ToolAttachment applicability and installation constraints.

    The base adapter continues to own primitive product facts and tether topology.
    This layer adds the structured compatibility semantics introduced after the
    attachment-method workstream without coupling those semantics to individual SKUs.
    """

    extractor = "nlg.v0.7"

    def related_sources(self, identity: ProductIdentity, source_artifact: SourceArtifact) -> list[SourceRequest]:
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return []
        if source_artifact.source_type != SourceType.MANUFACTURER_WEBPAGE:
            return []

        requests: list[SourceRequest] = []
        soup = BeautifulSoup(source_artifact.body, "html.parser")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            label = anchor.get_text(" ", strip=True)
            resolved = urljoin(source_artifact.url, href)
            search_text = f"{label} {resolved}".lower()
            if ".pdf" not in search_text:
                continue
            if "product/instructions" not in search_text and "instruction" not in search_text:
                continue
            requests.append(SourceRequest(
                url=resolved,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
                metadata={"role": "product_instructions", "relationship_basis": "page_link"},
            ))

        # NLG currently exposes product instructions under a stable first-party
        # SKU path. Use this as a generic manufacturer-document fallback when the
        # storefront omits the download link from rendered HTML. If the page already
        # supplied the same SKU document with a cache-busting query string, do not
        # fetch it again under the canonical path.
        if identity.sku and re.fullmatch(r"\d{6}", identity.sku):
            instruction_path = f"/hubfs/Product/Instructions/{identity.sku}.pdf"
            if not any(urlsplit(request.url).path == instruction_path for request in requests):
                requests.append(SourceRequest(
                    url=f"https://go.neverletgo.com{instruction_path}",
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    metadata={"role": "product_instructions", "relationship_basis": "manufacturer_sku_path"},
                ))

        return _dedupe_requests(requests)

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return claims

        for artifact in artifacts:
            text = page_text(artifact.body)
            claims.extend(_tool_attachment_constraint_claims(text, artifact.url, self.extractor))

        return _dedupe_claims(claims)


def _tool_attachment_constraint_claims(text: str, url: str, extractor: str) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []

    if category := _angle_grinder_applicability(text):
        claims.append(_constraint_claim(
            "applicable_tool_category_code",
            "angle_grinder",
            category,
            url,
            extractor,
            ConstraintOperator.REQUIRES,
        ))

    if feature := _handle_requirement(text):
        claims.append(_constraint_claim(
            "required_tool_feature_type",
            "handle",
            feature,
            url,
            extractor,
            ConstraintOperator.REQUIRES,
        ))

    if curved := _curved_surface_capability(text):
        claims.append(CandidateClaim(
            property_key="supported_surface_profile",
            value="curved",
            raw_value=curved,
            source_url=url,
            evidence_method="manufacturer_stated",
            extractor=extractor,
            claim_type=ClaimType.DIRECT,
        ))

    if flat := _flat_surface_installation_requirement(text):
        claims.append(_constraint_claim(
            "installation_surface_profile",
            "flat",
            flat,
            url,
            extractor,
            ConstraintOperator.REQUIRES,
        ))

    for condition, raw in _required_surface_conditions(text):
        claims.append(_constraint_claim(
            "required_surface_condition",
            condition,
            raw,
            url,
            extractor,
            ConstraintOperator.REQUIRES,
        ))

    if prohibited := _removable_part_prohibition(text):
        claims.append(_constraint_claim(
            "prohibited_tool_part_type",
            "removable_cover_or_door",
            prohibited,
            url,
            extractor,
            ConstraintOperator.PROHIBITS,
        ))

    if bond_time := _minimum_bond_time_hours(text):
        claims.append(_constraint_claim(
            "minimum_bond_time_h",
            bond_time[0],
            bond_time[1],
            url,
            extractor,
            ConstraintOperator.GTE,
            unit="h",
        ))

    if test_required := _pre_use_attachment_test(text):
        claims.append(_constraint_claim(
            "pre_use_attachment_test_required",
            True,
            test_required,
            url,
            extractor,
            ConstraintOperator.REQUIRES,
        ))

    return claims


def _constraint_claim(
    key: str,
    value: str | float | bool,
    raw: str,
    url: str,
    extractor: str,
    operator: ConstraintOperator,
    unit: str | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        property_key=key,
        value=value,
        unit=unit,
        raw_value=raw,
        source_url=url,
        evidence_method="manufacturer_stated",
        extractor=extractor,
        claim_type=ClaimType.DECLARED_CONSTRAINT,
        constraint_operator=operator,
    )


def _angle_grinder_applicability(text: str) -> str | None:
    # Product titles or related-product cards are not sufficient on their own.
    # Require contextual copy that actually scopes the attachment to angle grinders.
    patterns = (
        r"\b(?:designed|suitable|intended|made)\b.{0,90}\bangle\s+grinders?\b",
        r"\b(?:attach|install|fit)\w*\b.{0,90}\bangle\s+grinders?\b",
        r"\b(?:create|provide)\w*\b.{0,80}\btether\s+point\b.{0,80}\bangle\s+grinders?\b",
    )
    return _first_evidence(text, patterns)


def _handle_requirement(text: str) -> str | None:
    patterns = (
        r"\b(?:bracket|attachment)\b.{0,140}\b(?:attach\w*|secure\w*|fit\w*|install\w*)\b.{0,100}\b(?:side\s+)?handle\b",
        r"\b(?:attach\w*|secure\w*|fit\w*|install\w*)\b.{0,100}\b(?:angle\s+grinder(?:'s)?\s+)?handle\b",
        r"\bangle\s+grinder(?:'s)?\s+handle\b",
    )
    return _first_evidence(text, patterns)


def _curved_surface_capability(text: str) -> str | None:
    patterns = (
        r"\b(?:even\s+)?(?:on|for)\s+curved\s+surfaces?\b",
        r"\bworks?\b.{0,60}\bcurved\s+surfaces?\b",
        r"\bcurved\s+surfaces?\b.{0,60}\b(?:suitable|compatible|works?)\b",
    )
    return _first_evidence(text, patterns)


def _flat_surface_installation_requirement(text: str) -> str | None:
    patterns = (
        r"\b(?:attach|apply|install|place|position)\w*\b.{0,90}\b(?:a\s+)?flat\s+surface\b",
        r"\bflat\s+surface\b.{0,90}\b(?:attach|apply|install|place|position)\w*\b",
    )
    return _first_evidence(text, patterns)


def _required_surface_conditions(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    clean = _first_evidence(text, (
        r"\bsurfaces?\b.{0,80}\b(?:must\s+be|should\s+be|is|are)\s+clean\b",
        r"\bclean\s+(?:the\s+)?(?:tool\s+)?surfaces?\b",
    ))
    if clean:
        out.append(("clean", clean))

    grease_free = _first_evidence(text, (
        r"\b(?:grease[-\s]?free|free\s+(?:from|of)\s+grease)\b",
        r"\bremove\b.{0,50}\bgrease\b",
    ))
    if grease_free:
        out.append(("grease_free", grease_free))
    return out


def _removable_part_prohibition(text: str) -> str | None:
    patterns = (
        r"\b(?:do\s+not|never|must\s+not)\b.{0,180}\b(?:doors?|covers?)\b",
        r"\b(?:doors?|covers?)\b.{0,160}\b(?:can|may)\s+(?:come|be\s+removed|detach)\b",
        r"\bremovable\b.{0,80}\b(?:doors?|covers?|parts?)\b",
    )
    return _first_evidence(text, patterns)


def _minimum_bond_time_hours(text: str) -> tuple[float, str] | None:
    match = re.search(
        r"(?P<raw>\b(?:allow|leave|wait|requires?|takes?)\b.{0,80}?\b(?P<value>\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b.{0,80}?\b(?:bond|adhes|cure|use)\w*\b"
        r"|\b(?P<value2>\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b.{0,80}?\b(?:full(?:y)?\s+)?(?:bond|adhes|cure)\w*\b)",
        text,
        re.I | re.S,
    )
    if not match:
        return None
    value = float(match.group("value") or match.group("value2"))
    return value, re.sub(r"\s+", " ", match.group("raw")).strip()


def _pre_use_attachment_test(text: str) -> str | None:
    patterns = (
        r"\btest\b.{0,100}\b(?:attachment|tether\s+point|d[\s-]?ring)\b.{0,120}\bbefore\b.{0,80}\buse\b",
        r"\bbefore\b.{0,80}\buse\b.{0,120}\btest\b.{0,100}\b(?:attachment|tether\s+point|d[\s-]?ring)\b",
    )
    return _first_evidence(text, patterns)


def _first_evidence(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).strip()
    return None


def _dedupe_requests(requests: list[SourceRequest]) -> list[SourceRequest]:
    seen: set[str] = set()
    out: list[SourceRequest] = []
    for request in requests:
        if request.url in seen:
            continue
        seen.add(request.url)
        out.append(request)
    return out


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
