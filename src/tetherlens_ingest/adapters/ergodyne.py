from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)
from tetherlens_ingest.normalize import mass_to_kg

from .anchor_attachment_common import (
    dedupe,
    d_ring_interface_claims,
    installation_method_claim,
    installation_path_claim,
    claim,
)
from .base import ManufacturerAdapter
from .common import bounded_record_for_identifier, page_text


_EXTRACTOR = "ergodyne.v0.2"
_ANCHOR_INSTRUCTIONS_URL = (
    "https://www.ergodyne.com/sites/default/files/2022-11/"
    "squids-3171-3172-3174-3176-3177-anchor-straps-instructions.pdf"
)
_BUCKET_HOOK_INSTRUCTIONS_URL = (
    "https://www.ergodyne.com/sites/default/files/2022-11/"
    "squids-3178-locking-bucket-hook-instructions.pdf"
)
_ITEM_NUMBER = re.compile(r"\bItem\s*#\s*:?\s*(?P<sku>\d+)\b", re.I)
_PRODUCT_CAPACITY = re.compile(
    r"\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>lb|lbs?|kg|kgs?)\s*(?:/\s*\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?))?\s+maximum\s+(?:working\s+)?capacity\b",
    re.I,
)
_D_RING = re.compile(r"\b(?:durable\s+steel\s+|captive\s+)?D[-\s]?ring\b", re.I)
_ENCLOSED_TETHERING_POINT = re.compile(r"\benclosed\s+tethering\s+point\b", re.I)
_3171_SECTION = re.compile(
    r"\b3171\s+BELT\s+LOOP\s+ANCHOR\s+INSTRUCTIONS\b(?P<section>.*?)"
    r"\b3172\s+HOOK\s*&\s*LOOP\s+ANCHOR\s+INSTRUCTIONS\b",
    re.I | re.S,
)
_THREAD_OVER = re.compile(
    r"\bmust\s+be\s+threaded\s+onto\s+an\s+open[-\s]?ended\s+Primary\s+Anchor\s+like\s+a\s+belt\b",
    re.I,
)
_BELT_PRIMARY_ANCHOR = re.compile(r"\bbelt\s+that\s+is\s+acting\s+as\s+the\s+Primary\s+Anchor\b", re.I)
_REFASTEN = re.compile(r"\bRefasten\s+and\s+secure\s+the\s+belt\b", re.I)
_3171_TABLE_ROW = re.compile(
    r"\b3171\s+Belt\s+loop\b(?P<row>.*?)(?=\b3172\s+Hook\s*&\s*loop\b)",
    re.I | re.S,
)
_3171_SIZE = re.compile(
    r"(?P<height>3(?:\.0)?)\s*in\s*/\s*7\.6\s*cm\s*x\s*"
    r"(?P<thickness>0\.5)\s*in\s*/\s*1\.3\s*cm",
    re.I,
)
_BUCKET_PRIMARY_ANCHOR = re.compile(r"\b(?:lip\s+of\s+the\s+aerial\s+bucket|aerial\s+bucket\s+lip)\b", re.I)
_BUCKET_HOOK_INSTALL = re.compile(
    r"\bPry\s+the\s+hook\s+over\s+the\s+lip\b(?P<tail>.{0,260}?)\buntil\s+it\s+snaps\s+into\s+place\b",
    re.I | re.S,
)
_BUCKET_HOOK_ITEM_MARKER = re.compile(r"\b1917[89]\b", re.I)
_BUCKET_LIP_NOMINAL_SIZE = re.compile(
    r"\bLIP\s+CAVITY\s+OF\s+HOOK\s*\(BUCKET\s+LIP\s+SIZE\)\s*(?P<gap>.{0,160}?)"
    r"\b(?P<size>\d+(?:\.\d+)?)\s*IN\b",
    re.I | re.S,
)


