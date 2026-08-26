from __future__ import annotations

from collections import defaultdict

from .compatibility import (
    AttachmentEligibility,
    CaptiveState,
    EligibilityPath,
    FeatureKind,
    FeaturePredicate,
    FeatureRole,
    ToolInterfaceFeature,
)
from .connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from .models import CandidateClaim, ClaimSubjectType
from .normalize import length_to_mm


FEATURE_KIND_KEY = "feature.kind"
FEATURE_ROLE_KEY = "feature.role"
FEATURE_CAPTIVE_STATE_KEY = "feature.captive_state"
FEATURE_LOCATION_KEY = "feature.location_description"
FEATURE_DIMENSION_PREFIX = "feature.dimension."
FEATURE_ATTRIBUTE_PREFIX = "feature.attribute."
ATTACHMENT_SELECTION_CLASS_KEY = "attachment_selection_class"

INTERFACE_TYPE_KEY = "interface.type"
INTERFACE_ROLE_KEY = "interface.role"
INTERFACE_CONNECTOR_SPEC_REF_KEY = "interface.connector_spec_ref"
INTERFACE_DIMENSION_PREFIX = "interface.dimension."
INTERFACE_ATTRIBUTE_PREFIX = "interface.attribute."
TETHER_INTERFACE_TYPE_KEY = "connection_point.interface_type"
TETHER_SIDE_KEY = "connection_point.role"
TETHER_CONNECTOR_SPEC_REF_KEY = "connection_point.connector_spec_ref"

CONNECTOR_OPENING_ACTION_COUNT_KEY = "connector.opening_action_count"
CONNECTOR_LOCKING_MODE_KEY = "connector.locking_mode"
CONNECTOR_SWIVEL_KEY = "connector.swivel"
CONNECTOR_DIMENSION_PREFIX = "connector.dimension."
CONNECTOR_ATTRIBUTE_PREFIX = "connector.attribute."


class ClaimResolutionError(ValueError):
    """Accepted claims are internally inconsistent or unsupported for resolution."""


def resolve_tool_interface_features(claims: list[CandidateClaim]) -> list[ToolInterfaceFeature]:
    """Resolve accepted feature-scoped claims into runtime tool features.

    This function deliberately does not decide which candidate claims are accepted.
    Callers must pass only reconciled/accepted claims. Feature identity is carried by
    ``subject_ref`` so facts from separate physical features cannot be combined.
    """

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.PHYSICAL_INTERFACE:
            continue
        if not _is_feature_claim(claim.property_key):
            continue
        grouped[claim.subject_ref].append(claim)

    features: list[ToolInterfaceFeature] = []
    for feature_id, feature_claims in grouped.items():
        kind_claim = _single_claim(feature_claims, FEATURE_KIND_KEY)
        if kind_claim is None:
            # A physical-interface subject is not a ToolInterfaceFeature until its
            # normalized geometry has been established.
            continue

        role_claim = _single_claim(feature_claims, FEATURE_ROLE_KEY)
        captive_claim = _single_claim(feature_claims, FEATURE_CAPTIVE_STATE_KEY)
        location_claim = _single_claim(feature_claims, FEATURE_LOCATION_KEY)

        dimensions_mm: dict[str, float] = {}
        attributes: dict[str, str | int | float | bool] = {}
        for claim in feature_claims:
            if claim.property_key.startswith(FEATURE_DIMENSION_PREFIX):
                code = claim.property_key.removeprefix(FEATURE_DIMENSION_PREFIX)
                if not code:
                    continue
                _set_unique_dimension(
                    dimensions_mm,
                    code,
                    _dimension_to_mm(claim),
                    feature_id,
                )
            elif claim.property_key.startswith(FEATURE_ATTRIBUTE_PREFIX):
                code = claim.property_key.removeprefix(FEATURE_ATTRIBUTE_PREFIX)
                if not code:
                    continue
                _set_unique(attributes, code, claim.value, feature_id)

        try:
            feature_kind = FeatureKind(str(kind_claim.value))
            feature_role = (
                FeatureRole(str(role_claim.value))
                if role_claim is not None
                else FeatureRole.UNKNOWN
            )
            captive_state = (
                CaptiveState(str(captive_claim.value))
                if captive_claim is not None
                else CaptiveState.UNKNOWN
            )
        except ValueError as exc:
            raise ClaimResolutionError(
                f"unsupported normalized feature value on {feature_id!r}: {exc}"
            ) from exc

        features.append(
            ToolInterfaceFeature(
                feature_id=feature_id,
                feature_kind=feature_kind,
                feature_role=feature_role,
                captive_state=captive_state,
                location_description=(
                    str(location_claim.value) if location_claim is not None else None
                ),
                dimensions_mm=dimensions_mm,
                attributes=attributes,
            )
        )

    return features


