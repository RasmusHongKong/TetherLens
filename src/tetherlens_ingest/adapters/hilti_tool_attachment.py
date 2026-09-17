from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import parse_mass

from .common import page_text
from .hilti import HiltiAdapter as _BaseHiltiAdapter


_DOCUMENT_ROLES = {"document_index", "operating_instruction"}
_ACCESSORY_OPENINGS_FEATURE_REF = "accessory_installation_openings"
_RETAINING_STRAP_INTERFACE_REF = "tether_attachment_point"
_RETAINING_STRAP_INSTALLATION_REF = "retaining_strap_accessory_openings"
_TETHER_TO_STRAP_DECLARATION_REF = "tool_tether_to_retaining_strap"


class HiltiAdapter(_BaseHiltiAdapter):
    """Hilti adapter with ToolAttachment facts and manufacturer-document relationships."""

    recursive_related_sources = True

    def related_sources(self, identity: ProductIdentity, artifact: SourceArtifact) -> list[SourceRequest]:
        role = str(artifact.metadata.get("role") or "primary")
        if role == "document_index":
            return self._discover_operating_instructions(identity, artifact)
        if role != "primary":
            return []

        requests = list(super().related_sources(identity, artifact))
        if (
            identity.product_type == ProductType.TOOL
            and (model := _tool_model(identity))
            and _is_verified_tool_page(identity, artifact, model)
        ):
            requests.append(SourceRequest(
                url=f"https://www.hilti.com/technical-library?search=true&text={quote_plus(model)}",
                metadata={
                    "role": "document_index",
                    "document_query": model,
                    "relationship_basis": "technical_library_search",
                },
            ))
        return _dedupe_requests(requests)

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        # The legacy Hilti extractor treats every non-battery artifact as the product page.
        # Keep manufacturer documents out of that path so referenced component SKUs cannot
        # be mistaken for the tool's own manufacturer item code.
        base_artifacts = [
            artifact for artifact in artifacts
            if str(artifact.metadata.get("role") or "primary") not in _DOCUMENT_ROLES
        ]
        claims = list(super().extract(identity, base_artifacts))

        if identity.product_type == ProductType.TOOL_ATTACHMENT:
            for artifact in artifacts:
                if artifact.metadata.get("role"):
                    continue
                raw_capacity = self._extract_retaining_strap_capacity(identity, artifact)
                if raw_capacity and (quantity := parse_mass(raw_capacity)):
                    claims.append(CandidateClaim(
                        subject_type=ClaimSubjectType.PRODUCT,
                        subject_ref="self",
                        property_key="rated_capacity_kg",
                        value=quantity.value,
                        unit="kg",
                        raw_value=raw_capacity,
                        source_url=artifact.url,
                        evidence_method="manufacturer_stated",
                        extractor="hilti.v0.9",
                    ))
                claims.extend(self._extract_retaining_strap_interface(identity, artifact))

        if identity.product_type == ProductType.TOOL:
            for artifact in artifacts:
                if artifact.metadata.get("role") != "operating_instruction":
                    continue
                claims.extend(self._extract_drop_arrest_pairing(identity, artifact))

        return _dedupe_claims(claims)

    def observe(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[AcquisitionObservation]:
        observations = list(super().observe(identity, artifacts))
        manuals = [artifact for artifact in artifacts if artifact.metadata.get("role") == "operating_instruction"]
        if manuals:
            observations.append(AcquisitionObservation(
                code="MANUFACTURER_DOCUMENTS_DISCOVERED",
                value=len(manuals),
                detail="Hilti operating instructions were discovered through the manufacturer technical library.",
                source_url=identity.url,
                extractor="hilti.v0.9",
            ))
        return observations

    @staticmethod
    def _discover_operating_instructions(identity: ProductIdentity, artifact: SourceArtifact) -> list[SourceRequest]:
        model = _tool_model(identity)
        if not model:
            return []

        soup = BeautifulSoup(artifact.body, "html.parser")
        requests: list[SourceRequest] = []
        for heading in soup.find_all(["h2", "h3", "h4"]):
            title = " ".join(heading.stripped_strings)
            if "operating instruction" not in title.lower() or not _contains_model(title, model):
                continue

            container = heading.parent
            for _ in range(4):
                if container is None:
                    break
                links = container.find_all("a", href=True)
                pdf_links = [str(link.get("href") or "") for link in links if ".pdf" in str(link.get("href") or "").lower()]
                if pdf_links:
                    for href in pdf_links:
                        requests.append(SourceRequest(
                            url=urljoin(artifact.url, href),
                            source_type=SourceType.MANUFACTURER_DOCUMENT,
                            metadata={
                                "role": "operating_instruction",
                                "document_query": model,
                                "document_title": title,
                                "relationship_basis": "technical_library_result",
                            },
                        ))
                    break
                container = container.parent
        return _dedupe_requests(requests)

    @staticmethod
    def _extract_drop_arrest_pairing(identity: ProductIdentity, artifact: SourceArtifact) -> list[CandidateClaim]:
        model = _tool_model(identity)
        text = _normalized_document_text(artifact)
        if not model or not _contains_model(text, model):
            return []

        anchor = re.search(r"(?:fall arrest|drop arrester)", text, re.I)
        if not anchor:
            return []
        window = text[anchor.start():anchor.start() + 2200]
        pairing = re.search(
            r"retaining strap(?P<strap>.{0,220}?)and the Hilti tool tether(?P<tether>.{0,160}?)(?:\.|$)",
            window,
            re.I,
        )
        if not pairing:
            return []

        strap_match = re.search(r"#\s*(\d{6,})", pairing.group("strap"))
        tether_match = re.search(r"#\s*(\d{6,})", pairing.group("tether"))
        raw_match = re.search(r"As drop arrester.{0,700}?(?:\.|$)", window, re.I)
        raw = raw_match.group(0) if raw_match else pairing.group(0)

        claims: list[CandidateClaim] = []
        if strap_match:
            claims.append(CandidateClaim(
                subject_type=ClaimSubjectType.PRODUCT,
                subject_ref="self",
                property_key="tool.required_tool_attachment",
                value=strap_match.group(1),
                unit=None,
                raw_value=raw,
                source_url=artifact.url,
                evidence_method="manufacturer_pairing",
                extractor="hilti.v0.9",
            ))
        if tether_match:
            claims.append(CandidateClaim(
                subject_type=ClaimSubjectType.PRODUCT,
                subject_ref="self",
                property_key="tool.required_tether",
                value=tether_match.group(1),
                unit=None,
                raw_value=raw,
                source_url=artifact.url,
                evidence_method="manufacturer_pairing",
                extractor="hilti.v0.9",
            ))

        installation = re.search(
            r"Secure the retaining strap to the installation openings for accessories(?:\.|\s)",
            window,
            re.I,
        )
        if installation and strap_match:
            installation_raw = installation.group(0).strip()
            for property_key, value in (
                ("feature.kind", "other"),
                ("feature.role", "accessory_mount"),
                ("feature.location_description", "installation openings for accessories"),
            ):
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref=_ACCESSORY_OPENINGS_FEATURE_REF,
                    property_key=property_key,
                    value=value,
                    unit=None,
                    raw_value=installation_raw,
                    source_url=artifact.url,
                    evidence_method="manufacturer_installation_location",
                    extractor="hilti.v0.9",
                ))

            for property_key, value in (
                ("tool_attachment_installation.attachment_identifier", strap_match.group(1)),
                ("tool_attachment_installation.feature_ref", _ACCESSORY_OPENINGS_FEATURE_REF),
                ("tool_attachment_installation.issuer_manufacturer", "Hilti"),
                (
                    "tool_attachment_installation.scope",
                    f"{model} retaining strap installation at manufacturer-defined accessory openings",
                ),
            ):
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH,
                    subject_ref=_RETAINING_STRAP_INSTALLATION_REF,
                    property_key=property_key,
                    value=value,
                    unit=None,
                    raw_value=installation_raw,
                    source_url=artifact.url,
                    evidence_method="manufacturer_installation",
                    extractor="hilti.v0.9",
                ))

        connection = re.search(
            r"Secure one carabiner of the tool tether to the retaining strap(?:\s+and\s+secure the second carabiner to a load-bearing structure)?(?:\.|\s)",
            window,
            re.I,
        )
        if connection and strap_match and tether_match:
            connection_raw = connection.group(0).strip()
            compatibility_values = (
                ("connection_compatibility.connector_spec_ref", "tether_connector"),
                ("connection_compatibility.source_interface_type", "carabiner"),
                ("connection_compatibility.target_interface_type", "attachment_point"),
                (
                    "connection_compatibility.target_role",
                    "tool_attachment_tether_side",
                ),
                ("connection_compatibility.issuer_manufacturer", "Hilti"),
                (
                    "connection_compatibility.scope",
                    f"{model}: Hilti tool tether #{tether_match.group(1)} carabiner to retaining strap #{strap_match.group(1)}",
                ),
                # Retain the explicit product scope even though the current generic
                # declaration resolver does not yet execute on these two audit fields.
                (
                    "connection_compatibility.source_product_identifier",
                    tether_match.group(1),
                ),
                (
                    "connection_compatibility.target_product_identifier",
                    strap_match.group(1),
                ),
            )
            for property_key, value in compatibility_values:
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.CONNECTION_COMPATIBILITY,
                    subject_ref=_TETHER_TO_STRAP_DECLARATION_REF,
                    property_key=property_key,
                    value=value,
                    unit=None,
                    raw_value=connection_raw,
                    source_url=artifact.url,
                    evidence_method="manufacturer_pairing",
                    extractor="hilti.v0.9",
                ))

        return claims

    @staticmethod
    def _extract_retaining_strap_interface(
        identity: ProductIdentity,
        artifact: SourceArtifact,
    ) -> list[CandidateClaim]:
        text = re.sub(r"\s+", " ", page_text(artifact.body)).strip()
        if identity.sku and not re.search(rf"#\s*{re.escape(identity.sku)}\b", text):
            return []
        if "retaining strap" not in text.lower():
            return []

        function = re.search(
            r"Accessory for connecting compatible power tools to a Hilti (?:tool )?lanyard",
            text,
            re.I,
        )
        if not function:
            return []
        raw = function.group(0)
        return [
            CandidateClaim(
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref=_RETAINING_STRAP_INTERFACE_REF,
                property_key="interface.type",
                value="attachment_point",
                unit=None,
                raw_value=raw,
                source_url=artifact.url,
                evidence_method="manufacturer_functional_interface",
                extractor="hilti.v0.9",
            ),
            CandidateClaim(
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref=_RETAINING_STRAP_INTERFACE_REF,
                property_key="interface.role",
                value="tool_attachment_tether_side",
                unit=None,
                raw_value=raw,
                source_url=artifact.url,
                evidence_method="manufacturer_functional_interface",
                extractor="hilti.v0.9",
            ),
            CandidateClaim(
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref=_RETAINING_STRAP_INTERFACE_REF,
                property_key="interface.attribute.manufacturer_item_code",
                value=identity.sku or "2293133",
                unit=None,
                raw_value=raw,
                source_url=artifact.url,
                evidence_method="manufacturer_functional_interface",
                extractor="hilti.v0.9",
            ),
        ]

    @staticmethod
    def _extract_retaining_strap_capacity(identity: ProductIdentity, artifact: SourceArtifact) -> str | None:
        text = re.sub(r"\s+", " ", page_text(artifact.body))
        if identity.sku and not re.search(rf"#\s*{re.escape(identity.sku)}\b", text):
            return None
        if "retaining strap" not in text.lower():
            return None

        # Hilti's option line currently renders as e.g. "1x 15lb (6.8kg) Retaining strap assy".
        # Prefer the manufacturer's metric value when both units are published rather than
        # converting the rounded imperial marketing value back to kg.
        patterns = (
            r"\d+(?:\.\d+)?\s*lb[s]?\s*\(\s*(\d+(?:\.\d+)?\s*kg)\s*\)\s*Retaining strap",
            r"Retaining strap.{0,100}?\d+(?:\.\d+)?\s*lb[s]?\s*\(\s*(\d+(?:\.\d+)?\s*kg)\s*\)",
            r"Retaining strap.{0,100}?(\d+(?:\.\d+)?\s*kg)\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match and parse_mass(match.group(1)):
                return match.group(1).strip()
        return None


def _normalized_document_text(artifact: SourceArtifact) -> str:
    text = artifact.body if artifact.content_type == "application/pdf" else page_text(artifact.body)
    return re.sub(r"\s+", " ", text).strip()


def _tool_model(identity: ProductIdentity) -> str | None:
    candidates = [identity.model, identity.name]
    for candidate in candidates:
        if not candidate:
            continue
        match = re.search(r"\b[A-Z]{2,5}\s+\d+[A-Z]?(?:-\d+[A-Z]?)?\b", candidate, re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(0)).upper()
    return None


def _contains_model(text: str, model: str) -> bool:
    compact_text = re.sub(r"[\s\u00a0]+", " ", text).upper()
    compact_model = re.sub(r"\s+", " ", model).upper()
    return bool(re.search(rf"(?<![A-Z0-9]){re.escape(compact_model)}(?![A-Z0-9])", compact_text))


def _is_verified_tool_page(identity: ProductIdentity, artifact: SourceArtifact, model: str) -> bool:
    if artifact.source_type != SourceType.MANUFACTURER_WEBPAGE:
        return False
    text = page_text(artifact.body)
    if not _contains_model(text, model):
        return False
    if identity.sku and not re.search(rf"#\s*{re.escape(identity.sku)}\b", text):
        return False
    return True


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


def _dedupe_requests(requests: list[SourceRequest]) -> list[SourceRequest]:
    seen: set[tuple[str, str]] = set()
    out: list[SourceRequest] = []
    for request in requests:
        key = (request.url, request.source_type.value)
        if key in seen:
            continue
        seen.add(key)
        out.append(request)
    return out
