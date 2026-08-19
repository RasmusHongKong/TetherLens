from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin, urlparse

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


_DOCUMENT_ROLES = {"document_index", "operating_instruction", "online_operating_instruction"}
_PAIRING_ROLES = {"operating_instruction", "online_operating_instruction"}


class HiltiAdapter(_BaseHiltiAdapter):
    """Hilti adapter with ToolAttachment facts and manufacturer-document relationships."""

    recursive_related_sources = True

    def related_sources(self, identity: ProductIdentity, artifact: SourceArtifact) -> list[SourceRequest]:
        role = str(artifact.metadata.get("role") or "primary")
        if role == "document_index":
            return self._discover_operating_instructions(identity, artifact)
        if role == "operating_instruction":
            return self._discover_online_operating_instruction(identity, artifact)
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
                    extractor="hilti.v0.9",
                ))

        if identity.product_type == ProductType.TOOL:
            for artifact in artifacts:
                if artifact.metadata.get("role") not in _PAIRING_ROLES:
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
            external_link_count = sum(
                len(links)
                for artifact in manuals
                if isinstance((links := artifact.metadata.get("document_links")), list)
            )
            observations.append(AcquisitionObservation(
                code="MANUFACTURER_DOCUMENT_EXTERNAL_LINKS",
                value=external_link_count,
                detail="Count of external URI link annotations extracted from Hilti operating-instruction PDFs.",
                source_url=identity.url,
                extractor="hilti.v0.9",
            ))

        online_manuals = [artifact for artifact in artifacts if artifact.metadata.get("role") == "online_operating_instruction"]
        if online_manuals:
            observations.append(AcquisitionObservation(
                code="ONLINE_OPERATING_INSTRUCTION_DISCOVERED",
                value=len(online_manuals),
                detail="Hilti web-rendered operating instructions were resolved from documentation IDs embedded in manufacturer PDF evidence.",
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
    def _discover_online_operating_instruction(identity: ProductIdentity, artifact: SourceArtifact) -> list[SourceRequest]:
        model = _tool_model(identity)
        text = _normalized_document_text(artifact)
        if not model or not _contains_model(text, model):
            return []

        evidence_strings = [text]
        links = artifact.metadata.get("document_links")
        if isinstance(links, list):
            evidence_strings.extend(str(link) for link in links)

        document_id = next(
            (document_id for value in evidence_strings if (document_id := _embedded_online_manual_id(value))),
            None,
        )
        if not document_id or not (url := _online_manual_url(identity, document_id)):
            return []

        return [SourceRequest(
            url=url,
            metadata={
                "role": "online_operating_instruction",
                "document_query": model,
                "document_id": document_id,
                "parent_document_url": artifact.url,
                "relationship_basis": "embedded_document_id",
            },
        )]

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
        return claims

    @staticmethod
    def _extract_retaining_strap_capacity(identity: ProductIdentity, artifact: SourceArtifact) -> str | None:
        text = re.sub(r"\s+", " ", page_text(artifact.body))
        if identity.sku and not re.search(rf"#\s*{re.escape(identity.sku)}\b", text):
            return None
        if "retaining strap" not in text.lower():
            return None

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


def _embedded_online_manual_id(text: str) -> str | None:
    pair = re.search(
        r"id\s*=\s*(\d{6,})\s*(?:&|&amp;)\s*id\s*=\s*(\d{6,})",
        text,
        re.I,
    )
    if pair:
        return pair.group(2)

    pair = re.search(r"id\s*=\s*(\d{6,}).{0,80}?id\s*=\s*(\d{6,})", text, re.I)
    return pair.group(2) if pair else None


def _online_manual_url(identity: ProductIdentity, document_id: str) -> str | None:
    host = urlparse(identity.url).netloc.lower()
    if host in {"hilti.com", "www.hilti.com"}:
        return f"https://www.hilti.com/content/hilti/W1/US/en/op-man.html/{document_id}/en"
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
