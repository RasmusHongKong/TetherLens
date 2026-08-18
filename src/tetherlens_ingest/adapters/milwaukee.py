from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import quote, urljoin

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import mass_to_kg, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class MilwaukeeAdapter(ManufacturerAdapter):
    manufacturer = "Milwaukee"
    extractor = "milwaukee.v0.5"
    recursive_related_sources = True

    def related_sources(self, identity: ProductIdentity, source_artifact: SourceArtifact) -> list[SourceRequest]:
        if identity.product_type != ProductType.TOOL or not identity.sku:
            return []
        if source_artifact.source_type == SourceType.SECONDARY_WEBPAGE:
            return []

        role = str(source_artifact.metadata.get("role") or "primary")
        requests: list[SourceRequest] = []

        if role == "primary":
            requests.extend(self._discover_same_family_kits(identity, source_artifact))
            requests.extend(self._qualified_secondary_requests(identity.sku, "secondary_tool_mass", "self"))
        elif role == "kit":
            kit_sku = str(source_artifact.metadata.get("kit_sku") or "")
            battery_skus = _verified_kit_battery_skus(identity.sku, kit_sku, source_artifact.body)
            for battery_sku in battery_skus:
                requests.append(SourceRequest(
                    url=urljoin(source_artifact.url, f"/Products/{battery_sku}"),
                    metadata={
                        "role": "battery",
                        "battery_model": battery_sku,
                        "relationship_basis": "kit_composition",
                        "kit_sku": kit_sku,
                    },
                ))
                requests.extend(self._qualified_secondary_requests(
                    battery_sku,
                    "secondary_battery_mass",
                    battery_sku,
                    relationship_basis="kit_composition",
                    kit_sku=kit_sku,
                ))
        elif role == "battery":
            battery_sku = str(source_artifact.metadata.get("battery_model") or "")
            if battery_sku:
                requests.extend(self._qualified_secondary_requests(
                    battery_sku,
                    "secondary_battery_mass",
                    battery_sku,
                    relationship_basis=str(source_artifact.metadata.get("relationship_basis") or "manufacturer_product"),
                    kit_sku=str(source_artifact.metadata.get("kit_sku") or ""),
                ))

        return _dedupe_requests(requests)

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []

        for artifact in artifacts:
            text = page_text(artifact.body)
            role = str(artifact.metadata.get("role") or "primary")

            if role == "primary":
                if identity.sku and _contains_exact_sku(artifact.body, identity.sku):
                    claims.append(self._claim(
                        "manufacturer_item_code", identity.sku, None, identity.sku, artifact.url,
                    ))
                if re.search(r"\bM18\b", text, re.I):
                    claims.append(self._claim("battery_platform", "M18", None, "M18", artifact.url))
                if raw_mass := _extract_tool_mass(text):
                    if q := parse_mass(raw_mass):
                        claims.append(self._claim(
                            "tool_body_mass_kg", q.value, "kg", raw_mass, artifact.url,
                        ))
                continue

            if role == "battery":
                battery_sku = str(artifact.metadata.get("battery_model") or "battery")
                if raw_mass := _extract_battery_mass(text):
                    if q := parse_mass(raw_mass):
                        claims.append(self._claim(
                            "battery_mass_kg", q.value, "kg", raw_mass, artifact.url,
                            ClaimSubjectType.RELATED_PRODUCT, battery_sku,
                        ))
                continue

            if artifact.source_type != SourceType.SECONDARY_WEBPAGE:
                continue

            requested_sku = str(artifact.metadata.get("requested_sku") or "")
            if not _is_verified_secondary_detail(artifact, requested_sku):
                continue

            if role == "secondary_tool_mass":
                raw_mass = _extract_tool_mass(text)
                if raw_mass and (q := _parse_mass_with_label_unit(raw_mass)):
                    claims.append(self._claim(
                        "tool_body_mass_kg", q, "kg", raw_mass, artifact.url,
                        evidence_method="qualified_secondary_exact_sku",
                    ))
            elif role == "secondary_battery_mass":
                raw_mass = _extract_battery_mass(text)
                if raw_mass and (q := _parse_mass_with_label_unit(raw_mass)):
                    claims.append(self._claim(
                        "battery_mass_kg", q, "kg", raw_mass, artifact.url,
                        ClaimSubjectType.RELATED_PRODUCT,
                        str(artifact.metadata.get("subject_ref") or requested_sku),
                        evidence_method="qualified_secondary_exact_sku",
                    ))

        claims = _dedupe_claims(claims)
        body_claims = [
            c for c in claims
            if c.property_key == "tool_body_mass_kg" and c.subject_ref == "self"
        ]
        body_claim = _unambiguous_preferred_from(body_claims)

        batteries: dict[str, list[CandidateClaim]] = defaultdict(list)
        for claim in claims:
            if claim.property_key == "battery_mass_kg":
                batteries[claim.subject_ref].append(claim)

        if body_claim:
            for battery_ref, battery_claims in batteries.items():
                battery_claim = _unambiguous_preferred_from(battery_claims)
                if battery_claim is None:
                    continue
                evidence_urls = list(dict.fromkeys([body_claim.source_url, battery_claim.source_url]))
                evidence_method = (
                    "derived_cross_source"
                    if any(c.evidence_method == "qualified_secondary_exact_sku" for c in (body_claim, battery_claim))
                    else "derived"
                )
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
                    subject_ref=f"{identity.sku or identity.model or 'tool'}+{battery_ref}",
                    property_key="operational_mass_kg",
                    value=round(float(body_claim.value) + float(battery_claim.value), 6),
                    unit="kg",
                    raw_value=f"{body_claim.raw_value} tool body + {battery_claim.raw_value} battery",
                    source_url=identity.url,
                    supporting_source_urls=evidence_urls,
                    evidence_method=evidence_method,
                    extractor=self.extractor,
                ))

        return _dedupe_claims(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations: list[AcquisitionObservation] = []
        kit_artifacts = [a for a in artifacts if a.metadata.get("role") == "kit"]
        battery_artifacts = [a for a in artifacts if a.metadata.get("role") == "battery"]
        secondary_artifacts = [a for a in artifacts if a.source_type == SourceType.SECONDARY_WEBPAGE]

        if kit_artifacts:
            observations.append(AcquisitionObservation(
                code="RELATED_KIT_SOURCES_DISCOVERED",
                value=len(kit_artifacts),
                detail="Milwaukee same-family kit sources were traversed from first-party product references.",
                source_url=identity.url,
                extractor=self.extractor,
            ))

        battery_models = sorted({str(a.metadata.get("battery_model")) for a in battery_artifacts if a.metadata.get("battery_model")})
        if battery_models:
            observations.append(AcquisitionObservation(
                code="BATTERY_RELATIONSHIP_DISCOVERED",
                value=len(battery_models),
                detail="Compatible battery identities were established from verified Milwaukee kit contents.",
                source_url=identity.url,
                extractor=self.extractor,
            ))

        verified_secondary = 0
        for artifact in secondary_artifacts:
            requested_sku = str(artifact.metadata.get("requested_sku") or "")
            if _is_verified_secondary_detail(artifact, requested_sku):
                verified_secondary += 1
            else:
                observations.append(AcquisitionObservation(
                    code="SECONDARY_IDENTITY_UNVERIFIED",
                    value=requested_sku or None,
                    detail="Secondary evidence was ignored because it was not a verified exact-SKU product-detail page.",
                    source_url=artifact.url,
                    extractor=self.extractor,
                ))

            if artifact.metadata.get("role") == "secondary_battery_mass":
                text = page_text(artifact.body)
                if re.search(r"Shipping Weight", text, re.I) and _extract_battery_mass(text) is None:
                    observations.append(AcquisitionObservation(
                        code="SECONDARY_NON_PRODUCT_MASS_IGNORED",
                        value=requested_sku or None,
                        detail="A shipping-weight value was present but was not accepted as installed battery mass.",
                        source_url=artifact.url,
                        extractor=self.extractor,
                    ))

        if verified_secondary:
            observations.append(AcquisitionObservation(
                code="QUALIFIED_SECONDARY_SOURCES_VERIFIED",
                value=verified_secondary,
                detail="Secondary product-detail pages passed exact-SKU identity verification before physical facts were accepted.",
                source_url=identity.url,
                extractor=self.extractor,
            ))

        primary = artifacts[0] if artifacts else None
        if primary and re.search(r"Specs\s*Loading", page_text(primary.body), re.I):
            observations.append(AcquisitionObservation(
                code="DYNAMIC_SPECS_DETECTED",
                value=True,
                detail="The first-party page exposes a dynamically loaded Specs block; other graph sources may resolve required facts.",
                source_url=primary.url,
                extractor=self.extractor,
            ))
        return observations

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue]:
        issues: list[ReadinessIssue] = []
        if not any(c.property_key == "tool_body_mass_kg" for c in claims):
            issues.append(ReadinessIssue(code="MISSING_TOOL_BODY_MASS", property_key="tool_body_mass_kg"))
        if not any(c.property_key == "battery_mass_kg" for c in claims):
            issues.append(ReadinessIssue(code="MISSING_BATTERY_MASS", property_key="battery_mass_kg"))
        if not any(c.property_key == "operational_mass_kg" for c in claims):
            issues.append(ReadinessIssue(code="MISSING_OPERATIONAL_MASS", property_key="operational_mass_kg"))

        tool_claims = [
            c for c in claims
            if c.property_key == "tool_body_mass_kg" and c.subject_ref == "self"
        ]
        if _has_conflicting_values(tool_claims):
            issues.append(ReadinessIssue(
                code="CONFLICTING_PHYSICAL_FACTS",
                property_key="tool_body_mass_kg",
                detail="Qualified tool-body mass sources disagree; no operational profile is derived until reconciled.",
            ))

        battery_claims: dict[str, list[CandidateClaim]] = defaultdict(list)
        for claim in claims:
            if claim.property_key == "battery_mass_kg":
                battery_claims[claim.subject_ref].append(claim)
        for battery_ref, grouped_claims in battery_claims.items():
            if _has_conflicting_values(grouped_claims):
                issues.append(ReadinessIssue(
                    code="CONFLICTING_PHYSICAL_FACTS",
                    property_key="battery_mass_kg",
                    detail=f"Qualified battery mass sources disagree for {battery_ref}; that profile is not derived until reconciled.",
                ))
        return issues

    @classmethod
    def _claim(
        cls,
        key: str,
        value,
        unit: str | None,
        raw: str | None,
        url: str,
        subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
        subject_ref: str = "self",
        evidence_method: str = "manufacturer_stated",
    ) -> CandidateClaim:
        return CandidateClaim(
            subject_type=subject_type,
            subject_ref=subject_ref,
            property_key=key,
            value=value,
            unit=unit,
            raw_value=raw,
            source_url=url,
            evidence_method=evidence_method,
            extractor=cls.extractor,
        )

    @staticmethod
    def _qualified_secondary_requests(
        sku: str,
        role: str,
        subject_ref: str,
        **metadata,
    ) -> list[SourceRequest]:
        common = {
            "role": role,
            "requested_sku": sku,
            "subject_ref": subject_ref,
            "evidence_page_kind": "product_detail",
            **{k: v for k, v in metadata.items() if v},
        }
        return [
            SourceRequest(
                url=f"https://thepowertoolstore.com/products/milwaukee-{quote(sku)}",
                source_type=SourceType.SECONDARY_WEBPAGE,
                metadata={**common, "publisher": "The Power Tool Store"},
            ),
        ]

    @staticmethod
    def _discover_same_family_kits(identity: ProductIdentity, artifact: SourceArtifact) -> list[SourceRequest]:
        if not identity.sku:
            return []
        family = identity.sku.split("-", 1)[0]
        candidates = sorted(set(re.findall(rf"\b{re.escape(family)}-\d{{2}}[A-Z]{{0,3}}\b", artifact.body, re.I)))
        requests = []
        for sku in candidates:
            sku = sku.upper()
            if sku == identity.sku.upper():
                continue
            requests.append(SourceRequest(
                url=urljoin(artifact.url, f"/Products/{sku}"),
                metadata={
                    "role": "kit",
                    "kit_sku": sku,
                    "relationship_basis": "first_party_product_reference",
                },
            ))
        return requests


