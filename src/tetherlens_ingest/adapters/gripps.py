from __future__ import annotations

import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.normalize import mass_to_kg
from tetherlens_ingest.reconciliation import mass_claims_semantically_agree

from .anchor_attachment_common import (
    claim as anchor_claim,
    installation_method_claim,
    installation_path_claim,
)
from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "gripps.v0.5"

_LOAD_RATING = re.compile(
    r"\b(?:max(?:imum)?\s+load|load\s+rating(?:\s+of)?(?:\s+up\s+to)?)\b\s*:?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs?|lb|lbs?)\b"
    r"(?:\s*[/|]\s*\d+(?:\.\d+)?\s*(?:kg|kgs?|lb|lbs?)\b)?",
    re.I,
)
_DIRECTIONAL_CARABINERS = re.compile(
    r"\bdedicated\s+anchor\s+end\b.{0,80}?\blarge\s+carabiner\b"
    r".{0,160}?\bdedicated\s+tool\s+end\b.{0,80}?\bsmall\s+carabiner\b",
    re.I | re.S,
)
_DUAL_ACTION_BOTH_ENDS = re.compile(
    r"\bdual[-\s]?action\s+carabiners?\s+(?:at|on)\s+both\s+ends?\b",
    re.I,
)
_SNAPLOCK_SELF_CLOSING = re.compile(r"\bself[-\s]?closing\s+(?:tool\s+)?connector\b", re.I)
_SNAPLOCK_HANDLE_OR_NECK = re.compile(
    r"\binstallation\s+to\s+a\s+tool[’']s\s+handle\s+or\s+neck\b",
    re.I,
)
_SNAPLOCK_CONNECTION_POINT = re.compile(
    r"\bprovides\s+a\s+secure,?\s+standardi[sz]ed\s+connection\s+point\s+for\s+tethering\b",
    re.I,
)
_WRIST_TARGET = re.compile(r"\bcan\s+be\s+attached\s+to\s+hand\s+rails\s+or\s+your\s+wrist\b", re.I)
_WRIST_FASTENING = re.compile(
    r"\bindustrial[-\s]?grade\s+velcro\s+adjusts\s+diameter\s+to\s+suit\s+any\s+wrist\s+or\s+rail\s+size\b",
    re.I,
)
_LOAD_RATED_TETHER_ANCHOR = re.compile(r"\bbuilt[-\s]?in,?\s+load[-\s]?rated\s+tether\s+anchor\b", re.I)
_H01067_CARABINER_PAIR = re.compile(
    r"\btwo\s+swivel[-\s]?head\s+single[-\s]?action\s+carabiners?\b",
    re.I,
)
_H01067_TOOL_TO_WRIST_USE = re.compile(
    r"\battachment\s+of\s+hand\s+tools\s+to\b.{0,100}\b(?:gloves?|wrist\s+anchors?)\b",
    re.I | re.S,
)
_H01067_DIRECTIONAL_SPLIT = re.compile(
    r"(?:"
    r"\b(?:dedicated|designated|tool[-\s]?side|anchor[-\s]?side|tool\s+end|anchor\s+end)\b"
    r".{0,80}\bcarabiners?\b"
    r"|"
    r"\bcarabiners?\b.{0,80}"
    r"\b(?:dedicated|designated|tool[-\s]?side|anchor[-\s]?side|tool\s+end|anchor\s+end)\b"
    r")",
    re.I | re.S,
)
_H01085_WRIST_CONTEXT = re.compile(
    r"\b(?:slip[-\s]?on\s+wrist\s+anchor|wrist[-\s]?mounted\s+tether\s+anchor)\b",
    re.I,
)
_H01085_SLIP_ACTION = re.compile(
    r"\b(?:just\s+)?slip\s+(?:it|the\s+wrist[-\s]?anchor)\s+"
    r"(?:on|over\s+the\s+hand\s+onto\s+the\s+wrist)\b",
    re.I,
)
_H01085_H01067_ENDORSEMENT = re.compile(
    r"\bsuitable\s+for\s+use\s+with\s+our\b[^.;!?]{0,120}\bH01067\b"
    r"[^.;!?]{0,80}\bwrist\s+tethers?\b",
    re.I,
)
_H01085_H01067_IN_MATCH_EXCLUSION = re.compile(
    r"(?:"
    r"\b(?:but\s+not|not|except(?:ing)?|excluding?|other\s+than)\b"
    r"[^.;!?]{0,60}\bH01067\b"
    r"|"
    r"\bH01067\b[^.;!?]{0,60}"
    r"\b(?:is\s+not|isn't|not|never|except(?:ed)?|excluded)\b"
    r")",
    re.I,
)
_H01085_POST_ENDORSEMENT_PROHIBITION = re.compile(
    r"\b(?:but|however|yet|although|though)\b.{0,120}"
    r"\b(?:"
    r"(?:must|should|shall|may|can)\s+not|"
    r"cannot|can't|"
    r"(?:do|does|did)\s+not|"
    r"never"
    r")\b.{0,80}"
    r"\b(?:use|used|using|attach|attached|connect|connected|tether|tethered)\b",
    re.I | re.S,
)
_H01085_ADJACENT_PROHIBITION = re.compile(
    r"^\s*[.!?]\s*"
    r"(?:\b(?:but|however|yet|although|though)\b[,:]?\s*)?"
    r"(?:"
    r"(?:must|should|shall|may|can)\s+not|"
    r"cannot|can't|"
    r"(?:do|does|did)\s+not|"
    r"never"
    r")\b.{0,80}"
    r"\b(?:use|used|using|attach|attached|connect|connected|tether|tethered)\b",
    re.I | re.S,
)


