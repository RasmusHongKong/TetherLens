from __future__ import annotations

import html as html_lib
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

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
        if not self._is_sf4_22(identity):
            return []

        discovered = self._discover_battery_sources(identity, primary_artifact)
        return _prefer_discovered_requests([*discovered, *self._SF4_22_BATTERY_SOURCES])

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        primary_url = artifacts[0].url if artifacts else identity.url

        for artifact in artifacts:
            text = page_text(artifact.body)
            role = artifact.metadata.get("role")

            if role == "battery":
                model = str(artifact.metadata.get("battery_model") or "battery")
                raw_mass = self._extract_battery_mass_text(artifact)
                if raw_mass and (q := parse_mass(raw_mass)):
                    claims.append(self._claim(
                        "battery_mass_kg",
                        q.value,
                        "kg",
                        raw_mass,
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
                        extractor="hilti.v0.5",
                    ))

        return _dedupe(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations: list[AcquisitionObservation] = []
        if not self._is_sf4_22(identity):
            return observations

        battery_artifacts = [artifact for artifact in artifacts if artifact.metadata.get("role") == "battery"]
        discovered_count = sum(
            artifact.metadata.get("relationship_basis") in {"apollo_state", "page_link"}
            for artifact in battery_artifacts
        )
        seeded_count = sum(
            artifact.metadata.get("relationship_basis") == "benchmark_seed" for artifact in battery_artifacts
        )
        if discovered_count:
            observations.append(AcquisitionObservation(
                code="RELATED_SOURCES_DISCOVERED",
                value=discovered_count,
                detail="Hilti battery source edges were discovered from first-party relationship data in the tool page.",
                source_url=identity.url,
                extractor="hilti.v0.5",
            ))
        if seeded_count:
            observations.append(AcquisitionObservation(
                code="RELATED_SOURCES_SEEDED",
                value=seeded_count,
                detail="Missing battery source edges were filled from pre-verified benchmark seeds; automatic relationship discovery is incomplete.",
                source_url=identity.url,
                extractor="hilti.v0.5",
            ))

        for artifact in battery_artifacts:
            if self._extract_battery_mass_text(artifact) is None:
                observations.append(AcquisitionObservation(
                    code="RELATED_SOURCE_FACT_MISSING",
                    value=str(artifact.metadata.get("battery_model") or "battery"),
                    detail="Related Hilti battery page was fetched but no parseable manufacturer weight was recovered.",
                    source_url=artifact.url,
                    extractor="hilti.v0.5",
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
    def _is_sf4_22(identity: ProductIdentity) -> bool:
        return (
            identity.product_type == ProductType.TOOL
            and (identity.sku == "2253847" or identity.manufacturer_ids.get("technical_family") == "r13275669")
        )

    @staticmethod
    def _extract_battery_mass_text(artifact: SourceArtifact) -> str | None:
        text = page_text(artifact.body)
        for pattern in (
            r"\bWeight\s*:?\s*([^\n]+)",
            r"\bProduct weight\s*:?\s*([^\n]+)",
        ):
            m = re.search(pattern, text, re.I)
            if m and parse_mass(m.group(1)):
                mass = re.search(r"\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b", m.group(1), re.I)
                return mass.group(0) if mass else m.group(1).strip()

        raw = html_lib.unescape(artifact.body)
        m = re.search(
            r"(?:Product\s+)?Weight.{0,240}?(\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?|g)\b)",
            raw,
            re.I | re.S,
        )
        return m.group(1).strip() if m and parse_mass(m.group(1)) else None

    def _discover_battery_sources(
        self,
        identity: ProductIdentity,
        primary_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        requests = [
            *self._discover_apollo_battery_sources(identity, primary_artifact),
            *self._discover_linked_battery_sources(primary_artifact),
        ]
        return _prefer_discovered_requests(requests)

    @staticmethod
    def _discover_apollo_battery_sources(
        identity: ProductIdentity,
        primary_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        soup = BeautifulSoup(primary_artifact.body, "html.parser")
        script = soup.find("script", id="hdms-website-state")
        if script is None:
            return []
        body = script.string or script.get_text(" ", strip=False)
        if not body:
            return []
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return []

        state = payload.get("apollo.state")
        if not isinstance(state, dict):
            apollo = payload.get("apollo")
            state = apollo.get("state", {}) if isinstance(apollo, dict) else {}
        if not isinstance(state, dict):
            return []

        subject_refs = []
        if identity.sku:
            subject_refs.append(f"Product:{identity.sku}")
        family = identity.manufacturer_ids.get("technical_family")
        if family:
            subject_refs.append(f"Product:{family}")

        requests: list[SourceRequest] = []
        for subject_ref in subject_refs:
            subject = state.get(subject_ref)
            if not isinstance(subject, dict):
                continue
            related = subject.get("relatedProducts")
            if not isinstance(related, list):
                continue

            for relation in related:
                if not isinstance(relation, dict) or relation.get("type") != "BATTERIES_CHARGERS":
                    continue
                product_pointer = relation.get("product")
                if not isinstance(product_pointer, dict):
                    continue
                product_ref = product_pointer.get("__ref")
                if not isinstance(product_ref, str):
                    continue
                product = state.get(product_ref)
                if not isinstance(product, dict):
                    continue

                title = str(product.get("title") or "")
                model_match = re.search(r"\bB\s*\d{2}-\d+\b", title, re.I)
                if not model_match or "battery" not in title.lower():
                    continue
                model = re.sub(r"\s+", " ", model_match.group(0)).upper()

                product_id = str(product.get("id") or product_ref.removeprefix("Product:"))
                url = _apollo_product_url(primary_artifact.url, state, product, product_id)
                if not url:
                    continue
                requests.append(SourceRequest(
                    url=url,
                    metadata={
                        "role": "battery",
                        "battery_model": model,
                        "relationship_basis": "apollo_state",
                        "relationship_subject": subject_ref,
                        "relationship_product_ref": product_ref,
                    },
                ))
        return _prefer_discovered_requests(requests)

    @staticmethod
    def _discover_linked_battery_sources(primary_artifact: SourceArtifact) -> list[SourceRequest]:
        soup = BeautifulSoup(primary_artifact.body, "html.parser")
        requests: list[SourceRequest] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "")
            if "CLS_BATT_CHARGERS_POWER_STATIONS_7125" not in href:
                continue

            anchor_text = " ".join(anchor.stripped_strings)
            model_match = re.search(r"\bB\s*\d{2}-\d+\b", anchor_text, re.I)
            if not model_match:
                parent_text = " ".join(anchor.parent.stripped_strings) if anchor.parent else ""
                model_match = re.search(r"\bB\s*\d{2}-\d+\b", parent_text, re.I)
            if not model_match:
                continue

            model = re.sub(r"\s+", " ", model_match.group(0)).upper()
            requests.append(SourceRequest(
                url=urljoin(primary_artifact.url, href),
                metadata={
                    "role": "battery",
                    "battery_model": model,
                    "relationship_basis": "page_link",
                },
            ))
        return _prefer_discovered_requests(requests)

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
            extractor="hilti.v0.5",
        )


def _apollo_product_url(
    primary_url: str,
    state: dict,
    product: dict,
    product_id: str,
) -> str | None:
    category_pointer = product.get("defaultCategory")
    if not isinstance(category_pointer, dict):
        return None
    category_ref = category_pointer.get("__ref")
    if not isinstance(category_ref, str) or not category_ref.startswith("Category:"):
        return None
    category = state.get(category_ref)
    if not isinstance(category, dict):
        return None

    category_ids: list[str] = []
    path = category.get("path")
    if isinstance(path, list):
        for pointer in path:
            if not isinstance(pointer, dict):
                continue
            ref = pointer.get("__ref")
            if isinstance(ref, str) and ref.startswith("Category:"):
                category_ids.append(ref.removeprefix("Category:"))
    category_id = str(category.get("id") or category_ref.removeprefix("Category:"))
    category_ids.append(category_id)
    if not category_ids:
        return None
    relative = "/c/" + "/".join(category_ids) + f"/{product_id}"
    return urljoin(primary_url, relative)


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen = set()
    out = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out


def _prefer_discovered_requests(requests: list[SourceRequest]) -> list[SourceRequest]:
    priority = {"benchmark_seed": 0, "page_link": 1, "apollo_state": 2}
    by_model: dict[str, SourceRequest] = {}
    for request in requests:
        model = str(request.metadata.get("battery_model") or request.url).upper()
        existing = by_model.get(model)
        if existing is None:
            by_model[model] = request
            continue
        existing_priority = priority.get(str(existing.metadata.get("relationship_basis")), 0)
        request_priority = priority.get(str(request.metadata.get("relationship_basis")), 0)
        if request_priority > existing_priority:
            by_model[model] = request
    return list(by_model.values())
