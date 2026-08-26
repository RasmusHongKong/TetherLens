from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .compatibility import ManufacturerAssessment, ManufacturerPosition


class ConnectionInterfaceRole(StrEnum):
    TOOL_ATTACHMENT_TETHER_SIDE = "tool_attachment_tether_side"
    TOOL_DIRECT_TETHER_INTERFACE = "tool_direct_tether_interface"
    TETHER_CONNECTION = "tether_connection"
    ANCHOR_ATTACHMENT_TETHER_SIDE = "anchor_attachment_tether_side"
    CONTAINER_CONNECTION = "container_connection"
    UNKNOWN = "unknown"


class TetherSide(StrEnum):
    TOOL_SIDE = "tool_side"
    ANCHOR_SIDE = "anchor_side"
    EITHER = "either"
    UNKNOWN = "unknown"


class ConnectionStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    REQUIRES_VERIFICATION = "requires_verification"
    UNRESOLVED = "unresolved"


class CompatibilityBasis(StrEnum):
    MANUFACTURER_DECLARED = "manufacturer_declared"
    VALIDATED_GEOMETRY = "validated_geometry"
    VALIDATED_INTERFACE_CLASS = "validated_interface_class"
    RUNTIME_VERIFICATION = "runtime_verification"
    NONE = "none"


class RuntimeVerificationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ContradictionType(StrEnum):
    DERIVED_RULE_DISAGREEMENT = "derived_rule_disagreement"
    HARD_PHYSICAL_CONTRADICTION = "hard_physical_contradiction"
    AUTHORITATIVE_SOURCE_CONFLICT = "authoritative_source_conflict"


class ConnectionInterface(BaseModel):
    """One physical interface participating in a tether connection.

    This is intentionally separate from ``ToolInterfaceFeature``. A ToolAttachment
    can consume one tool feature while providing a different tether-side interface.
    """

    interface_id: str
    role: ConnectionInterfaceRole
    interface_type: str
    tether_side: TetherSide = TetherSide.UNKNOWN
    connector_spec_ref: str | None = None
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("interface_type must be non-empty")
        return normalized

    @field_validator("dimensions_mm", mode="before")
    @classmethod
    def validate_dimensions_mm(cls, dimensions: Any) -> Any:
        return _validate_dimensions(dimensions)


class ConnectorSpec(BaseModel):
    """Accepted reusable facts about one discrete connector specification.

    The initial runtime slice intentionally carries only facts already extracted by
    current adapters plus narrowly-scoped geometry when it is available. It is not a
    general connector CAD model.
    """

    connector_spec_id: str
    opening_action_count: int | None = Field(default=None, ge=1)
    locking_mode: str | None = None
    swivel: bool | None = None
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("dimensions_mm", mode="before")
    @classmethod
    def validate_dimensions_mm(cls, dimensions: Any) -> Any:
        return _validate_dimensions(dimensions)


class ConnectionManufacturerAssessment(ManufacturerAssessment):
    """Manufacturer assessment plus source/causal metadata needed by connection logic.

    The manufacturer position remains an independent axis. ``technical_causal_scope``
    only records whether an explicit prohibition also establishes a genuine technical
    failure mode for this exact connection scope.
    """

    authoritative: bool = True
    technical_causal_scope_established: bool = False


class ConnectionRuleResult(BaseModel):
    """One reusable technical-rule result retained for precedence/review semantics.

    ``status=None`` means the rule was applicable but inconclusive. Such a result must
    fall through to later compatibility bases rather than terminating evaluation.
    """

    rule_id: str
    basis: CompatibilityBasis
    status: ConnectionStatus | None = None
    reason: str
    hard_physical: bool = False


