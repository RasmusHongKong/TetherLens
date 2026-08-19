from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, ProductType, SourceArtifact
from tetherlens_ingest.normalize import opening_action_count, parse_length_range_mm, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


class NLGAdapter(ManufacturerAdapter):
    manufacturer = "NLG"

    def discover_collection(self, artifact: SourceArtifact) -> list[ProductIdentity]:
        """Turn a manufacturer collection payload into canonical product candidates.

        NLG currently exposes Shopify-style collection data, where SKU is normally a
        variant field rather than a product-level field. Preserve each distinct SKU as
        a candidate identity so catalogue enumeration does not silently discard the
        identifier needed to bind later evidence.
        """
        payload = json.loads(artifact.body)
        rows: Iterable[Any]
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("products") or payload.get("items") or payload.get("results") or []
        else:
            rows = []

        identities: list[ProductIdentity] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = row.get("title") or row.get("name")
            url = row.get("url") or row.get("product_url")
            handle = row.get("handle")
            if not url and handle:
                url = f"/products/{handle}"
            if not title or not url:
                continue
            url = urljoin(artifact.url, str(url))

            product_id = row.get("id")
            variants = row.get("variants")
            variant_rows = variants if isinstance(variants, list) else []
            sku_variants = [
                variant for variant in variant_rows
                if isinstance(variant, dict) and variant.get("sku")
            ]

            if sku_variants:
                for variant in sku_variants:
                    manufacturer_ids = {}
                    if product_id is not None:
                        manufacturer_ids["id"] = str(product_id)
                    if variant.get("id") is not None:
                        manufacturer_ids["variant_id"] = str(variant["id"])
                    identities.append(
                        ProductIdentity(
                            manufacturer=self.manufacturer,
                            name=str(title),
                            sku=str(variant["sku"]),
                            url=url,
                            manufacturer_ids=manufacturer_ids,
                        )
                    )
                continue

            manufacturer_ids = {
                key: str(row[key])
                for key in ("id", "variant_id")
                if row.get(key) is not None
            }
            identities.append(
                ProductIdentity(
                    manufacturer=self.manufacturer,
                    name=str(title),
                    sku=str(row.get("sku")) if row.get("sku") else None,
                    url=url,
                    manufacturer_ids=manufacturer_ids,
                )
            )
        return _dedupe_identities(identities)

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if "json" in artifact.content_type:
                continue
            text = page_text(artifact.body)

            mass_match = re.search(r"Max(?:imum)?\s+Load\s*:\s*([^\n]+)", text, re.I)
            if mass_match and (q := parse_mass(mass_match.group(1))):
                claims.append(self._claim("rated_capacity_kg", q.value, "kg", mass_match.group(1), artifact.url))

            # Length has product-level tether semantics only for a Tether. Other NLG
            # products publish ranges such as belt adjustment, which must not become
            # tether min/max length.
            if identity.product_type == ProductType.TETHER and (lengths := parse_length_range_mm(text)):
                length_raw = _first_length_range(text)
                claims.extend([
                    self._claim("min_length_mm", lengths[0], "mm", length_raw, artifact.url),
                    self._claim("max_length_mm", lengths[1], "mm", length_raw, artifact.url),
                ])

            if identity.product_type == ProductType.TETHER:
                claims.extend(self._extract_tether_interfaces(text, artifact.url))

            if identity.product_type == ProductType.TOOL_ATTACHMENT:
                claims.extend(self._extract_tool_attachment_interfaces(text, artifact.url))

            # NLG commonly publishes fixed product dimensions and a separate maximum
            # permitted lanyard length for attachment products. Keep these distinct
            # from tether extension length.
            if dimensions := _dimension_pair_mm(text):
                raw, length_mm, width_mm = dimensions
                claims.extend([
                    self._claim("dimensions.length_mm", length_mm, "mm", raw, artifact.url),
                    self._claim("dimensions.width_mm", width_mm, "mm", raw, artifact.url),
                ])

            if max_lanyard := _max_lanyard_length_mm(text):
                raw, value_mm = max_lanyard
                if identity.product_type == ProductType.CONTAINER:
                    claims.append(self._claim(
                        "max_lanyard_length_mm",
                        value_mm,
                        "mm",
                        raw,
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "internal_anchor",
                    ))
                elif identity.product_type == ProductType.TOOL_ATTACHMENT:
                    claims.append(self._claim("max_lanyard_length_mm", value_mm, "mm", raw, artifact.url))

            # Opening-action terminology is only mapped to the tether connector on
            # tether product pages. A triple-action belt buckle is not a connector.
            if identity.product_type == ProductType.TETHER:
                actions = opening_action_count(text)
                if actions:
                    claims.append(self._claim(
                        "connector.opening_action_count",
                        actions,
                        None,
                        _first_action_phrase(text),
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        "tether_connector",
                    ))

                if re.search(r"automatic\s+(?:twist[- ]?lock|twistlock)\s+carabiner|auto(?:matic)?[- ]locking\s+carabiner", text, re.I):
                    claims.append(self._claim(
                        "connector.locking_mode",
                        "auto_locking",
                        None,
                        _first_matching_line(text, r"automatic|auto(?:matic)?[- ]locking"),
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        "tether_connector",
                    ))

            if re.search(r"360\s*[°º].{0,20}(?:rot|swivel)|(?:rot|swivel).{0,20}360\s*[°º]", text, re.I | re.S):
                subject_type = ClaimSubjectType.CONNECTOR_SPEC if identity.product_type == ProductType.TETHER else ClaimSubjectType.PHYSICAL_INTERFACE
                subject_ref = "tether_connector" if identity.product_type == ProductType.TETHER else "rotating_interface"
                claims.append(self._claim(
                    "connector.swivel",
                    True,
                    None,
                    "360 degree rotating/swivel interface",
                    artifact.url,
                    subject_type,
                    subject_ref,
                ))

            if re.search(r"climbing cord loop|loop allows|loop tool tether", text, re.I):
                claims.append(self._claim(
                    "interface.loop_present",
                    True,
                    None,
                    "loop",
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "loop_interface",
                ))

            # The MEWP Bag page distinguishes the overall bag rating from the load
            # and lanyard-length constraint of each internal tether point. Preserve
            # those as interface claims rather than bag-level properties.
            if identity.product_type == ProductType.CONTAINER:
                anchor_match = re.search(r"(?:anchor|daisy chain).{0,80}?(\d+(?:\.\d+)?)\s*(kg|lb)s?", text, re.I | re.S)
                if anchor_match and (q := parse_mass(anchor_match.group(0))):
                    claims.append(self._claim(
                        "rated_capacity_kg",
                        q.value,
                        "kg",
                        anchor_match.group(0),
                        artifact.url,
                        ClaimSubjectType.PHYSICAL_INTERFACE,
                        "internal_anchor",
                    ))
        return _dedupe(claims)

    def _extract_tether_interfaces(self, text: str, url: str) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []

        # Quantity words must directly describe the connector noun. This deliberately
        # excludes phrases such as "a dual action carabiner", where "dual" describes
        # the opening action rather than the number of carabiners.
        dual_carabiner = re.search(
            r"\b(?:dual|double|twin|two)\s+(?:360\s*[°º]\s*)?(?:rotobiners?|carabiners?)\b",
            text,
            re.I,
        )
        loop_to_carabiner = re.search(
            r"(?:one|an?)\s+end.{0,180}?(?:dyneema[^\n]{0,30})?loop.{0,220}?(?:other|another)\s+(?:end\s+)?(?:it\s+)?(?:features?\s+)?(?:a\s+)?[^\n]{0,80}?(?:rotobiner|carabiner)",
            text,
            re.I | re.S,
        )
        carabiner_to_loop = re.search(
            r"(?:one|an?)\s+end.{0,180}?(?:rotobiner|carabiner).{0,220}?(?:other|another)\s+(?:end\s+)?(?:it\s+)?(?:features?\s+)?(?:a\s+)?[^\n]{0,80}?loop",
            text,
            re.I | re.S,
        )
        carabiner_one_end_to_loop_other = re.search(
            r"(?:rotobiner|carabiner).{0,140}?(?:at\s+)?(?:the\s+)?one\s+end.{0,240}?loop.{0,140}?(?:at\s+)?(?:the\s+)?other\s+end",
            text,
            re.I | re.S,
        )
        loop_one_end_to_carabiner_other = re.search(
            r"loop.{0,140}?(?:at\s+)?(?:the\s+)?one\s+end.{0,240}?(?:rotobiner|carabiner).{0,140}?(?:at\s+)?(?:the\s+)?other\s+end",
            text,
            re.I | re.S,
        )

        if dual_carabiner:
            claims.append(self._claim("tether.connection_count", 2, None, dual_carabiner.group(0), url))
            for endpoint in ("tether_endpoint_1", "tether_endpoint_2"):
                claims.append(self._claim(
                    "interface.type",
                    "carabiner",
                    None,
                    dual_carabiner.group(0),
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    endpoint,
                ))
        elif loop_to_carabiner or loop_one_end_to_carabiner_other:
            match = loop_to_carabiner or loop_one_end_to_carabiner_other
            raw = match.group(0) if match else None
            claims.append(self._claim("tether.connection_count", 2, None, raw, url))
            claims.extend([
                self._claim(
                    "interface.type",
                    "loop",
                    None,
                    raw,
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tether_endpoint_1",
                ),
                self._claim(
                    "interface.type",
                    "carabiner",
                    None,
                    raw,
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tether_endpoint_2",
                ),
            ])
        elif carabiner_to_loop or carabiner_one_end_to_loop_other:
            match = carabiner_to_loop or carabiner_one_end_to_loop_other
            raw = match.group(0) if match else None
            claims.append(self._claim("tether.connection_count", 2, None, raw, url))
            claims.extend([
                self._claim(
                    "interface.type",
                    "carabiner",
                    None,
                    raw,
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tether_endpoint_1",
                ),
                self._claim(
                    "interface.type",
                    "loop",
                    None,
                    raw,
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tether_endpoint_2",
                ),
            ])

        return claims

    def _extract_tool_attachment_interfaces(self, text: str, url: str) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []

        interface_type: str | None = None
        raw_interface: str | None = None
        if match := re.search(r"\bD[ -]?Ring\b", text, re.I):
            interface_type, raw_interface = "d_ring", match.group(0)
        elif match := re.search(r"\bV\s*Ring\b", text, re.I):
            interface_type, raw_interface = "v_ring", match.group(0)
        elif match := re.search(r"\bTether\s+Shackle\b|\bshackle\b", text, re.I):
            interface_type, raw_interface = "shackle", match.group(0)

        if interface_type:
            claims.append(self._claim(
                "interface.type",
                interface_type,
                None,
                raw_interface,
                url,
                ClaimSubjectType.PHYSICAL_INTERFACE,
                "lanyard_interface",
            ))

        if match := re.search(r"(?:paired|used)\s+with\s+Tether\s+Tape|Tether\s+Tape.{0,60}(?:D[ -]?Ring|D Ring)", text, re.I | re.S):
            claims.append(self._claim(
                "interface.attachment_method",
                "tether_tape",
                None,
                match.group(0),
                url,
                ClaimSubjectType.PHYSICAL_INTERFACE,
                "tool_attachment_interface",
            ))

        if match := re.search(r"cinch(?:ed|es|ing)?\s+around\s+(?:a\s+)?captive\s+handle\s+or\s+hole", text, re.I):
            claims.append(self._claim(
                "interface.attachment_method",
                "cinch",
                None,
                match.group(0),
                url,
                ClaimSubjectType.PHYSICAL_INTERFACE,
                "tool_attachment_interface",
            ))
            claims.extend([
                self._claim(
                    "interface.compatible_tool_feature",
                    "captive_handle",
                    None,
                    match.group(0),
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tool_attachment_interface",
                ),
                self._claim(
                    "interface.compatible_tool_feature",
                    "captive_hole",
                    None,
                    match.group(0),
                    url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "tool_attachment_interface",
                ),
            ])

        if match := re.search(r"tapered\s+tools?|narrower\s+mid[- ]section|\bwaist\b", text, re.I):
            claims.append(self._claim(
                "interface.compatible_tool_feature",
                "tapered_profile",
                None,
                match.group(0),
                url,
                ClaimSubjectType.PHYSICAL_INTERFACE,
                "tool_attachment_interface",
            ))

        if match := re.search(r"pre[- ]manufactured\s+hole", text, re.I):
            claims.append(self._claim(
                "interface.compatible_tool_feature",
                "pre_manufactured_hole",
                None,
                match.group(0),
                url,
                ClaimSubjectType.PHYSICAL_INTERFACE,
                "tool_attachment_interface",
            ))

        return claims

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
            extractor="nlg.v0.3",
        )


