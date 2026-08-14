from __future__ import annotations

import re

from tetherlens_ingest.models import AcquisitionObservation, CandidateClaim, ProductIdentity, ReadinessIssue, SourceArtifact
from .base import ManufacturerAdapter
from .common import page_text


class MilwaukeeAdapter(ManufacturerAdapter):
    manufacturer = "Milwaukee"

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            sku = re.search(r"\b(\d{4}-\d{2})\b", text)
            if sku:
                claims.append(self._claim("manufacturer_item_code", sku.group(1), sku.group(1), artifact.url))
            if re.search(r"M18\b", text, re.I):
                claims.append(self._claim("battery_platform", "M18", "M18", artifact.url))
        return _dedupe(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations: list[AcquisitionObservation] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            if re.search(r"Compact.*Battery|Extended Capacity.*Battery|XC Extended Capacity", text, re.I | re.S):
                observations.append(AcquisitionObservation(
                    code="BATTERY_CONFIGURATION_REQUIRED",
                    value=True,
                    detail="Manufacturer page indicates multiple compatible battery configurations; operational mass must include the selected installed battery.",
                    source_url=artifact.url,
                    extractor="milwaukee.v0.2",
                ))
            if re.search(r"Specs\s*Loading", text, re.I):
                observations.append(AcquisitionObservation(
                    code="DYNAMIC_SPECS_DETECTED",
                    value=True,
                    detail="Static page shell exposes a dynamically loaded Specs block.",
                    source_url=artifact.url,
                    extractor="milwaukee.v0.2",
                ))
        return observations

    def readiness_issues(
        self,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue]:
        keys = {c.property_key for c in claims}
        observation_codes = {o.code for o in observations}
        issues: list[ReadinessIssue] = []
        if "operational_mass_kg" not in keys:
            issues.append(ReadinessIssue(code="MISSING_OPERATIONAL_MASS", property_key="operational_mass_kg"))
        if "DYNAMIC_SPECS_DETECTED" in observation_codes:
            issues.append(ReadinessIssue(code="DYNAMIC_SPECS_UNRESOLVED", detail="Static page shell exposes a dynamically loaded Specs block."))
        return issues

    @staticmethod
    def _claim(key: str, value, raw: str | None, url: str) -> CandidateClaim:
        return CandidateClaim(property_key=key, value=value, raw_value=raw, source_url=url, extractor="milwaukee.v0.2")


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