class ConnectionEvaluation(BaseModel):
    status: ConnectionStatus
    basis: CompatibilityBasis
    endpoint_id: str
    target_interface_id: str
    reason: str
    manufacturer_assessments: list[ConnectionManufacturerAssessment] = Field(default_factory=list)
    rule_results: list[ConnectionRuleResult] = Field(default_factory=list)
    verification_status: RuntimeVerificationStatus | None = None
    verification_family: str | None = None
    contradiction_type: ContradictionType | None = None
    review_required: bool = False

    @property
    def compatible(self) -> bool:
        return self.status == ConnectionStatus.COMPATIBLE

    @property
    def requires_verification(self) -> bool:
        return self.status == ConnectionStatus.REQUIRES_VERIFICATION

    @property
    def blocked(self) -> bool:
        return self.status in {ConnectionStatus.INCOMPATIBLE, ConnectionStatus.UNRESOLVED}


def evaluate_endpoint_engagement(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
    *,
    connector_specs: dict[str, ConnectorSpec] | None = None,
    manufacturer_assessments: list[ConnectionManufacturerAssessment] | None = None,
    derived_results: list[ConnectionRuleResult] | None = None,
    verification_status: RuntimeVerificationStatus | None = None,
) -> ConnectionEvaluation:
    """Evaluate one tether endpoint against one target interface conservatively.

    Evaluation uses the strongest defensible basis available. Inconclusive geometry
    falls through. Manufacturer assessments remain attached separately from technical
    status, and only a bounded validated verification family can produce
    ``requires_verification``.
    """

    assessments = list(manufacturer_assessments or [])
    rule_results = list(derived_results or [])
    connector_specs = connector_specs or {}

    if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION:
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.INCOMPATIBLE,
            basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
            reason="source interface is not a tether connection point",
            assessments=assessments,
            rule_results=rule_results,
        )

    if target.role not in _CONNECTABLE_TARGET_ROLES:
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.INCOMPATIBLE,
            basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
            reason="target interface is not a connectable tether-side interface",
            assessments=assessments,
            rule_results=rule_results,
        )

    if _has_authoritative_source_conflict(assessments):
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.UNRESOLVED,
            basis=CompatibilityBasis.NONE,
            reason="authoritative manufacturer evidence conflicts for the same connection scope",
            assessments=assessments,
            rule_results=rule_results,
            contradiction_type=ContradictionType.AUTHORITATIVE_SOURCE_CONFLICT,
            review_required=True,
        )

    technical_prohibition = next(
        (
            assessment
            for assessment in assessments
            if assessment.authoritative
            and assessment.position == ManufacturerPosition.EXPLICITLY_PROHIBITED
            and assessment.technical_causal_scope_established
        ),
        None,
    )
    if technical_prohibition is not None:
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.INCOMPATIBLE,
            basis=CompatibilityBasis.MANUFACTURER_DECLARED,
            reason="manufacturer prohibition establishes a technical failure mode for this connection",
            assessments=assessments,
            rule_results=rule_results,
        )

    side_result = _side_rule_result(endpoint, target)
    if side_result is not None:
        rule_results.insert(0, side_result)

    connector_spec = (
        connector_specs.get(endpoint.connector_spec_ref)
        if endpoint.connector_spec_ref is not None
        else None
    )
    verification_family = _verification_family(endpoint, target, connector_spec)
    geometry_result = _gate_admission_geometry_result(
        endpoint,
        target,
        connector_spec,
        verification_family=verification_family,
    )
    if geometry_result is not None:
        rule_results.append(geometry_result)

    manufacturer_declaration = next(
        (
            assessment
            for assessment in assessments
            if assessment.authoritative
            and assessment.position == ManufacturerPosition.EXPLICITLY_COMPATIBLE
        ),
        None,
    )

    conclusive_results = [result for result in rule_results if result.status is not None]
    incompatible_results = [
        result for result in conclusive_results if result.status == ConnectionStatus.INCOMPATIBLE
    ]
    compatible_results = [
        result for result in conclusive_results if result.status == ConnectionStatus.COMPATIBLE
    ]

    if manufacturer_declaration is not None:
        hard_physical = next(
            (result for result in incompatible_results if result.hard_physical),
            None,
        )
        if hard_physical is not None:
            return _evaluation(
                endpoint,
                target,
                status=ConnectionStatus.UNRESOLVED,
                basis=CompatibilityBasis.NONE,
                reason="manufacturer compatibility declaration conflicts with accepted primitive physical facts",
                assessments=assessments,
                rule_results=rule_results,
                contradiction_type=ContradictionType.HARD_PHYSICAL_CONTRADICTION,
                review_required=True,
            )

        if incompatible_results:
            return _evaluation(
                endpoint,
                target,
                status=ConnectionStatus.COMPATIBLE,
                basis=CompatibilityBasis.MANUFACTURER_DECLARED,
                reason="manufacturer compatibility declaration is operative despite a non-hard derived-rule disagreement",
                assessments=assessments,
                rule_results=rule_results,
                contradiction_type=ContradictionType.DERIVED_RULE_DISAGREEMENT,
                review_required=True,
            )

        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.COMPATIBLE,
            basis=CompatibilityBasis.MANUFACTURER_DECLARED,
            reason="accepted manufacturer declaration establishes this connection",
            assessments=assessments,
            rule_results=rule_results,
        )

    if incompatible_results and compatible_results:
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.UNRESOLVED,
            basis=CompatibilityBasis.NONE,
            reason="conclusive reusable technical rules disagree",
            assessments=assessments,
            rule_results=rule_results,
            review_required=True,
        )

    if incompatible_results:
        result = incompatible_results[0]
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.INCOMPATIBLE,
            basis=result.basis,
            reason=result.reason,
            assessments=assessments,
            rule_results=rule_results,
        )

    if compatible_results:
        result = compatible_results[0]
        return _evaluation(
            endpoint,
            target,
            status=ConnectionStatus.COMPATIBLE,
            basis=result.basis,
            reason=result.reason,
            assessments=assessments,
            rule_results=rule_results,
        )

    if verification_family is not None:
        runtime_status = verification_status or RuntimeVerificationStatus.PENDING
        if runtime_status == RuntimeVerificationStatus.PASSED:
            status = ConnectionStatus.COMPATIBLE
            reason = "bounded runtime verification passed for the observed connection"
        elif runtime_status == RuntimeVerificationStatus.FAILED:
            status = ConnectionStatus.INCOMPATIBLE
            reason = "bounded runtime verification failed for the observed connection"
        else:
            status = ConnectionStatus.REQUIRES_VERIFICATION
            reason = "catalogue evidence supports a bounded runtime verification path"

        return _evaluation(
            endpoint,
            target,
            status=status,
            basis=CompatibilityBasis.RUNTIME_VERIFICATION,
            reason=reason,
            assessments=assessments,
            rule_results=rule_results,
            verification_status=runtime_status,
            verification_family=verification_family,
        )

    return _evaluation(
        endpoint,
        target,
        status=ConnectionStatus.UNRESOLVED,
        basis=CompatibilityBasis.NONE,
        reason="interface topology is plausible but no validated geometry rule proves engagement",
        assessments=assessments,
        rule_results=rule_results,
    )