def _contains_exact_sku(body: str, sku: str) -> bool:
    return bool(re.search(rf"(?<![A-Z0-9]){re.escape(sku)}(?![A-Z0-9])", body, re.I))


def _verified_kit_battery_skus(tool_sku: str, kit_sku: str, body: str) -> list[str]:
    if not kit_sku or not _contains_exact_sku(body, kit_sku):
        return []
    contents = _kit_contents_text(body)
    if not contents or not _contains_exact_sku(contents, tool_sku):
        return []
    return sorted({sku.upper() for sku in re.findall(r"\b48-11-\d{4}\b", contents, re.I)})


def _kit_contents_text(body: str) -> str | None:
    text = page_text(body)
    start = re.search(r"(?:^|\n)In The Box(?:\s*\(\d+\))?(?:\n|$)", text, re.I)
    if not start:
        return None
    remainder = text[start.end():]
    stop = re.search(r"(?:^|\n)(?:Specs|Product Overview|Features|Reviews|Additional Resources)(?:\n|$)", remainder, re.I)
    return remainder[:stop.start()] if stop else remainder[:5000]


def _is_verified_secondary_detail(artifact: SourceArtifact, requested_sku: str) -> bool:
    return bool(
        requested_sku
        and artifact.metadata.get("evidence_page_kind") == "product_detail"
        and _contains_exact_sku(artifact.body, requested_sku)
    )


