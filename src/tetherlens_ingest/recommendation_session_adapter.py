from __future__ import annotations

from .candidate_generation import CandidateComponentRole, ProductConstraintRuntimeState
from .candidate_selection import EvaluatedCandidate
from .connection import (
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionStatus,
    GatedConnectorClosedInterfaceVerification,
    RuntimeVerificationStatus,
    evaluate_gated_connector_closed_interface_verification,
)
from .constraints import (
    ProductConstraintContext,
    ProductConstraintDisposition,
    ProductConstraintEvaluation,
    ProductConstraintStatus,
    evaluate_product_constraints,
)
from .recommendation_session import (
    RecommendationSessionResult,
    RecommendationSessionState,
    SessionConditionKind,
    SessionConditionOutcome,
    SessionConditionRef,
    SessionConditionResolution,
)


_GATED_CONNECTOR_CLOSED_INTERFACE_FAMILY = "gated_connector_to_closed_interface.v1"


def derive_connection_session_resolution(
    session: RecommendationSessionResult,
    *,
    candidate_id: str,
    condition_id: str,
    observations: GatedConnectorClosedInterfaceVerification,
) -> SessionConditionResolution | None:
    """Derive one terminal connection condition from bounded structured observations.

    The original hard evaluation remains immutable. This adapter only targets a
    currently pending runtime-verification condition on the active session candidate
    and delegates pass/fail semantics to the bounded connection verifier retained by
    that original evaluation.
    """

    candidate = _require_active_pending_condition(
        session,
        candidate_id=candidate_id,
        condition_kind=SessionConditionKind.RUNTIME_VERIFICATION,
        condition_id=condition_id,
    )
    connection = _pending_connection(candidate, condition_id)

    if connection.basis != CompatibilityBasis.RUNTIME_VERIFICATION:
        raise ValueError(
            "pending connection condition must retain runtime-verification as its original basis"
        )
    if connection.verification_status != RuntimeVerificationStatus.PENDING:
        raise ValueError(
            "pending connection condition must retain a pending primitive verification status"
        )
    if connection.verification_family != _GATED_CONNECTOR_CLOSED_INTERFACE_FAMILY:
        raise ValueError(
            "connection session adapter supports only the original bounded "
            "gated-connector/closed-interface verification family"
        )
    if connection.verification_connector_spec is None:
        raise ValueError(
            "pending connection condition is missing the retained connector specification "
            "required by its primitive verifier"
        )

    status = evaluate_gated_connector_closed_interface_verification(
        connection.verification_connector_spec,
        observations,
    )
    if status == RuntimeVerificationStatus.PENDING:
        return None
    if status == RuntimeVerificationStatus.PASSED:
        outcome = SessionConditionOutcome.SATISFIED
    elif status == RuntimeVerificationStatus.FAILED:
        outcome = SessionConditionOutcome.FAILED
    else:  # pragma: no cover - exhaustive guard for future enum expansion
        raise ValueError(f"unsupported runtime verification status {status!r}")

    return SessionConditionResolution(
        candidate_id=candidate_id,
        condition_kind=SessionConditionKind.RUNTIME_VERIFICATION,
        condition_id=condition_id,
        outcome=outcome,
    )