class GRIPPSAdapter(ManufacturerAdapter):
    """Extract GRIPPS evidence into existing manufacturer-neutral primitives.

    Tether direction is emitted only when the manufacturer explicitly distinguishes the
    anchor and tool ends. ToolAttachment installation remains equally evidence-bound:
    SnapLock's published ``handle or neck`` wording compiles only the independently
    established handle subset. ``neck`` is not widened to an external-section path and
    S/M/L/XL labels never become inferred dimensions.

    Worker-worn AnchorAttachments follow the same rule. Adjustable/all-sizes wrist
    wording can establish an evidence-backed fastening mechanism and wrist/rail targets,
    but it never becomes a numeric fit envelope.
    """

    manufacturer = "GRIPPS"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        relationship_claims = _extract_declared_relationship_claims(identity, artifacts)
        compatibility_claims = _extract_connection_compatibility_claims(identity, artifacts)

        if identity.product_type == ProductType.TETHER:
            component_claims = self._extract_tether(identity, artifacts)
        elif identity.product_type == ProductType.TOOL_ATTACHMENT:
            component_claims = self._extract_tool_attachment(artifacts)
        elif identity.product_type == ProductType.ANCHOR_ATTACHMENT:
            component_claims = self._extract_anchor_attachment(identity, artifacts)
        else:
            component_claims = []

        return _dedupe([*relationship_claims, *compatibility_claims, *component_claims])

    def _extract_tether(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if _base_sku(identity.sku) == "H01067":
                if not _is_verified_product_detail(artifact, identity):
                    continue
                product_text = _product_local_text(artifact.body, identity)
                claims.extend(_capacity_claims(product_text, artifact.url))
                claims.extend(_h01067_tether_claims(product_text, artifact.url))
                continue

            text = page_text(artifact.body)
            claims.extend(_capacity_claims(text, artifact.url))

            directional = _DIRECTIONAL_CARABINERS.search(text)
            if directional is None:
                continue

            directional_raw = directional.group(0)
            claims.append(_claim(
                "tether.connection_count",
                2,
                None,
                directional_raw,
                artifact.url,
            ))
            claims.extend(_directional_endpoint_claims(directional_raw, artifact.url))

            dual_action = _DUAL_ACTION_BOTH_ENDS.search(text)
            if dual_action is not None:
                for connector_ref in ("anchor_carabiner", "tool_carabiner"):
                    claims.append(_claim(
                        "connector.opening_action_count",
                        2,
                        None,
                        dual_action.group(0),
                        artifact.url,
                        ClaimSubjectType.CONNECTOR_SPEC,
                        connector_ref,
                    ))

        return _dedupe(claims)

    def _extract_tool_attachment(
        self,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            text = page_text(artifact.body)
            claims.extend(_capacity_claims(text, artifact.url))

            retaining_action = _SNAPLOCK_SELF_CLOSING.search(text)
            installation = _SNAPLOCK_HANDLE_OR_NECK.search(text)
            if retaining_action is None or installation is None:
                continue

            # The source establishes handle installation as one explicit alternative.
            # It does not establish that the handle must be non-captive, nor does its
            # separate word "neck" establish executable external-section semantics.
            claims.extend([
                _claim(
                    "attachment_selection_class",
                    "handle_attachment",
                    None,
                    installation.group(0),
                    artifact.url,
                ),
                _claim(
                    "attachment_method_code",
                    "mechanical_capture",
                    None,
                    retaining_action.group(0),
                    artifact.url,
                ),
            ])

            connection_point = _SNAPLOCK_CONNECTION_POINT.search(text)
            if connection_point is not None:
                # The page establishes a ToolAttachment-provided tether connection point
                # but does not establish a connector/interface form. Preserve that
                # structural role without inventing a ring, carabiner, or other type.
                claims.append(_claim(
                    "interface.role",
                    "tool_attachment_tether_side",
                    None,
                    connection_point.group(0),
                    artifact.url,
                    ClaimSubjectType.PHYSICAL_INTERFACE,
                    "snaplock_tether_connection",
                ))

        return _dedupe(claims)

    def _extract_anchor_attachment(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
            if not _is_verified_product_detail(artifact, identity):
                continue

            product_text = _product_local_text(artifact.body, identity)
            claims.extend(_capacity_claims(product_text, artifact.url))

            if _base_sku(identity.sku) == "H01085":
                slip_action = _affirmative_search(_H01085_SLIP_ACTION, product_text)
                wrist_context = _H01085_WRIST_CONTEXT.search(product_text)
                if slip_action is not None and wrist_context is not None:
                    raw = f"{wrist_context.group(0)}; {slip_action.group(0)}"
                    claims.extend(
                        [
                            installation_method_claim(
                                "slip_on",
                                raw_value=raw,
                                source_url=artifact.url,
                                extractor=_EXTRACTOR,
                            ),
                            installation_path_claim(
                                "wrist",
                                "anchor_installation.feature_kind",
                                "wrist",
                                raw_value=raw,
                                source_url=artifact.url,
                                extractor=_EXTRACTOR,
                            ),
                        ]
                    )

            target = _WRIST_TARGET.search(product_text)
            fastening = _WRIST_FASTENING.search(product_text)
            if target is not None and fastening is not None:
                claims.extend(
                    [
                        installation_method_claim(
                            "fasten_around",
                            raw_value=fastening.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "wrist",
                            "anchor_installation.feature_kind",
                            "wrist",
                            raw_value=target.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                        installation_path_claim(
                            "rail",
                            "anchor_installation.feature_kind",
                            "rail",
                            raw_value=target.group(0),
                            source_url=artifact.url,
                            extractor=_EXTRACTOR,
                        ),
                    ]
                )

            tether_anchor = _LOAD_RATED_TETHER_ANCHOR.search(product_text)
            if tether_anchor is not None:
                # The page establishes a provided tether anchor, but not its physical
                # interface form. Retain the role and let resolution keep type unknown.
                claims.append(
                    anchor_claim(
                        "interface.role",
                        "anchor_attachment_tether_side",
                        raw_value=tether_anchor.group(0),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                        subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                        subject_ref="wrist_anchor_tether_connection",
                    )
                )

        return _dedupe(claims)

    def observe(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[AcquisitionObservation]:
        if identity.product_type != ProductType.KIT:
            return []

        observations: list[AcquisitionObservation] = []
        for artifact in artifacts:
            if not _is_verified_product_detail(artifact, identity):
                continue
            wrapper_text = _product_local_text(artifact.body, identity)
            slip_on_rows = [
                (sku, description, quantity)
                for sku, description, quantity in _kit_content_rows(artifact.body, identity)
                if re.search(r"\bslip[-\s]?on\s+wrist\s+anchor\b", description, re.I)
            ]
            if (
                slip_on_rows
                and re.search(r"\badjustable\s+wrist\s+anchor\b", wrapper_text, re.I)
                and re.search(r"\b(?:velcro|hook\s+and\s+loop)\b", wrapper_text, re.I)
            ):
                identifiers = ", ".join(sorted({sku for sku, _, _ in slip_on_rows}))
                observations.append(
                    AcquisitionObservation(
                        code="KIT_COMPONENT_IDENTITY_CONFLICT",
                        value=identifiers,
                        detail=(
                            "The exact GRIPPS kit page describes an adjustable hook-and-loop "
                            "wrist anchor but its Kit Contents names "
                            f"{identifiers} Slip-On Wrist Anchor. Preserve the stated relationship "
                            "evidence but do not make the kit composition recommendation-ready "
                            "until GRIPPS resolves the component identity."
                        ),
                        source_url=artifact.url,
                        extractor=_EXTRACTOR,
                    )
                )
        return observations

    def readiness_issues_for(
        self,
        identity: ProductIdentity,
        claims: list[CandidateClaim],
        observations: list[AcquisitionObservation],
    ) -> list[ReadinessIssue] | None:
        issues = list(self.readiness_issues(claims, observations) or [])
        for observation in observations:
            if observation.code != "KIT_COMPONENT_IDENTITY_CONFLICT":
                continue
            issues.append(
                ReadinessIssue(
                    code="KIT_COMPONENT_IDENTITY_CONFLICT",
                    property_key="declared_relationship",
                    detail=observation.detail,
                )
            )
        return issues or None

    def readiness_issues(self, claims, observations) -> list[ReadinessIssue] | None:
        capacity_claims = [
            claim
            for claim in claims
            if claim.subject_type == ClaimSubjectType.PRODUCT
            and claim.subject_ref == "self"
            and claim.property_key == "rated_capacity_kg"
        ]
        if mass_claims_semantically_agree(capacity_claims):
            return None

        capacity_values = sorted({float(claim.value) for claim in capacity_claims})
        rendered = ", ".join(f"{value:g} kg" for value in capacity_values)
        return [ReadinessIssue(
            code="EVIDENCE_CONFLICT",
            property_key="rated_capacity_kg",
            detail=(
                "Conflicting first-party rated-capacity claims remain unreconciled "
                f"({rendered}); no value is recommendation-ready."
            ),
        )]


def _is_verified_product_detail(
    artifact: SourceArtifact,
    identity: ProductIdentity,
) -> bool:
    if artifact.source_type != SourceType.MANUFACTURER_WEBPAGE:
        return False
    if _normalized_product_url(artifact.url) != _normalized_product_url(identity.url):
        return False

    text = page_text(artifact.body)
    if identity.sku and re.search(
        rf"(?<![A-Z0-9]){re.escape(identity.sku)}(?![A-Z0-9])",
        text,
        re.I,
    ) is not None:
        return True

    heading = re.search(r"<h1\b[^>]*>(?P<body>.*?)</h1>", artifact.body, re.I | re.S)
    if heading is None or not identity.name:
        return False
    heading_text = page_text(heading.group(0)).casefold()
    name_tokens = [token for token in re.findall(r"[a-z0-9]+", identity.name.casefold()) if len(token) > 2]
    return bool(name_tokens) and all(token in heading_text for token in name_tokens)


def _product_local_elements(body: str, identity: ProductIdentity) -> list:
    """Return the exact product's main page region before cross-sell content.

    Exact product URLs still contain sibling product cards. The matching product H1 is
    therefore the start boundary. A later H1 always ends the region; explicit cross-sell
    headings also end it. All PR #72 GRIPPS semantics consume this same bounded region.
    """

    if not identity.name:
        return []

    soup = BeautifulSoup(body, "html.parser")
    name_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", identity.name.casefold())
        if len(token) > 2
    ]
    if not name_tokens:
        return []

    heading = next(
        (
            candidate
            for candidate in soup.find_all("h1")
            if all(
                token in " ".join(candidate.stripped_strings).casefold()
                for token in name_tokens
            )
        ),
        None,
    )
    if heading is None:
        return []

    elements: list = []
    for element in heading.next_elements:
        name = getattr(element, "name", None)
        if name == "h1" and element is not heading:
            break
        if name in {"h2", "h3", "h4", "h5", "h6"}:
            heading_text = " ".join(element.stripped_strings).casefold()
            if any(
                boundary in heading_text
                for boundary in (
                    "related products",
                    "recently viewed products",
                    "popular products",
                    "you may also like",
                )
            ):
                break
        elements.append(element)

    return elements


def _product_local_text(body: str, identity: ProductIdentity) -> str:
    pieces: list[str] = []
    for element in _product_local_elements(body, identity):
        if isinstance(element, str):
            normalized = " ".join(element.split())
            if normalized:
                pieces.append(normalized)
    return " ".join(pieces)


def _extract_declared_relationship_claims(
    identity: ProductIdentity,
    artifacts: list[SourceArtifact],
) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for artifact in artifacts:
        if not _is_verified_product_detail(artifact, identity):
            continue

        if identity.product_type == ProductType.KIT:
            for sku, description, quantity in _kit_content_rows(artifact.body, identity):
                relationship_ref = f"kit:{identity.sku or identity.model or 'product'}:{sku}"
                raw = " ".join(
                    part
                    for part in (
                        sku,
                        description,
                        str(quantity) if quantity is not None else None,
                    )
                    if part
                )
                claims.extend(
                    _relationship_claims(
                        relationship_ref,
                        relationship_type="kit_relationship",
                        object_identifier=sku,
                        quantity=quantity,
                        scope="Manufacturer-published Kit Contents row",
                        raw_value=raw,
                        source_url=artifact.url,
                        evidence_method="manufacturer_kit_composition",
                    )
                )

        product_text = _product_local_text(artifact.body, identity)
        if _base_sku(identity.sku) == "H01085":
            endorsement = _h01085_h01067_endorsement(product_text)
            if endorsement is not None:
                claims.extend(
                    _relationship_claims(
                        f"endorsed:{identity.sku or 'H01085'}:H01067",
                        relationship_type="explicitly_endorsed",
                        object_identifier="H01067",
                        quantity=None,
                        scope="GRIPPS states H01067 is suitable for this wrist anchor",
                        raw_value=endorsement.group(0),
                        source_url=artifact.url,
                        evidence_method="manufacturer_pairing",
                    )
                )

    return _dedupe(claims)



def _extract_connection_compatibility_claims(
    identity: ProductIdentity,
    artifacts: list[SourceArtifact],
) -> list[CandidateClaim]:
    """Keep H01067/H01085 connection authority exact when geometry remains sparse.

    The H01085 page explicitly names H01067 wrist tethers as suitable, while the
    normalized H01085 tether-side interface remains physically unknown. Preserve that
    statement as a product-scoped manufacturer declaration rather than widening it into
    generic carabiner-to-wrist-anchor compatibility.
    """

    if (
        identity.product_type != ProductType.ANCHOR_ATTACHMENT
        or _base_sku(identity.sku) != "H01085"
        or not identity.sku
        or identity.sku.upper() == "H01085"
    ):
        return []

    claims: list[CandidateClaim] = []
    for artifact in artifacts:
        if not _is_verified_product_detail(artifact, identity):
            continue
        product_text = _product_local_text(artifact.body, identity)
        variant_evidence = _exact_sku_evidence(product_text, identity.sku)
        if variant_evidence is None:
            continue
        endorsement = _h01085_h01067_endorsement(product_text)
        if endorsement is None:
            continue
        claims.extend(
            _connection_compatibility_claims(
                declaration_ref=f"h01067_to_{identity.sku.lower()}_wrist_anchor",
                source_product_identifier="H01067",
                target_product_identifier=identity.sku.upper(),
                relationship_raw_value=endorsement.group(0),
                target_product_raw_value=variant_evidence,
                source_url=artifact.url,
            )
        )
    return _dedupe(claims)


def _exact_sku_evidence(text: str, sku: str) -> str | None:
    """Return unambiguous identity-bearing SKU evidence for one exact variant."""

    identity_matches = list(
        re.finditer(
            r"\bSKU\s*[:#-]?\s*(?P<sku>H\d{5}(?:-[A-Z0-9]+)?)\b",
            text,
            re.I,
        )
    )
    identity_skus = {match.group("sku").upper() for match in identity_matches}
    if identity_skus != {sku.upper()}:
        return None

    match = next(
        (
            match
            for match in identity_matches
            if match.group("sku").upper() == sku.upper()
        ),
        None,
    )
    return match.group(0) if match is not None else None

def _h01085_h01067_endorsement(text: str) -> re.Match[str] | None:
    """Return the local affirmative H01067 suitability statement, if uncontradicted."""

    match = _affirmative_search(_H01085_H01067_ENDORSEMENT, text)
    if match is None:
        return None
    if _H01085_H01067_IN_MATCH_EXCLUSION.search(match.group(0)) is not None:
        return None

    # A contradiction may follow in the same sentence or in an immediately adjacent
    # rhetorical sentence ("However, do not ..."). Keep the scan bounded so an
    # unrelated later prohibition elsewhere on the product page does not erase the
    # positive statement, but fail closed on nearby contrary first-party wording.
    suffix = text[match.end() : match.end() + 180]
    if (
        _H01085_POST_ENDORSEMENT_PROHIBITION.search(suffix) is not None
        or _H01085_ADJACENT_PROHIBITION.search(suffix) is not None
    ):
        return None
    return match


def _connection_compatibility_claims(
    *,
    declaration_ref: str,
    source_product_identifier: str,
    target_product_identifier: str,
    relationship_raw_value: str,
    target_product_raw_value: str,
    source_url: str,
) -> list[CandidateClaim]:
    values = (
        ("connection_compatibility.source_product_identifier", source_product_identifier),
        ("connection_compatibility.target_product_identifier", target_product_identifier),
        ("connection_compatibility.issuer_manufacturer", "GRIPPS"),
        (
            "connection_compatibility.scope",
            "GRIPPS states H01067 wrist tethers are suitable for this exact "
            "Slip-On Wrist Anchor variant; tether-side interface geometry remains unpublished",
        ),
    )
    claims: list[CandidateClaim] = []
    for property_key, value in values:
        is_target_identity = (
            property_key == "connection_compatibility.target_product_identifier"
        )
        claims.append(
            CandidateClaim(
                subject_type=ClaimSubjectType.CONNECTION_COMPATIBILITY,
                subject_ref=declaration_ref,
                property_key=property_key,
                value=value,
                unit=None,
                raw_value=(
                    target_product_raw_value
                    if is_target_identity
                    else relationship_raw_value
                ),
                source_url=source_url,
                evidence_method=(
                    "manufacturer_product_identity"
                    if is_target_identity
                    else "manufacturer_pairing"
                ),
                extractor=_EXTRACTOR,
                claim_type=ClaimType.DIRECT,
            )
        )
    return claims


def _kit_content_rows(
    body: str,
    identity: ProductIdentity,
) -> list[tuple[str, str, int | None]]:
    """Return rows only from a Kit Contents table inside the requested product region."""

    elements = _product_local_elements(body, identity)
    rows: list[tuple[str, str, int | None]] = []

    marker_index: int | None = None
    for index, element in enumerate(elements):
        if (
            isinstance(element, str)
            and "kit contents" in " ".join(element.casefold().split())
        ):
            marker_index = index
            break
    if marker_index is None:
        return rows

    table = None
    for element in elements[marker_index + 1 :]:
        name = getattr(element, "name", None)
        if name == "table":
            table = element
            break
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading_text = " ".join(element.stripped_strings).casefold()
            if any(
                boundary in heading_text
                for boundary in (
                    "key features",
                    "specifications",
                    "downloads",
                    "related products",
                    "recently viewed products",
                )
            ):
                break
    if table is None:
        return rows

    for row in table.find_all("tr"):
        cells = [" ".join(cell.stripped_strings) for cell in row.find_all(["th", "td"])]
        if len(cells) < 2:
            continue
        sku_match = re.search(r"\bH\d{5}(?:-[A-Z0-9]+)?\b", cells[0], re.I)
        if sku_match is None:
            continue
        quantity: int | None = None
        description_cells = cells[1:]
        if len(cells) >= 3:
            quantity_text = cells[-1].strip()
            description_cells = cells[1:-1]
            if quantity_text:
                quantity_match = re.fullmatch(r"\d+", quantity_text)
                if quantity_match is None:
                    continue
                quantity = int(quantity_match.group(0))
        description = " ".join(description_cells).strip()
        if not description:
            continue
        rows.append(
            (
                sku_match.group(0).upper(),
                description,
                quantity,
            )
        )
    return rows


def _relationship_claims(
    relationship_ref: str,
    *,
    relationship_type: str,
    object_identifier: str,
    quantity: int | None,
    scope: str,
    raw_value: str,
    source_url: str,
    evidence_method: str,
) -> list[CandidateClaim]:
    values = [
        ("declared_relationship.type", relationship_type),
        ("declared_relationship.object_product_identifier", object_identifier),
        ("declared_relationship.scope", scope),
    ]
    if quantity is not None:
        values.append(("declared_relationship.quantity", quantity))
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.DECLARED_RELATIONSHIP,
            subject_ref=relationship_ref,
            property_key=property_key,
            value=value,
            unit=None,
            raw_value=raw_value,
            source_url=source_url,
            evidence_method=evidence_method,
            extractor=_EXTRACTOR,
            claim_type=ClaimType.DIRECT,
        )
        for property_key, value in values
    ]


def _affirmative_search(
    pattern: re.Pattern[str],
    text: str,
) -> re.Match[str] | None:
    """Return the first locally affirmative match, skipping explicit negation.

    Manufacturer copy is flattened before extraction, so a positive-looking phrase can
    occur inside a prohibition such as "do not just slip it on" or "not suitable for".
    Treat nearby same-clause negation as contrary evidence and fail closed rather than
    promoting the phrase into an executable claim.
    """

    for match in pattern.finditer(text):
        prefix_start = max(
            text.rfind(".", 0, match.start()),
            text.rfind(";", 0, match.start()),
            text.rfind("!", 0, match.start()),
            text.rfind("?", 0, match.start()),
            text.rfind("\n", 0, match.start()),
        )
        prefix = text[prefix_start + 1 : match.start()][-80:]
        if re.search(r"\b(?:not|no|never)\b", prefix, re.I):
            if re.search(r"\bnot\s+only\b", prefix, re.I):
                continue
            continue
        return match
    return None


def _h01067_tether_claims(text: str, source_url: str) -> list[CandidateClaim]:
    pair = _affirmative_search(_H01067_CARABINER_PAIR, text)
    pair_use = _affirmative_search(_H01067_TOOL_TO_WRIST_USE, text)
    if pair is None:
        return []

    connector_ref = "wrist_tether_carabiner"
    claims = [
        _claim(
            "tether.connection_count",
            2,
            None,
            pair.group(0),
            source_url,
        ),
        _claim(
            "connector.opening_action_count",
            1,
            None,
            pair.group(0),
            source_url,
            ClaimSubjectType.CONNECTOR_SPEC,
            connector_ref,
        ),
        _claim(
            "connector.swivel",
            True,
            None,
            pair.group(0),
            source_url,
            ClaimSubjectType.CONNECTOR_SPEC,
            connector_ref,
        ),
    ]
    for endpoint_ref in ("connection_point_1", "connection_point_2"):
        claims.extend(
            [
                _claim(
                    "connection_point.interface_type",
                    "carabiner",
                    None,
                    pair.group(0),
                    source_url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    endpoint_ref,
                ),
                _claim(
                    "connection_point.connector_spec_ref",
                    connector_ref,
                    None,
                    pair.group(0),
                    source_url,
                    ClaimSubjectType.TETHER_CONNECTION_POINT,
                    endpoint_ref,
                ),
            ]
        )

    if pair_use is None or _H01067_DIRECTIONAL_SPLIT.search(text) is not None:
        return claims

    evidence_raw = f"{pair.group(0)}; {pair_use.group(0)}"
    declaration_ref = "endpoint_assignment:h01067_carabiner_equivalent_pair"
    values = [
        ("endpoint_assignment.member_ref", "connection_point_1"),
        ("endpoint_assignment.member_ref", "connection_point_2"),
        ("endpoint_assignment.semantics", "reversible_tool_anchor_pair"),
        ("endpoint_assignment.basis", "derived_endpoint_equivalence"),
        ("endpoint_assignment.issuer_manufacturer", "GRIPPS"),
        (
            "endpoint_assignment.scope",
            "Derived from first-party evidence of one same-construction single-action "
            "carabiner pair and undifferentiated hand-tool to glove/wrist-anchor use",
        ),
    ]
    claims.extend(
        CandidateClaim(
            subject_type=ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT,
            subject_ref=declaration_ref,
            property_key=property_key,
            value=value,
            raw_value=evidence_raw,
            source_url=source_url,
            evidence_method="derived_endpoint_equivalence",
            extractor=_EXTRACTOR,
            claim_type=ClaimType.DERIVED,
        )
        for property_key, value in values
    )
    return claims


def _base_sku(sku: str | None) -> str | None:
    if not sku:
        return None
    return sku.strip().upper().split("-", 1)[0]


def _normalized_product_url(url: str) -> tuple[str, str] | None:
    parts = urlsplit(url)
    if parts.scheme.casefold() not in {"http", "https"} or not parts.hostname:
        return None
    host = parts.hostname.casefold()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/").casefold() or "/"
    return host, path


def _capacity_claims(text: str, source_url: str) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for match in _LOAD_RATING.finditer(text):
        claims.append(_claim(
            "rated_capacity_kg",
            mass_to_kg(float(match.group("value")), match.group("unit")),
            "kg",
            match.group(0),
            source_url,
        ))
    return claims


def _directional_endpoint_claims(raw: str, source_url: str) -> list[CandidateClaim]:
    claims: list[CandidateClaim] = []
    for endpoint_ref, role, connector_ref, relative_size in (
        ("anchor_side", "anchor_side", "anchor_carabiner", "large"),
        ("tool_side", "tool_side", "tool_carabiner", "small"),
    ):
        claims.extend([
            _claim(
                "connection_point.interface_type",
                "carabiner",
                None,
                raw,
                source_url,
                ClaimSubjectType.TETHER_CONNECTION_POINT,
                endpoint_ref,
            ),
            _claim(
                "connection_point.role",
                role,
                None,
                raw,
                source_url,
                ClaimSubjectType.TETHER_CONNECTION_POINT,
                endpoint_ref,
            ),
            _claim(
                "connection_point.connector_spec_ref",
                connector_ref,
                None,
                raw,
                source_url,
                ClaimSubjectType.TETHER_CONNECTION_POINT,
                endpoint_ref,
            ),
            _claim(
                "connector.attribute.relative_size",
                relative_size,
                None,
                raw,
                source_url,
                ClaimSubjectType.CONNECTOR_SPEC,
                connector_ref,
            ),
        ])
    return claims


def _claim(
    property_key: str,
    value,
    unit: str | None,
    raw_value: str | None,
    source_url: str,
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT,
    subject_ref: str = "self",
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        unit=unit,
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=_EXTRACTOR,
        claim_type=ClaimType.DIRECT,
    )


def _dedupe(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    seen: set[tuple[str, str, str, str, str | None, str]] = set()
    out: list[CandidateClaim] = []
    for claim in claims:
        key = (
            claim.subject_type.value,
            claim.subject_ref,
            claim.property_key,
            str(claim.value),
            claim.unit,
            claim.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
