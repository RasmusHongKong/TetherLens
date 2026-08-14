from __future__ import annotations

import re

from tetherlens_ingest.models import CandidateClaim, ProductIdentity, ReadinessIssue, SourceArtifact
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
                claims.append(self._claim("manufacturer_item_code", sku.group(1), artifact.url))
            if re.search(r"M18\b", text, re.I):
                claims.append(self._claim("battery_platform", "M18", artifact.url))
            if re.search(r"Compact.*Battery|Extended Capacity.*Battery|XC Extended Capacity", text, re.I | re.S):
                claims.append(self._claim("battery_configuration_required", True, artifact.url))
            if re.search(r"Specs\s*Loading", text, re.I):
                claims.append(self._claim("acquisition.dynamic_specs_detected", True, artifact.url))
        return _dedupe(claims)

    def readiness_issues(self, claims: list[CandidateClaim]) -> list[ReadinessIssue]:
        keys = {c.property_key for c in claims}
        issues: list[ReadinessIssue] = []
        if "operational_mass_kg" not in keys:
            issues.append(ReadinessIssue(code="MISSING_OPERATIONAL_MASS", property_key="operational_mass_kg"))
        if "acquisition.dynamic_specs_detected" in keys:
            issues.append(ReadinessIssue(code="DYNAMIC_SPECS_UNRESOLVED", detail="Static page shell exposes a dynamically loaded Specs block."))
        return issues

    @staticmethod
    def _claim(key: str, value, url: str) -> CandidateClaim:
        return CandidateClaim(property_key=key, value=value, source_url=url, extractor="milwaukee.v0.1")


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
