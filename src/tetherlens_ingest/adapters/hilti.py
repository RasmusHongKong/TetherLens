from __future__ import annotations

import re

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
)
from tetherlens_ingest.normalize import opening_action_count, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class HiltiAdapter(ManufacturerAdapter):
    manufacturer = "Hilti"

    _SF4_22_BATTERY_SOURCES = (
        SourceRequest(
            url="https://www.hilti.com/c/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250264",
            metadata={"role": "battery", "battery_model": "B 22-55", "relationship_basis": "benchmark_seed"},
        ),
        SourceRequest(
            url="https://www.hilti.com/c/CLS_POWER_TOOLS_7125/CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250303",
            metadata={"role": "battery", "battery_model": "B 22-85", "relationship_basis": "benchmark_seed"},
        ),
    )

    def related_sources(self, identity: ProductIdentity, primary_artifact: SourceArtifact) -> list[SourceRequest]:
        if identity.product_type == ProductType.TOOL and (
            identity.sku == "2253847" or identity.manufacturer_ids.get("technical_family") == "r13275669"
        ):
            return list(self._SF4_22_BATTERY_SOURCES)
        return []

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        primary_url = artifacts[0].url if artifacts else identity.url

        for artifact in artifacts:
            text = page_text(artifact.body)
            role = artifact.metadata.get("role")

            if role == "battery":
                model = str(artifact.metadata.get("battery_model") or "battery")
                m = re.search(r"\bWeight\s*:?\s*([^\n]+)", text, re.I)
                if m and (q := parse_mass(m.group(1))):
                    claims.append(self._claim(
                        "battery_mass_kg",
                        q.value,
                        "kg",
                        m.group(1),
                        artifact.url,
                        ClaimSubjectType.RELATED_PRODUCT,
                        model,
                    ))
                continue

            if identity.product_type == ProductType.TETHER:
                m = re.search(r"Maximum load\s*:?\s*([^\n]+)", text, re.I)
                if m and (q := parse_mass(m.group(1))):
                    claims.append(self._claim("rated_capacity_kg", q.value, "kg", m.group(1), artifact.url))

            if identity.product_type == ProductType.TOOL:
                for pattern in (
                    r"Tool body weight\s*:?\s*([^\n]+)",
                    r"Weight according[^\n]*without battery\s*:?\s*([^\n]+)",
                ):
                    m = re.search(pattern, text, re.I)
                    if m and (q := parse_mass(m.group(1))):
                        claims.append(self._claim("tool_body_mass_kg", q.value, "kg", m.group(1), artifact.url))
                        break

            sku = re.search(r"#(\d{6,})", text)
            if sku:
                claims.append(self._claim("manufacturer_item_code", sku.group(1), None, sku.group(1), artifact.url))

            if identity.product_type == ProductType.TETHER:
                if re.search(r"self-locking carabiner", text, re.I):
                    claims.append(self._claim(
                        "connector.locking_mode", "auto_locking", None, "self-locking carabiner", artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC, "tether_connector",
                    ))
                if re.search(r"double carabiner", text, re.I):
                    claims.append(self._claim("tether.connection_count", 2, None, "double carabiner", artifact.url))
                actions = opening_action_count(text)
                if actions:
                    claims.append(self._claim(
                        "connector.opening_action_count", actions, None, None, artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC, "tether_connector",
                    ))

        if identity.product_type == ProductType.TOOL:
            body_claim = next((claim for claim in claims if claim.property_key == "tool_body_mass_kg"), None)
            battery_claims = [claim for claim in claims if claim.property_key == "battery_mass_kg"]
            if body_claim:
                for battery_claim in battery_claims:
                    profile_ref = f"{identity.sku or identity.model or 'tool'}+{battery_claim.subject_ref}"
                    claims.append(CandidateClaim(
                        subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
                        subject_ref=profile_ref,
                        property_key="operational_mass_kg",
                        value=self.operational_mass(float(body_claim.value), float(battery_claim.value)),
                        unit="kg",
                        raw_value=f"{body_claim.raw_value} tool body + {battery_claim.raw_value} battery",
                        source_url=primary_url,
                        supporting_source_urls=[battery_claim.source_url],
                        evidence_method="derived",
                        extractor="hilti.v0.3",
                    ))

        return _dedupe(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations: list[AcquisitionObservation] = []
        if identity.product_type == ProductType.TOOL and (
            identity.sku == "2253847" or identity.manufacturer_ids.get("technical_family") == "r13275669"
        ):
            observations.append(AcquisitionObservation(
                code="RELATED_SOURCES_SEEDED",
                value=2,
                detail="B 22-55 and B 22-85 battery source edges are pre-verified benchmark seeds; automatic Hilti compatibility discovery is not yet implemented.",
                source_url=identity.url,
                extractor="hilti.v0.3",
            ))
        return observations

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue] | None:
        if not any(claim.property_key == "tool_body_mass_kg" for claim in claims):
            return None
        if not any(claim.property_key == "operational_mass_kg" for claim in claims):
            return [ReadinessIssue(code="MISSING_OPERATIONAL_MASS", property_key="operational_mass_kg")]
        return []

    @staticmethod
    def operational_mass(tool_body_mass_kg: float, battery_mass_kg: float) -> float:
        return round(tool_body_mass_kg + battery_mass_kg, 6)

    @staticmethod
    def _claim(
        key: str,
        value,
        unit: str | None,
        raw: str | None,
        url: str,
        subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
        subject_ref: str = "self",
    ) -> CandidateClaim:
        return CandidateClaim(
            subject_type=subject_type,
            subject_ref=subject_ref,
            property_key=key,
            value=value,
            unit=unit,
            raw_value=raw,
            source_url=url,
            extractor="hilti.v0.3",
        )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