def _side_rule_result(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
) -> ConnectionRuleResult | None:
    if target.role in {
        ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
    } and endpoint.tether_side == TetherSide.ANCHOR_SIDE:
        return ConnectionRuleResult(
            rule_id="endpoint_side_semantics.v1",
            basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
            status=ConnectionStatus.INCOMPATIBLE,
            reason="anchor-side-only tether endpoint cannot serve the tool side",
        )

    if target.role in {
        ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.CONTAINER_CONNECTION,
    } and endpoint.tether_side == TetherSide.TOOL_SIDE:
        return ConnectionRuleResult(
            rule_id="endpoint_side_semantics.v1",
            basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
            status=ConnectionStatus.INCOMPATIBLE,
            reason="tool-side-only tether endpoint cannot serve the anchor side",
        )

    return None


def _verification_family(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
    connector_spec: ConnectorSpec | None,
) -> str | None:
    """Return a validated bounded verification family, never a compatibility claim."""

    if endpoint.interface_type not in _GATED_CONNECTOR_TYPES:
        return None
    if target.interface_type not in _CLOSED_INTERFACE_TYPES:
        return None
    if connector_spec is None or connector_spec.opening_action_count is None:
        # A type label plus target label is not enough. Current ingestion must also
        # establish that the referenced discrete connector has an opening action.
        return None
    return "gated_connector_to_closed_interface.v1"


