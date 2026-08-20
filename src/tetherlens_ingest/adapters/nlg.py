from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType, ProductIdentity, ProductType, SourceArtifact
from tetherlens_ingest.normalize import length_to_mm, opening_action_count, parse_length_range_mm, parse_mass
from .base import ManufacturerAdapter
from .common import page_text


_FULL_ROTATION = r"360\s*(?:[°º]|degrees?)"


class NLGAdapter(ManufacturerAdapter):
    manufacturer = "NLG"

    def discover_collection(self, artifact: SourceArtifact) -> list[ProductIdentity]:
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
                variant
                for variant in variant_rows
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
                topology_claims = _tether_topology_claims(identity, text, artifact.url)
                claims.extend(topology_claims)

                connection_count = _tether_connection_count(identity, text)
                topology_count = len({
                    claim.subject_ref
                    for claim in topology_claims
                    if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
                    and claim.property_key == "connection_point.interface_type"
                })
                if topology_count >= 2:
                    connection_count = max(connection_count or 0, topology_count)
                if connection_count:
                    claims.append(self._claim(
                        "tether.connection_count",
                        connection_count,
                        None,
                        "explicit tether endpoint/multiplicity terminology",
                        artifact.url,
                    ))

                connector_ref = _tether_connector_subject_ref(text)
                actions = opening_action_count(text)
                if actions:
                    claims.append(self._claim(
                        "connector.opening_action_count",
                        actions,
                        None,
                        _first_action_phrase(text),
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        connector_ref,
                    ))

                if swivel_ref := _tether_swivel_connector_subject_ref(text):
                    claims.append(self._claim(
                        "connector.swivel",
                        True,
                        None,
                        "360 degree connector rotation",
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        swivel_ref,
                    ))
            elif re.search(
                rf"{_FULL_ROTATION}.{{0,20}}(?:rot|swivel)|(?:rot|swivel).{{0,20}}{_FULL_ROTATION}",
                text,
                re.I | re.S,
            ):
                claims.append(self._claim(
                    "connector.swivel",
                    True,
                    None,
                    "360 degree rotating/swivel interface",
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "rotating_interface",
                ))

            # Loops on non-tether products remain physical interfaces. Tether loops
            # are represented by explicit TetherConnectionPoint subjects instead.
            if identity.product_type != ProductType.TETHER and re.search(
                r"climbing cord loop|loop allows|loop tool tether",
                text,
                re.I,
            ):
                claims.append(self._claim(
                    "interface.loop_present",
                    True,
                    None,
                    "loop",
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "loop_interface",
                ))

            # "Max Lanyard Length" is a pairing/use constraint on an attachment,
            # anchor or container. It is deliberately distinct from a tether's own
            # physical min/max length.
            if identity.product_type != ProductType.TETHER and (lanyard_limit := _max_lanyard_length_mm(text)):
                claims.append(self._claim(
                    "max_lanyard_length_mm",
                    lanyard_limit[0],
                    "mm",
                    lanyard_limit[1],
                    artifact.url,
                ))

            # Preserve an interface-specific rating separately from a belt's overall
            # load. This phrase-based rule is intentionally scoped to an explicitly
            # named bottom D-ring interface rather than any nearby load value.
            if bottom_d_ring := _bottom_d_ring_capacity(text):
                claims.append(self._claim(
                    "rated_capacity_kg",
                    bottom_d_ring[0],
                    "kg",
                    bottom_d_ring[1],
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "bottom_d_ring",
                ))

            # A manufacturer usage recommendation is not the same thing as a rated
            # capacity. Preserve the webpage statement as a candidate claim; evidence
            # reconciliation may still reject it if another first-party source conflicts.
            if identity.product_type == ProductType.ANCHOR_ATTACHMENT and (wrist_limit := _wrist_recommended_mass(text)):
                claims.append(self._claim(
                    "max_recommended_attached_mass_kg",
                    wrist_limit[0],
                    "kg",
                    wrist_limit[1],
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "wrist_anchor",
                ))

            # NLG container pages distinguish the overall bag rating from the load
            # of each internal tether point. Preserve those as separate subjects.
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
            extractor="nlg.v0.5",
        )