def _extract_tool_mass(text: str) -> str | None:
    for pattern in (
        r"\bNet Tool Weight\b(?:\s*\(lbs?\))?.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b|\d+(?:\.\d+)?)",
        r"\bTool Weight\b.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
        r"\bTool Body Weight\b.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
        r"\bWeight\s*:?\s*(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)\s*\(Tool Only\)",
        r"\bProduct Weight\b.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
        r"\bProduct Weight\s*\(lb\.?\)\s*[:|\n]?\s*(\d+(?:\.\d+)?)\b",
    ):
        m = re.search(pattern, text, re.I | re.S)
        if m:
            value = m.group(1).strip()
            if re.search(r"\b(?:kg|kgs?|lb|lbs?|g)\b", value, re.I):
                return value
            return f"Net Tool Weight (lbs) {value} lb"
    return None


def _extract_battery_mass(text: str) -> str | None:
    for pattern in (
        r"\bIndividual Battery Weight\b.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
        r"\bBattery Weight\b.{0,100}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
        r"(?<!Shipping )\bWeight\b.{0,80}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
    ):
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return m.group(1).strip()
    return None


def _parse_mass_with_label_unit(raw: str) -> float | None:
    q = parse_mass(raw)
    if q:
        return q.value
    m = re.search(r"(?:\(lbs?\)|\(lb\.?\)).{0,40}?(\d+(?:\.\d+)?)", raw, re.I | re.S)
    return mass_to_kg(float(m.group(1)), "lb") if m else None


def _has_conflicting_values(claims: list[CandidateClaim]) -> bool:
    return len({round(float(c.value), 9) for c in claims}) > 1


def _unambiguous_preferred_from(claims: list[CandidateClaim]) -> CandidateClaim | None:
    if not claims or _has_conflicting_values(claims):
        return None
    return _preferred_from(claims)


def _preferred_from(claims: list[CandidateClaim]) -> CandidateClaim:
    priority = {"manufacturer_stated": 2, "qualified_secondary_exact_sku": 1}
    return max(claims, key=lambda c: priority.get(c.evidence_method, 0))


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.source_url,
        )
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out


def _dedupe_requests(requests: list[SourceRequest]) -> list[SourceRequest]:
    seen = set()
    out = []
    for request in requests:
        if request.url not in seen:
            out.append(request)
            seen.add(request.url)
    return out