def resolve_attachment_eligibility(claims: list[CandidateClaim]) -> AttachmentEligibility | None:
    """Compile accepted attachment semantics into reusable feature eligibility.

    The first supported selection class is intentionally geometry-led and reusable:
    a captive-feature attachment can install on one captive handle OR one captive
    through-opening. No tool or attachment SKU participates in this compilation.
    """

    selection = _single_claim(claims, ATTACHMENT_SELECTION_CLASS_KEY)
    if selection is None:
        return None

    if selection.value == "captive_feature_attachment":
        return AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle"),
                        FeaturePredicate(property_key="captive_state", value="captive"),
                    ],
                ),
                EligibilityPath(
                    binding_name="opening",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="through_opening"),
                        FeaturePredicate(property_key="captive_state", value="captive"),
                    ],
                ),
            ]
        )

    raise ClaimResolutionError(
        f"unsupported attachment selection class: {selection.value!r}"
    )


def resolve_connection_interfaces(claims: list[CandidateClaim]) -> list[ConnectionInterface]:
    """Resolve accepted connection-interface claims without merging distinct subjects.

    ToolAttachment-provided interfaces use ``physical_interface`` subjects with
    explicit ``interface.role`` and ``interface.type`` claims. Tether endpoints use
    the already-established ``tether_connection_point`` subjects. Both normalize to
    the same runtime shape while retaining their different structural roles.
    """

    interfaces: list[ConnectionInterface] = []
    physical_groups: dict[str, list[CandidateClaim]] = defaultdict(list)
    tether_groups: dict[str, list[CandidateClaim]] = defaultdict(list)

    for claim in claims:
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE and _is_connection_interface_claim(
            claim.property_key
        ):
            physical_groups[claim.subject_ref].append(claim)
        elif claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT and claim.property_key in {
            TETHER_INTERFACE_TYPE_KEY,
            TETHER_SIDE_KEY,
            TETHER_CONNECTOR_SPEC_REF_KEY,
        }:
            tether_groups[claim.subject_ref].append(claim)

    for interface_id, interface_claims in physical_groups.items():
        type_claim = _single_claim(interface_claims, INTERFACE_TYPE_KEY)
        role_claim = _single_claim(interface_claims, INTERFACE_ROLE_KEY)
        if type_claim is None or role_claim is None:
            continue

        connector_claim = _single_claim(interface_claims, INTERFACE_CONNECTOR_SPEC_REF_KEY)
        dimensions_mm: dict[str, float] = {}
        attributes: dict[str, str | int | float | bool] = {}
        for claim in interface_claims:
            if claim.property_key.startswith(INTERFACE_DIMENSION_PREFIX):
                code = claim.property_key.removeprefix(INTERFACE_DIMENSION_PREFIX)
                if code:
                    _set_unique_dimension(
                        dimensions_mm,
                        code,
                        _dimension_to_mm(claim),
                        interface_id,
                    )
            elif claim.property_key.startswith(INTERFACE_ATTRIBUTE_PREFIX):
                code = claim.property_key.removeprefix(INTERFACE_ATTRIBUTE_PREFIX)
                if code:
                    _set_unique(attributes, code, claim.value, interface_id)

        try:
            role = ConnectionInterfaceRole(str(role_claim.value))
        except ValueError as exc:
            raise ClaimResolutionError(
                f"unsupported connection interface role on {interface_id!r}: {role_claim.value!r}"
            ) from exc

        interfaces.append(
            ConnectionInterface(
                interface_id=interface_id,
                role=role,
                interface_type=str(type_claim.value),
                connector_spec_ref=(
                    str(connector_claim.value) if connector_claim is not None else None
                ),
                dimensions_mm=dimensions_mm,
                attributes=attributes,
            )
        )

    for interface_id, interface_claims in tether_groups.items():
        type_claim = _single_claim(interface_claims, TETHER_INTERFACE_TYPE_KEY)
        if type_claim is None:
            continue
        side_claim = _single_claim(interface_claims, TETHER_SIDE_KEY)
        connector_claim = _single_claim(interface_claims, TETHER_CONNECTOR_SPEC_REF_KEY)

        try:
            tether_side = (
                TetherSide(str(side_claim.value)) if side_claim is not None else TetherSide.UNKNOWN
            )
        except ValueError as exc:
            raise ClaimResolutionError(
                f"unsupported tether-side value on {interface_id!r}: {side_claim.value!r}"
            ) from exc

        interfaces.append(
            ConnectionInterface(
                interface_id=interface_id,
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type=str(type_claim.value),
                tether_side=tether_side,
                connector_spec_ref=(
                    str(connector_claim.value) if connector_claim is not None else None
                ),
            )
        )

    return interfaces