def _tether_topology_claims(identity: ProductIdentity, text: str, url: str) -> list[CandidateClaim]:
    search_text = f"{identity.name or ''}\n{text}"
    claims: list[CandidateClaim] = []

    def point(ref: str, interface_type: str, raw: str, role: str | None = None, connector_spec_ref: str | None = None) -> None:
        claims.append(NLGAdapter._claim(
            "connection_point.interface_type",
            interface_type,
            None,
            raw,
            url,
            ClaimSubjectType.TETHER_CONNECTION_POINT,
            ref,
        ))
        if role:
            claims.append(NLGAdapter._claim(
                "connection_point.role",
                role,
                None,
                raw,
                url,
                ClaimSubjectType.TETHER_CONNECTION_POINT,
                ref,
            ))
        if connector_spec_ref:
            claims.append(NLGAdapter._claim(
                "connection_point.connector_spec_ref",
                connector_spec_ref,
                None,
                raw,
                url,
                ClaimSubjectType.TETHER_CONNECTION_POINT,
                ref,
            ))

    # Role is only emitted when the copy itself establishes which endpoint is for
    # the anchor/belt and which is for tool attachment.
    explicit_roles = re.search(
        r"integral\s+carabiner.{0,50}(?:belt|anchor).{0,80}rotobiner.{0,50}tool\s+attachment",
        text,
        re.I | re.S,
    )
    if explicit_roles:
        raw = explicit_roles.group(0)
        point("anchor_side", "carabiner", raw, "anchor_side", "anchor_carabiner")
        point("tool_side", "carabiner", raw, "tool_side", "tool_rotobiner")
        return claims

    has_loop = bool(re.search(r"climbing cord loop|loop allows|loop tool tether", search_text, re.I))
    has_rotobiner = bool(re.search(r"\brotobiner\b", search_text, re.I))
    if has_loop and has_rotobiner:
        rotobiner_role = "either" if _interface_supports_either_role(search_text, r"\brotobiner\b") else None
        loop_role = "either" if _interface_supports_either_role(
            search_text,
            r"(?:climbing\s+cord\s+loop|cord\s+loop|\bloop\b)",
        ) else None
        point("connection_point_1", "carabiner", "Rotobiner", rotobiner_role, "rotobiner")
        point("connection_point_2", "loop", "loop", loop_role)
        return claims

    if re.search(
        r"\b(?:dual|double|twin)(?![-\s]+action\b)\s+(?:\w+[\s™®-]+){0,2}quick\s*clips?\b",
        search_text,
        re.I,
    ):
        point("connection_point_1", "clip", "dual/double quick clips", connector_spec_ref="quick_clip")
        point("connection_point_2", "clip", "dual/double quick clips", connector_spec_ref="quick_clip")
        return claims

    if re.search(
        r"\b(?:dual|double|twin)(?![-\s]+action\b)\s+(?:\w+[\s™®-]+){0,2}carabiners?\b",
        search_text,
        re.I,
    ) or re.search(r"\bcarabiners?\b.{0,40}\b(?:at|on)\s+(?:each|both)\s+ends?\b", search_text, re.I | re.S):
        point("connection_point_1", "carabiner", "double/dual carabiner", connector_spec_ref="tether_connector")
        point("connection_point_2", "carabiner", "double/dual carabiner", connector_spec_ref="tether_connector")

    return claims


def _interface_supports_either_role(text: str, interface_pattern: str) -> bool:
    for match in re.finditer(interface_pattern, text, re.I | re.S):
        window = text[match.start():match.end() + 220]
        if (
            re.search(r"\b(?:attach\w*|connect\w*)\b", window, re.I)
            and re.search(r"\btool\b", window, re.I)
            and re.search(r"\banchor\b", window, re.I)
            and re.search(r"\bor\b", window, re.I)
        ):
            return True
    return False


