from __future__ import annotations

import json
import re
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
from tetherlens_ingest.normalize import parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class MilwaukeeAdapter(ManufacturerAdapter):
    manufacturer = "Milwaukee"
    extractor = "milwaukee.v0.3"

    def related_sources(self, identity: ProductIdentity, primary_artifact: SourceArtifact) -> list[SourceRequest]:
        if identity.product_type != ProductType.TOOL:
            return []
        sku = identity.sku or self._sku_from_artifact(primary_artifact)
        if not sku:
            return []

        requests = [self._api_request(primary_artifact.url, sku, role="product_api")]
        for battery_sku in self._discover_battery_skus(primary_artifact.body):
            requests.append(self._api_request(
                primary_artifact.url,
                battery_sku,
                role="battery_api",
                relationship_basis="rsc_family_graph",
            ))
        return _dedupe_requests(requests)

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            role = artifact.metadata.get("role")
            if role in {"product_api", "battery_api"}:
                product = self._api_product(artifact)
                if not product:
                    continue
                sku = str(product.get("sku") or artifact.metadata.get("sku") or "")
                if role == "battery_api":
                    raw_mass = self._preferred_battery_mass(product)
                    if raw_mass and (mass := parse_mass(raw_mass)):
                        claims.append(self._claim(
                            "battery_mass_kg", mass.value, raw_mass, artifact.url,
                            subject_type=ClaimSubjectType.RELATED_PRODUCT,
                            subject_ref=sku or "battery", unit="kg",
                        ))
                    continue

                if sku:
                    claims.append(self._claim("manufacturer_item_code", sku, sku, artifact.url))
                platform = self._spec_value(product, "batterySystem")
                if platform:
                    claims.append(self._claim("battery_platform", platform.replace("™", "").strip(), platform, artifact.url))
                raw_body_mass = self._product_mass(product)
                if raw_body_mass and (mass := parse_mass(raw_body_mass)):
                    claims.append(self._claim("tool_body_mass_kg", mass.value, raw_body_mass, artifact.url, unit="kg"))
                continue

            text = page_text(artifact.body)
            sku_match = re.search(r"\b(\d{4}-\d{2})\b", text)
            if sku_match:
                claims.append(self._claim("manufacturer_item_code", sku_match.group(1), sku_match.group(1), artifact.url))
            if re.search(r"M18\b", text, re.I):
                claims.append(self._claim("battery_platform", "M18", "M18", artifact.url))

        body_claim = next((claim for claim in claims if claim.property_key == "tool_body_mass_kg"), None)
        if body_claim:
            primary_url = artifacts[0].url if artifacts else identity.url
            for battery_claim in (claim for claim in claims if claim.property_key == "battery_mass_kg"):
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
                    subject_ref=f"{identity.sku or identity.model or 'tool'}+{battery_claim.subject_ref}",
                    property_key="operational_mass_kg",
                    value=round(float(body_claim.value) + float(battery_claim.value), 6),
                    unit="kg",
                    raw_value=f"{body_claim.raw_value} tool body + {battery_claim.raw_value} battery",
                    source_url=body_claim.source_url or primary_url,
                    supporting_source_urls=[battery_claim.source_url],
                    evidence_method="derived",
                    extractor=self.extractor,
                ))
        return _dedupe(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations: list[AcquisitionObservation] = []
        api_artifacts = [artifact for artifact in artifacts if artifact.metadata.get("role") in {"product_api", "battery_api"}]
        product_api = [artifact for artifact in api_artifacts if artifact.metadata.get("role") == "product_api"]
        battery_api = [artifact for artifact in api_artifacts if artifact.metadata.get("role") == "battery_api"]

        if product_api and any(self._api_product(artifact) for artifact in product_api):
            observations.append(AcquisitionObservation(
                code="PRODUCT_API_ACQUIRED", value=True,
                detail="Milwaukee first-party product API returned structured product specifications.",
                source_url=product_api[0].url, extractor=self.extractor,
            ))
        if battery_api:
            observations.append(AcquisitionObservation(
                code="RELATED_SOURCES_DISCOVERED", value=len(battery_api),
                detail="Compatible battery SKUs were discovered from Milwaukee first-party RSC family data and fetched through the product API.",
                source_url=identity.url, extractor=self.extractor,
            ))

        if identity.product_type == ProductType.TOOL:
            product = next((self._api_product(artifact) for artifact in product_api if self._api_product(artifact)), None)
            if product and self._product_mass(product) is None:
                observations.append(AcquisitionObservation(
                    code="MANUFACTURER_TOOL_MASS_MISSING", value=True,
                    detail="Milwaukee product API was acquired successfully but does not publish a tool-body mass for this SKU.",
                    source_url=product_api[0].url, extractor=self.extractor,
                ))

        for artifact in battery_api:
            product = self._api_product(artifact)
            if product and self._preferred_battery_mass(product) is None:
                observations.append(AcquisitionObservation(
                    code="RELATED_SOURCE_FACT_MISSING",
                    value=str(product.get("sku") or artifact.metadata.get("sku") or "battery"),
                    detail="Related Milwaukee battery API record was fetched but contains no manufacturer physical-mass value.",
                    source_url=artifact.url, extractor=self.extractor,
                ))
            elif product and self._has_mass_conflict(product):
                observations.append(AcquisitionObservation(
                    code="CONFLICTING_MANUFACTURER_MASS",
                    value=str(product.get("sku") or artifact.metadata.get("sku") or "battery"),
                    detail="Milwaukee publishes different physical weight and netWeight values; the physical specs.weight value is retained as the battery mass candidate.",
                    source_url=artifact.url, extractor=self.extractor,
                ))
        return observations

    def readiness_issues(self, claims, observations) -> list[ReadinessIssue]:
        issues: list[ReadinessIssue] = []
        if not any(claim.property_key == "operational_mass_kg" for claim in claims):
            issues.append(ReadinessIssue(code="MISSING_OPERATIONAL_MASS", property_key="operational_mass_kg"))
        if not any(claim.property_key == "tool_body_mass_kg" for claim in claims):
            codes = {observation.code for observation in observations}
            if "MANUFACTURER_TOOL_MASS_MISSING" in codes:
                issues.append(ReadinessIssue(
                    code="MISSING_TOOL_BODY_MASS", property_key="tool_body_mass_kg",
                    detail="Manufacturer data does not publish tool-body mass and no qualified fallback source resolved it.",
                ))
        return issues

    @classmethod
    def _api_request(cls, page_url: str, sku: str, role: str, relationship_basis: str | None = None) -> SourceRequest:
        metadata = {"role": role, "sku": sku}
        if relationship_basis:
            metadata["relationship_basis"] = relationship_basis
        return SourceRequest(url=urljoin(page_url, f"/api/v1/products/{quote(sku, safe='')}?language=en"), source_type=SourceType.MANUFACTURER_JSON, metadata=metadata)

    @staticmethod
    def _sku_from_artifact(artifact: SourceArtifact) -> str | None:
        match = re.search(r"\b(\d{4}-\d{2})\b", page_text(artifact.body))
        return match.group(1) if match else None

    @staticmethod
    def _discover_battery_skus(raw: str) -> list[str]:
        found: list[str] = []
        for match in re.finditer(r"\b(48-11-\d{4})\b", raw, re.I):
            context = raw[max(0, match.start() - 500): min(len(raw), match.end() + 500)]
            if "battery" in context.lower():
                sku = match.group(1).upper()
                if sku not in found:
                    found.append(sku)
        return found

    @staticmethod
    def _api_product(artifact: SourceArtifact) -> dict | None:
        try:
            payload = json.loads(artifact.body)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            return None
        data = payload.get("data")
        result = data.get("result") if isinstance(data, dict) else None
        return result if isinstance(result, dict) else None

    @staticmethod
    def _spec_value(product: dict, key: str) -> str | None:
        specs = product.get("specs")
        spec = specs.get(key) if isinstance(specs, dict) else None
        if not isinstance(spec, dict):
            return None
        value = spec.get("value") or spec.get("display")
        return str(value).strip() if value not in (None, "") else None

    @classmethod
    def _product_mass(cls, product: dict) -> str | None:
        return cls._spec_value(product, "weight") or cls._spec_value(product, "productWeight")

    @classmethod
    def _preferred_battery_mass(cls, product: dict) -> str | None:
        return cls._spec_value(product, "weight") or cls._spec_value(product, "productWeight")

    @classmethod
    def _has_mass_conflict(cls, product: dict) -> bool:
        physical = cls._preferred_battery_mass(product)
        if not physical:
            return False
        specs2 = product.get("specs2")
        if not isinstance(specs2, list):
            return False
        net = next((str(item.get("value") or item.get("display") or "").strip() for item in specs2 if isinstance(item, dict) and item.get("key") == "netWeight"), "")
        return bool(net and net != physical)

    @classmethod
    def _claim(cls, key, value, raw, url, subject_type=ClaimSubjectType.PRODUCT, subject_ref="self", unit=None) -> CandidateClaim:
        return CandidateClaim(subject_type=subject_type, subject_ref=subject_ref, property_key=key, value=value, unit=unit, raw_value=raw, source_url=url, extractor=cls.extractor)


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
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
