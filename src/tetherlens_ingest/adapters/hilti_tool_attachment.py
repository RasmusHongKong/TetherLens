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
                if not raw_capacity or not (quantity := parse_mass(raw_capacity)):
                    continue
                claims.append(CandidateClaim(
                    subject_type=ClaimSubjectType.PRODUCT,
                    subject_ref="self",
                    property_key="rated_capacity_kg",
                    value=quantity.value,
                    unit="kg",
                    raw_value=raw_capacity,
                    source_url=artifact.url,
                    evidence_method="manufacturer_stated",
                    extractor="hilti.v0.8",
                ))

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
                extractor="hilti.v0.8",
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
        window = text[anchor.start():anchor.start() + 1800]
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
                extractor="hilti.v0.8",
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
                extractor="hilti.v0.8",
            ))
        return claims

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