def derive_product_action_session_resolution(
    session: RecommendationSessionResult,
    *,
    candidate_id: str,
    condition_id: str,
    runtime_state: ProductConstraintRuntimeState,
) -> SessionConditionResolution | None:
    """Derive one terminal pre-use condition from normalized candidate-local facts.

    The adapter re-evaluates only the exact normalized product constraint retained by
    the original candidate configuration. It does not re-run candidate generation or
    hard candidate evaluation and it does not accept a caller-supplied pass/fail result.
    """

    candidate = _require_active_pending_condition(
        session,
        candidate_id=candidate_id,
        condition_kind=SessionConditionKind.PRE_USE_ACTION,
        condition_id=condition_id,
    )
    evaluation = _pending_product_constraint(candidate, condition_id)
    resolved = evaluation.resolved_constraint
    if resolved is None:
        raise ValueError(
            "pending pre-use condition is missing its retained normalized product constraint"
        )
    if resolved.disposition != ProductConstraintDisposition.PRE_USE_OBLIGATION:
        raise ValueError(
            "session pre-use adapter may evaluate only constraints originally normalized "
            "as pre-use obligations"
        )
    if resolved.constraint_id != evaluation.constraint_id:
        raise ValueError(
            "retained normalized product constraint identity does not match its original evaluation"
        )
    if evaluation.component_ref is None:
        raise ValueError(
            "pending pre-use condition must retain the physical component instance it applies to"
        )

    selected_component = next(
        (
            component
            for component in candidate.generated_candidate.selection.components
            if component.component_ref == evaluation.component_ref
        ),
        None,
    )
    if selected_component is None:
        raise ValueError(
            "pending pre-use condition component is not part of the active generated candidate"
        )
    if selected_component.source_product_ref != resolved.source_product_ref:
        raise ValueError(
            "pending pre-use condition source-product identity does not match the active component"
        )

    expected_feature_id = (
        candidate.generated_candidate.selection.installation_feature_id
        if selected_component.role == CandidateComponentRole.TOOL_ATTACHMENT
        else None
    )
    if runtime_state.component_ref != evaluation.component_ref:
        raise ValueError(
            "product runtime facts must target the exact component instance from the active condition"
        )
    if runtime_state.installation_feature_id != expected_feature_id:
        raise ValueError(
            "product runtime facts must retain the active candidate's exact installation-feature binding"
        )

    primitive = evaluate_product_constraints(
        [resolved],
        ProductConstraintContext(
            tether_max_length_mm=(
                candidate.generated_candidate.configuration.tether_max_length_mm
            ),
            bond_elapsed_h=runtime_state.bond_elapsed_h,
            pre_use_attachment_test_passed=runtime_state.pre_use_attachment_test_passed,
        ),
    )[0]
    if primitive.constraint_id != evaluation.constraint_id:
        raise ValueError(
            "primitive product evaluator returned a different constraint identity"
        )

    if primitive.status == ProductConstraintStatus.REQUIRES_ACTION:
        return None
    if primitive.status == ProductConstraintStatus.PASSED:
        outcome = SessionConditionOutcome.SATISFIED
    elif primitive.status == ProductConstraintStatus.FAILED:
        outcome = SessionConditionOutcome.FAILED
    elif primitive.status == ProductConstraintStatus.UNRESOLVED:
        raise ValueError(
            "pending pre-use condition became unresolved under the retained primitive evaluator"
        )
    else:  # pragma: no cover - exhaustive guard for future enum expansion
        raise ValueError(f"unsupported product constraint status {primitive.status!r}")

    return SessionConditionResolution(
        candidate_id=candidate_id,
        condition_kind=SessionConditionKind.PRE_USE_ACTION,
        condition_id=condition_id,
        outcome=outcome,
    )


def _require_active_pending_condition(
    session: RecommendationSessionResult,
    *,
    candidate_id: str,
    condition_kind: SessionConditionKind,
    condition_id: str,
) -> EvaluatedCandidate:
    if (
        session.state != RecommendationSessionState.ACTIVE
        or session.active_candidate is None
    ):
        raise ValueError("session condition evidence requires an active candidate")
    if session.active_candidate.candidate_id != candidate_id:
        raise ValueError(
            "session condition evidence may target only the current active candidate"
        )

    condition = SessionConditionRef(
        candidate_id=candidate_id,
        condition_kind=condition_kind,
        condition_id=condition_id,
    )
    if condition not in session.active_pending_conditions:
        raise ValueError(
            "session condition evidence must target an unresolved original pending condition "
            "with the same candidate, kind and identifier"
        )
    return session.active_candidate


def _pending_connection(
    candidate: EvaluatedCandidate,
    condition_id: str,
) -> ConnectionEvaluation:
    pending_connections = [
        connection
        for connection in candidate.evaluation.connections
        if connection.status == ConnectionStatus.REQUIRES_VERIFICATION
    ]
    condition_ids = candidate.evaluation.pending_verification_connection_ids
    if len(pending_connections) != len(condition_ids):
        raise ValueError(
            "original candidate evaluation has inconsistent pending connection identity coverage"
        )

    for pending_id, connection in zip(condition_ids, pending_connections, strict=True):
        if pending_id == condition_id:
            return connection
    raise ValueError("pending runtime-verification condition has no matching original connection")


def _pending_product_constraint(
    candidate: EvaluatedCandidate,
    condition_id: str,
) -> ProductConstraintEvaluation:
    pending_evaluations = [
        evaluation
        for evaluation in candidate.generated_candidate.configuration.product_constraint_evaluations
        if evaluation.status == ProductConstraintStatus.REQUIRES_ACTION
    ]
    condition_ids = candidate.evaluation.pending_action_constraint_ids
    if len(pending_evaluations) != len(condition_ids):
        raise ValueError(
            "original candidate evaluation has inconsistent pending product-action identity coverage"
        )

    for pending_id, evaluation in zip(condition_ids, pending_evaluations, strict=True):
        if pending_id == condition_id:
            return evaluation
    raise ValueError("pending pre-use condition has no matching original product constraint")