def resolve_connector_specs(claims: list[CandidateClaim]) -> dict[str, ConnectorSpec]:
    """Resolve accepted connector-spec claims into reusable runtime connector facts."""

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.CONNECTOR_SPEC:
            continue
        if not _is_connector_spec_claim(claim.property_key):
            continue
        grouped[claim.subject_ref].append(claim)

    specs: dict[str, ConnectorSpec] = {}
    for connector_spec_id, spec_claims in grouped.items():
        action_claim = _single_claim(spec_claims, CONNECTOR_OPENING_ACTION_COUNT_KEY)
        locking_claim = _single_claim(spec_claims, CONNECTOR_LOCKING_MODE_KEY)
        swivel_claim = _single_claim(spec_claims, CONNECTOR_SWIVEL_KEY)
        dimensions_mm: dict[str, float] = {}
        attributes: dict[str, str | int | float | bool] = {}

        for claim in spec_claims:
            if claim.property_key.startswith(CONNECTOR_DIMENSION_PREFIX):
                code = claim.property_key.removeprefix(CONNECTOR_DIMENSION_PREFIX)
                if code:
                    _set_unique_dimension(
                        dimensions_mm,
                        code,
                        _dimension_to_mm(claim),
                        connector_spec_id,
                    )
            elif claim.property_key.startswith(CONNECTOR_ATTRIBUTE_PREFIX):
                code = claim.property_key.removeprefix(CONNECTOR_ATTRIBUTE_PREFIX)
                if code:
                    _set_unique(attributes, code, claim.value, connector_spec_id)

        opening_action_count: int | None = None
        if action_claim is not None:
            if isinstance(action_claim.value, bool) or not isinstance(action_claim.value, int):
                raise ClaimResolutionError(
                    f"connector opening action count on {connector_spec_id!r} must be an integer"
                )
            opening_action_count = action_claim.value

        swivel: bool | None = None
        if swivel_claim is not None:
            if not isinstance(swivel_claim.value, bool):
                raise ClaimResolutionError(
                    f"connector swivel value on {connector_spec_id!r} must be boolean"
                )
            swivel = swivel_claim.value

        specs[connector_spec_id] = ConnectorSpec(
            connector_spec_id=connector_spec_id,
            opening_action_count=opening_action_count,
            locking_mode=str(locking_claim.value) if locking_claim is not None else None,
            swivel=swivel,
            dimensions_mm=dimensions_mm,
            attributes=attributes,
        )

    return specs


def _is_feature_claim(property_key: str) -> bool:
    return property_key in {
        FEATURE_KIND_KEY,
        FEATURE_ROLE_KEY,
        FEATURE_CAPTIVE_STATE_KEY,
        FEATURE_LOCATION_KEY,
    } or property_key.startswith((FEATURE_DIMENSION_PREFIX, FEATURE_ATTRIBUTE_PREFIX))


def _is_connection_interface_claim(property_key: str) -> bool:
    return property_key in {
        INTERFACE_TYPE_KEY,
        INTERFACE_ROLE_KEY,
        INTERFACE_CONNECTOR_SPEC_REF_KEY,
    } or property_key.startswith((INTERFACE_DIMENSION_PREFIX, INTERFACE_ATTRIBUTE_PREFIX))


def _is_connector_spec_claim(property_key: str) -> bool:
    return property_key in {
        CONNECTOR_OPENING_ACTION_COUNT_KEY,
        CONNECTOR_LOCKING_MODE_KEY,
        CONNECTOR_SWIVEL_KEY,
    } or property_key.startswith((CONNECTOR_DIMENSION_PREFIX, CONNECTOR_ATTRIBUTE_PREFIX))


def _single_claim(
    claims: list[CandidateClaim],
    property_key: str,
) -> CandidateClaim | None:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        return None

    normalized_values = {(str(claim.value), claim.unit or "") for claim in matches}
    if len(normalized_values) > 1:
        subjects = sorted({claim.subject_ref for claim in matches})
        raise ClaimResolutionError(
            f"conflicting accepted claims for {property_key!r} on {subjects}: "
            f"{sorted(normalized_values)!r}"
        )
    return matches[0]


def _dimension_to_mm(claim: CandidateClaim) -> float:
    if isinstance(claim.value, bool) or not isinstance(claim.value, (int, float)):
        raise ClaimResolutionError(
            f"feature dimension {claim.property_key!r} must be numeric"
        )
    if claim.unit is None:
        raise ClaimResolutionError(
            f"feature dimension {claim.property_key!r} requires a unit"
        )
    try:
        return float(length_to_mm(float(claim.value), claim.unit))
    except ValueError as exc:
        raise ClaimResolutionError(str(exc)) from exc


def _set_unique(
    target: dict[str, str | int | float | bool],
    key: str,
    value: str | int | float | bool,
    feature_id: str,
) -> None:
    if key in target and target[key] != value:
        raise ClaimResolutionError(
            f"conflicting accepted feature attribute {key!r} on {feature_id!r}"
        )
    target[key] = value


def _set_unique_dimension(
    target: dict[str, float],
    key: str,
    value: float,
    feature_id: str,
) -> None:
    if key in target and target[key] != value:
        raise ClaimResolutionError(
            f"conflicting accepted feature dimension {key!r} on {feature_id!r}"
        )
    target[key] = value
