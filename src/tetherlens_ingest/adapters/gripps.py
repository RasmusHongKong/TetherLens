from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
)
from tetherlens_ingest.normalize import mass_to_kg
from tetherlens_ingest.reconciliation import mass_claims_semantically_agree

from .base import ManufacturerAdapter
from .common import page_text


_EXTRACTOR = "gripps.v0.2"

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


class GRIPPSAdapter(ManufacturerAdapter):
    """Extract GRIPPS evidence into existing manufacturer-neutral primitives.

    Tether direction is emitted only when the manufacturer explicitly distinguishes the
    anchor and tool ends. ToolAttachment installation remains equally evidence-bound:
    SnapLock's published ``handle or neck`` wording compiles only the independently
    established handle subset. ``neck`` is not widened to an external-section path and
    S/M/L/XL labels never become inferred dimensions.
    """

    manufacturer = "GRIPPS"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        if identity.product_type == ProductType.TETHER:
            return self._extract_tether(artifacts)
        if identity.product_type == ProductType.TOOL_ATTACHMENT:
            return self._extract_tool_attachment(artifacts)
        return []

    def _extract_tether(self, artifacts: list[SourceArtifact]) -> list[CandidateClaim]:
        claims: list[CandidateClaim] = []
        for artifact in artifacts:
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