def _gate_admission_geometry_result(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
    connector_spec: ConnectorSpec | None,
    *,
    verification_family: str | None,
) -> ConnectionRuleResult | None:
    """Evaluate the one narrow geometry condition already justified by the model.

    A closed-interface section larger than the accepted maximum gate opening proves
    admission impossible. A passing or incomplete comparison does not prove full safe
    engagement and therefore deliberately falls through to later bases.
    """

    if verification_family is None or connector_spec is None:
        return None

    gate_opening = connector_spec.dimensions_mm.get("gate_opening")
    section_diameter = target.dimensions_mm.get("feature_section_diameter")

    if gate_opening is None or section_diameter is None:
        return ConnectionRuleResult(
            rule_id="gated_connector_closed_interface_admission.v1",
            basis=CompatibilityBasis.VALIDATED_GEOMETRY,
            status=None,
            reason="gate-admission geometry is incomplete and cannot conclude engagement",
        )

    if section_diameter > gate_opening:
        return ConnectionRuleResult(
            rule_id="gated_connector_closed_interface_admission.v1",
            basis=CompatibilityBasis.VALIDATED_GEOMETRY,
            status=ConnectionStatus.INCOMPATIBLE,
            reason="closed-interface section is larger than the accepted maximum gate opening",
            hard_physical=True,
        )

    return ConnectionRuleResult(
        rule_id="gated_connector_closed_interface_admission.v1",
        basis=CompatibilityBasis.VALIDATED_GEOMETRY,
        status=None,
        reason="gate-admission geometry passes but does not establish complete safe engagement",
    )


def _has_authoritative_source_conflict(
    assessments: list[ConnectionManufacturerAssessment],
) -> bool:
    compatible_scopes = {
        _normalized_scope(assessment.scope)
        for assessment in assessments
        if assessment.authoritative
        and assessment.position == ManufacturerPosition.EXPLICITLY_COMPATIBLE
    }
    prohibited_scopes = {
        _normalized_scope(assessment.scope)
        for assessment in assessments
        if assessment.authoritative
        and assessment.position == ManufacturerPosition.EXPLICITLY_PROHIBITED
    }
    return bool(compatible_scopes & prohibited_scopes)


def _normalized_scope(scope: str) -> str:
    return " ".join(scope.strip().casefold().split())


def _evaluation(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
    *,
    status: ConnectionStatus,
    basis: CompatibilityBasis,
    reason: str,
    assessments: list[ConnectionManufacturerAssessment],
    rule_results: list[ConnectionRuleResult],
    verification_status: RuntimeVerificationStatus | None = None,
    verification_family: str | None = None,
    contradiction_type: ContradictionType | None = None,
    review_required: bool = False,
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=status,
        basis=basis,
        endpoint_id=endpoint.interface_id,
        target_interface_id=target.interface_id,
        reason=reason,
        manufacturer_assessments=assessments,
        rule_results=rule_results,
        verification_status=verification_status,
        verification_family=verification_family,
        contradiction_type=contradiction_type,
        review_required=review_required,
    )


def _validate_dimensions(dimensions: Any) -> Any:
    if not isinstance(dimensions, dict):
        return dimensions
    for key, value in dimensions.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"dimension {key!r} must be a finite positive number")
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"dimension {key!r} must be a finite positive number") from exc
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError(f"dimension {key!r} must be a finite positive number")
    return dimensions


_CONNECTABLE_TARGET_ROLES = {
    ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
    ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
    ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
    ConnectionInterfaceRole.CONTAINER_CONNECTION,
}

_GATED_CONNECTOR_TYPES = {
    "carabiner",
    "snap_hook",
}

_CLOSED_INTERFACE_TYPES = {
    "ring",
    "dedicated_eye",
    "captive_hole",
    "closed_handle",
}