def _first_length_range(text: str) -> str | None:
    m = re.search(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")?\s*(?:to|[-–])\s*\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")", text, re.I)
    return m.group(0) if m else None


def _first_action_phrase(text: str) -> str | None:
    m = re.search(r"(?:single|dual|double|triple|one|two|three)[ -]?(?:stage|action)", text, re.I)
    return m.group(0) if m else None


def _first_matching_line(text: str, pattern: str) -> str | None:
    return next((line for line in text.splitlines() if re.search(pattern, line, re.I)), None)


def _dimension_pair_mm(text: str) -> tuple[str, float, float] | None:
    match = re.search(
        r"Dimensions\s*:\s*(\d+(?:\.\d+)?)\s*mm\s*\(L\)\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm\s*\(W\)",
        text,
        re.I,
    )
    if not match:
        return None
    return match.group(0), float(match.group(1)), float(match.group(2))


def _max_lanyard_length_mm(text: str) -> tuple[str, float] | None:
    match = re.search(r"Max\s+Lanyard\s+Length\s*:\s*([^\n]+)", text, re.I)
    if not match:
        return None
    metric = re.search(r"(\d+(?:\.\d+)?)\s*(mm|cm|m)\b", match.group(1), re.I)
    if not metric:
        return None
    value = float(metric.group(1))
    unit = metric.group(2).lower()
    factor = {"mm": 1.0, "cm": 10.0, "m": 1000.0}[unit]
    return match.group(0), value * factor


def _dedupe_identities(identities: list[ProductIdentity]) -> list[ProductIdentity]:
    seen: set[tuple[str, str | None]] = set()
    out: list[ProductIdentity] = []
    for identity in identities:
        key = (identity.url, identity.sku)
        if key not in seen:
            out.append(identity)
            seen.add(key)
    return out


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (claim.subject_type.value, claim.subject_ref, claim.property_key, str(claim.value))
        if key not in seen:
            out.append(claim)
            seen.add(key)
    return out