def _tether_swivel_connector_subject_ref(text: str) -> str | None:
    connector_patterns = (
        (r"\brotobiner\b", _tether_connector_subject_ref(text)),
        (r"\bquick\s*clips?\b", "quick_clip"),
        (r"\bcarabiners?\b", "tether_connector"),
        (r"\bconnectors?\b", "tether_connector"),
    )
    for connector_pattern, subject_ref in connector_patterns:
        if re.search(
            rf"(?:{_FULL_ROTATION}.{{0,24}}{connector_pattern}|{connector_pattern}.{{0,24}}{_FULL_ROTATION})",
            text,
            re.I | re.S,
        ):
            return subject_ref

    if re.search(
        rf"{_FULL_ROTATION}.{{0,24}}(?:rotat|swivel)|(?:rotat|swivel).{{0,24}}{_FULL_ROTATION}",
        text,
        re.I | re.S,
    ):
        return _tether_connector_subject_ref(text)
    return None


def _tether_connector_subject_ref(text: str) -> str:
    if re.search(r"rotobiner.{0,50}tool\s+attachment", text, re.I | re.S):
        return "tool_rotobiner"
    if re.search(r"\brotobiner\b", text, re.I):
        return "rotobiner"
    return "tether_connector"


def _tether_connection_count(identity: ProductIdentity, text: str) -> int | None:
    search_text = f"{identity.name or ''}\n{text}"
    # Do not confuse "double-action" / "dual-action" gate terminology with
    # a count of connectors. Count only explicit multiplicity/interface wording.
    if re.search(
        r"\b(?:dual|double|twin)(?![-\s]+action\b)\s+(?:\w+[\s™®-]+){0,2}"
        r"(?:carabiners?|connectors?|quick\s*clips?|attachment\s+points?)\b",
        search_text,
        re.I,
    ):
        return 2
    if re.search(
        r"\b(?:carabiners?|connectors?|quick\s*clips?)\b.{0,40}\b(?:at|on)\s+(?:each|both)\s+ends?\b",
        search_text,
        re.I | re.S,
    ):
        return 2
    return None


def _max_lanyard_length_mm(text: str) -> tuple[float, str] | None:
    match = re.search(
        r"\bMax(?:imum)?\s+Lanyard\s+Length\s*:\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m|inches|inch|in|\")",
        text,
        re.I,
    )
    if not match:
        return None
    value = round(length_to_mm(float(match.group("value")), match.group("unit")), 3)
    return value, match.group(0)


def _bottom_d_ring_capacity(text: str) -> tuple[float, str] | None:
    match = re.search(
        r"\bbottom\s+d[\s-]*rings?\b.{0,80}?\bload\s+rating\s*:?\s*"
        r"\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?)\b",
        text,
        re.I | re.S,
    )
    if not match or not (quantity := parse_mass(match.group(0))):
        return None
    return quantity.value, match.group(0)


def _wrist_recommended_mass(text: str) -> tuple[float, str] | None:
    match = re.search(
        r"\brecommend\b.{0,60}?\bmaximum\s+weight\b.{0,100}?\bwrist\b.{0,40}?"
        r"\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?)\b",
        text,
        re.I | re.S,
    )
    if not match or not (quantity := parse_mass(match.group(0))):
        return None
    return quantity.value, match.group(0)


def _first_length_range(text: str) -> str | None:
    m = re.search(r"\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")?\s*(?:to|[-–])\s*\d+(?:\.\d+)?\s*(?:mm|cm|m|in(?:ches)?|\")", text, re.I)
    return m.group(0) if m else None


def _first_action_phrase(text: str) -> str | None:
    m = re.search(r"(?:single|dual|double|triple|one|two|three)[ -]?(?:stage|action)", text, re.I)
    return m.group(0) if m else None


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