class ErgodyneAdapter(ManufacturerAdapter):
    """First-party Ergodyne AnchorAttachment ingestion.

    Family instruction documents are identity-scoped. The 3171 belt-loop rules and
    the 3178 bucket-hook rules stay separate, and sibling-model facts are never inherited.
    Bucket-hook size labels are retained only as nominal feature classes; they do not
    become inferred numeric fit envelopes.
    """

    manufacturer = "Ergodyne"

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        if identity.product_type != ProductType.ANCHOR_ATTACHMENT:
            return []
        if _is_verified_3171_primary(identity, source_artifact):
            return [
                SourceRequest(
                    url=_ANCHOR_INSTRUCTIONS_URL,
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    metadata={"role": "anchor_attachment_instructions"},
                )
            ]
        if _is_verified_3178_primary(identity, source_artifact):
            return [
                SourceRequest(
                    url=_BUCKET_HOOK_INSTRUCTIONS_URL,
                    source_type=SourceType.MANUFACTURER_DOCUMENT,
                    metadata={"role": "bucket_hook_instructions"},
                )
            ]
        return []

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type != ProductType.ANCHOR_ATTACHMENT:
            return []

        has_3171_primary = any(_is_verified_3171_primary(identity, artifact) for artifact in artifacts)
        has_3178_primary = any(_is_verified_3178_primary(identity, artifact) for artifact in artifacts)
        if not has_3171_primary and not has_3178_primary:
            return []

        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            if _is_verified_3171_primary(identity, artifact):
                ring = _D_RING.search(text)
                if ring is not None:
                    claims.extend(
                        d_ring_interface_claims(
                            raw_value=ring.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        )
                    )
                capacity = _PRODUCT_CAPACITY.search(text)
                if capacity is not None:
                    claims.append(
                        claim(
                            "rated_capacity_kg",
                            mass_to_kg(
                                float(capacity.group("value")),
                                capacity.group("unit"),
                            ),
                            unit="kg",
                            raw_value=capacity.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        )
                    )
                continue

            if _is_verified_3178_primary(identity, artifact):
                tethering_point = _ENCLOSED_TETHERING_POINT.search(text)
                if tethering_point is not None:
                    claims.append(
                        claim(
                            "interface.role",
                            "anchor_attachment_tether_side",
                            raw_value=tethering_point.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                            subject_ref="bucket_hook_tether_connection",
                        )
                    )
                continue

            if has_3171_primary and _is_3171_instruction_artifact(artifact):
                section_match = _3171_SECTION.search(text)
                row_match = _3171_TABLE_ROW.search(text)
                if section_match is None or row_match is None:
                    continue

                section = section_match.group("section")
                thread = _THREAD_OVER.search(section)
                belt = _BELT_PRIMARY_ANCHOR.search(section)
                refasten = _REFASTEN.search(section)
                size = _3171_SIZE.search(row_match.group("row"))
                if thread is None or belt is None or refasten is None or size is None:
                    continue

                claims.extend(
                    [
                        installation_method_claim(
                            "thread_over",
                            raw_value=thread.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "belt",
                            "anchor_installation.feature_kind",
                            "belt",
                            raw_value=belt.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "belt",
                            "anchor_installation.attribute.open_for_threading",
                            True,
                            raw_value=thread.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "belt",
                            "anchor_installation.attribute.can_be_resecured",
                            True,
                            raw_value=refasten.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "belt",
                            "anchor_installation.dimension.section_height",
                            float(size.group("height")),
                            unit="in",
                            raw_value=size.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                            operator=ConstraintOperator.LTE,
                        ),
                        installation_path_claim(
                            "belt",
                            "anchor_installation.dimension.section_thickness",
                            float(size.group("thickness")),
                            unit="in",
                            raw_value=size.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                            operator=ConstraintOperator.LTE,
                        ),
                    ]
                )
                continue

            if has_3178_primary and _is_3178_instruction_artifact(artifact):
                anchor_target = _BUCKET_PRIMARY_ANCHOR.search(text)
                install = _BUCKET_HOOK_INSTALL.search(text)
                row = bounded_record_for_identifier(
                    text,
                    identity.sku,
                    _BUCKET_HOOK_ITEM_MARKER,
                )
                if anchor_target is None or install is None or row is None:
                    continue
                nominal_size = _BUCKET_LIP_NOMINAL_SIZE.search(row)
                if nominal_size is None:
                    continue

                raw_install = " ".join(install.group(0).split())
                nominal_size_class = f"{float(nominal_size.group('size')):g}_in"
                claims.extend(
                    [
                        installation_method_claim(
                            "hook_on",
                            raw_value=raw_install,
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "bucket_lip",
                            "anchor_installation.feature_kind",
                            "bucket_lip",
                            raw_value=anchor_target.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "bucket_lip",
                            "anchor_installation.attribute.nominal_lip_size",
                            nominal_size_class,
                            raw_value=nominal_size.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                    ]
                )

        return dedupe(claims)


def _is_verified_3171_primary(identity: ProductIdentity, artifact: SourceArtifact) -> bool:
    if (
        artifact.source_type != SourceType.MANUFACTURER_WEBPAGE
        or str(artifact.metadata.get("role") or "primary") != "primary"
        or not identity.sku
        or identity.sku != "19171"
    ):
        return False
    if _normalize_url(artifact.url) != _normalize_url(identity.url):
        return False

    soup = BeautifulSoup(artifact.body, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        return False
    heading_text = " ".join(heading.stripped_strings)
    if re.search(r"\bSquids\s+3171\b", heading_text, re.I) is None:
        return False

    item_numbers = {match.group("sku") for match in _ITEM_NUMBER.finditer(page_text(artifact.body))}
    return item_numbers == {identity.sku}


def _is_verified_3178_primary(identity: ProductIdentity, artifact: SourceArtifact) -> bool:
    if (
        artifact.source_type != SourceType.MANUFACTURER_WEBPAGE
        or str(artifact.metadata.get("role") or "primary") != "primary"
        or not identity.sku
    ):
        return False
    if _normalize_url(artifact.url) != _normalize_url(identity.url):
        return False

    soup = BeautifulSoup(artifact.body, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        return False
    heading_text = " ".join(heading.stripped_strings)
    if re.search(r"\bSquids\s+3178\b", heading_text, re.I) is None:
        return False

    item_numbers = {match.group("sku") for match in _ITEM_NUMBER.finditer(page_text(artifact.body))}
    return identity.sku in item_numbers


def _is_3171_instruction_artifact(artifact: SourceArtifact) -> bool:
    return bool(
        artifact.source_type == SourceType.MANUFACTURER_DOCUMENT
        and str(artifact.metadata.get("role") or "") == "anchor_attachment_instructions"
        and _normalize_url(artifact.url) == _normalize_url(_ANCHOR_INSTRUCTIONS_URL)
    )


def _is_3178_instruction_artifact(artifact: SourceArtifact) -> bool:
    return bool(
        artifact.source_type == SourceType.MANUFACTURER_DOCUMENT
        and str(artifact.metadata.get("role") or "") == "bucket_hook_instructions"
        and _normalize_url(artifact.url) == _normalize_url(_BUCKET_HOOK_INSTRUCTIONS_URL)
    )


def _normalize_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, parts.query, ""))
