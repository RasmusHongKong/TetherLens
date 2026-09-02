import pytest

from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateSelectedComponent,
    EligibilityProof,
    GeneratedCandidate,
    ProductConstraintRuntimeState,
    _candidate_id,
)
from tetherlens_ingest.candidate_selection import rank_and_select_candidates
from tetherlens_ingest.compatibility import (
    EligibilityEvaluation,
    EligibilityMatch,
    EligibilityStatus,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    GatedConnectorClosedInterfaceVerification,
    LockingMode,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.constraints import (
    ProductConstraintContext,
    ProductConstraintDisposition,
    ResolvedProductConstraint,
    evaluate_product_constraints,
)
from tetherlens_ingest.models import ClaimSubjectType, ConstraintOperator
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateConfiguration,
    LoadBearingComponent,
    PolicyApplicability,
    evaluate_candidate_configuration,
)
from tetherlens_ingest.recommendation_run import RecommendationRunResult
from tetherlens_ingest.recommendation_session import (
    SessionConditionKind,
    SessionConditionOutcome,
    resolve_recommendation_session,
)
from tetherlens_ingest.recommendation_session_adapter import (
    derive_connection_session_resolution,
    derive_product_action_session_resolution,
)


def compatible_connection(
    *,
    endpoint_id: str,
    target_id: str,
    target_role: ConnectionInterfaceRole,
    side: TetherSide,
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=ConnectionStatus.COMPATIBLE,
        basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=side,
        target_role=target_role,
        reason="test connection is already compatible",
    )


def completed_verification(
    *,
    locking_mechanism_engaged: bool | None = True,
    gate_unobstructed: bool = True,
) -> GatedConnectorClosedInterfaceVerification:
    return GatedConnectorClosedInterfaceVerification(
        target_fully_captured=True,
        gate_closed_completely=True,
        locking_mechanism_engaged=locking_mechanism_engaged,
        gate_unobstructed=gate_unobstructed,
        intended_loaded_orientation=True,
        stable_seating_no_cross_loading=True,
        no_adjacent_interference=True,
    )


def recommendation_session(candidate: GeneratedCandidate):
    evaluation = evaluate_candidate_configuration(candidate.configuration)
    selection = rank_and_select_candidates([candidate], [evaluation])
    run = RecommendationRunResult(
        generated_candidates=[candidate],
        evaluations=[evaluation],
        selection=selection,
    )
    return run, resolve_recommendation_session(run)


def direct_runtime_candidate(
    *,
    locking_mode: LockingMode = LockingMode.UNKNOWN,
) -> GeneratedCandidate:
    endpoint = ConnectionInterface(
        interface_id="endpoint:tool",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.TOOL_SIDE,
        connector_spec_ref="connector:tool",
    )
    target = ConnectionInterface(
        interface_id="tool:ring",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )
    connector_spec = ConnectorSpec(
        connector_spec_id="connector:tool",
        opening_action_count=2,
        locking_mode=locking_mode,
    )
    pending_connection = evaluate_endpoint_engagement(
        endpoint,
        target,
        connector_specs={connector_spec.connector_spec_id: connector_spec},
    )
    selection = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="anchor:1",
        tool_endpoint_id="endpoint:tool",
        tool_target_interface_id="tool:ring",
        anchor_endpoint_id="endpoint:anchor",
        anchor_target_interface_id="anchor:ring",
        components=[
            CandidateSelectedComponent(
                component_ref="component:tether",
                source_product_ref="tether:1",
                role=CandidateComponentRole.TETHER,
            )
        ],
    )
    candidate_id = _candidate_id(selection)
    return GeneratedCandidate(
        selection=selection,
        configuration=CandidateConfiguration(
            candidate_id=candidate_id,
            object_mass_kg=1.0,
            load_bearing_components=[
                LoadBearingComponent(
                    component_id="component:tether",
                    rated_capacity_kg=5.0,
                )
            ],
            tether_max_length_mm=1200.0,
            attachment_mode=CandidateAttachmentMode.DIRECT,
            tool_side_connection=pending_connection,
            anchor_side_connection=compatible_connection(
                endpoint_id="endpoint:anchor",
                target_id="anchor:ring",
                target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                side=TetherSide.ANCHOR_SIDE,
            ),
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
        ),
    )


def pre_use_constraint(
    *,
    constraint_key: str,
    value,
    operator: ConstraintOperator,
) -> ResolvedProductConstraint:
    return ResolvedProductConstraint(
        constraint_id=f"product:attachment:product:self:{constraint_key}:1",
        source_product_ref="product:attachment",
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref="self",
        constraint_key=constraint_key,
        operator=operator,
        value=value,
        unit="h" if constraint_key == "minimum_bond_time_h" else None,
        disposition=ProductConstraintDisposition.PRE_USE_OBLIGATION,
    )


def tool_attachment_action_candidate(
    constraint: ResolvedProductConstraint,
) -> GeneratedCandidate:
    action_evaluation = evaluate_product_constraints(
        [constraint],
        ProductConstraintContext(),
    )[0].model_copy(update={"component_ref": "component:attachment"})

    selection = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="anchor:1",
        attachment_assembly_ref="assembly:1",
        installation_feature_id="feature:surface",
        eligibility_proofs=[EligibilityProof(path_index=0, binding_name="surface")],
        tool_endpoint_id="endpoint:tool",
        tool_target_interface_id="attachment:ring",
        anchor_endpoint_id="endpoint:anchor",
        anchor_target_interface_id="anchor:ring",
        components=[
            CandidateSelectedComponent(
                component_ref="component:attachment",
                source_product_ref="product:attachment",
                role=CandidateComponentRole.TOOL_ATTACHMENT,
            ),
            CandidateSelectedComponent(
                component_ref="component:tether",
                source_product_ref="tether:1",
                role=CandidateComponentRole.TETHER,
            ),
        ],
    )
    candidate_id = _candidate_id(selection)
    return GeneratedCandidate(
        selection=selection,
        configuration=CandidateConfiguration(
            candidate_id=candidate_id,
            object_mass_kg=1.0,
            load_bearing_components=[
                LoadBearingComponent(
                    component_id="component:attachment",
                    rated_capacity_kg=3.0,
                ),
                LoadBearingComponent(
                    component_id="component:tether",
                    rated_capacity_kg=5.0,
                ),
            ],
            tether_max_length_mm=1200.0,
            product_constraint_evaluations=[action_evaluation],
            attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
            attachment_eligibility=EligibilityEvaluation(
                status=EligibilityStatus.ELIGIBLE,
                matches=[
                    EligibilityMatch(
                        path_index=0,
                        binding_name="surface",
                        feature_id="feature:surface",
                    )
                ],
            ),
            tool_side_connection=compatible_connection(
                endpoint_id="endpoint:tool",
                target_id="attachment:ring",
                target_role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
                side=TetherSide.TOOL_SIDE,
            ),
            anchor_side_connection=compatible_connection(
                endpoint_id="endpoint:anchor",
                target_id="anchor:ring",
                target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                side=TetherSide.ANCHOR_SIDE,
            ),
            policy_applicability=PolicyApplicability.NOT_APPLICABLE,
        ),
    )


def test_connection_adapter_returns_none_until_bounded_observations_are_terminal():
    candidate = direct_runtime_candidate()
    run, session = recommendation_session(candidate)
    original_evaluation = run.evaluations[0].model_copy(deep=True)
    condition = session.active_pending_conditions[0]

    resolution = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=GatedConnectorClosedInterfaceVerification(
            target_fully_captured=True,
            gate_closed_completely=True,
        ),
    )

    assert resolution is None
    assert run.evaluations[0] == original_evaluation


def test_connection_adapter_maps_primitive_pass_and_failure_without_mutating_original():
    candidate = direct_runtime_candidate()
    run, session = recommendation_session(candidate)
    original_evaluation = run.evaluations[0].model_copy(deep=True)
    condition = session.active_pending_conditions[0]

    passed = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=completed_verification(),
    )
    failed = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=completed_verification(gate_unobstructed=False),
    )

    assert passed is not None
    assert passed.condition_kind == SessionConditionKind.RUNTIME_VERIFICATION
    assert passed.outcome == SessionConditionOutcome.SATISFIED
    assert failed is not None
    assert failed.outcome == SessionConditionOutcome.FAILED
    assert run.evaluations[0] == original_evaluation


def test_connection_adapter_preserves_unknown_locking_requirement():
    candidate = direct_runtime_candidate(locking_mode=LockingMode.UNKNOWN)
    _, session = recommendation_session(candidate)
    condition = session.active_pending_conditions[0]

    resolution = derive_connection_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        observations=completed_verification(locking_mechanism_engaged=None),
    )

    assert resolution is None


def test_connection_adapter_rejects_non_active_candidate_identity():
    candidate = direct_runtime_candidate()
    _, session = recommendation_session(candidate)
    condition = session.active_pending_conditions[0]

    with pytest.raises(ValueError, match="current active candidate"):
        derive_connection_session_resolution(
            session,
            candidate_id="candidate:other",
            condition_id=condition.condition_id,
            observations=completed_verification(),
        )


def test_bond_time_action_remains_pending_until_existing_constraint_passes():
    constraint = pre_use_constraint(
        constraint_key="minimum_bond_time_h",
        value=24.0,
        operator=ConstraintOperator.GTE,
    )
    candidate = tool_attachment_action_candidate(constraint)
    run, session = recommendation_session(candidate)
    original_evaluation = run.evaluations[0].model_copy(deep=True)
    condition = next(
        condition
        for condition in session.active_pending_conditions
        if condition.condition_kind == SessionConditionKind.PRE_USE_ACTION
    )

    still_pending = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=ProductConstraintRuntimeState(
            component_ref="component:attachment",
            installation_feature_id="feature:surface",
            bond_elapsed_h=12.0,
        ),
    )
    satisfied = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=ProductConstraintRuntimeState(
            component_ref="component:attachment",
            installation_feature_id="feature:surface",
            bond_elapsed_h=24.0,
        ),
    )

    assert still_pending is None
    assert satisfied is not None
    assert satisfied.outcome == SessionConditionOutcome.SATISFIED
    assert run.evaluations[0] == original_evaluation


def test_required_attachment_test_failure_rejects_via_primitive_failure():
    constraint = pre_use_constraint(
        constraint_key="pre_use_attachment_test_required",
        value=True,
        operator=ConstraintOperator.REQUIRES,
    )
    candidate = tool_attachment_action_candidate(constraint)
    _, session = recommendation_session(candidate)
    condition = next(
        condition
        for condition in session.active_pending_conditions
        if condition.condition_kind == SessionConditionKind.PRE_USE_ACTION
    )

    failed = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=ProductConstraintRuntimeState(
            component_ref="component:attachment",
            installation_feature_id="feature:surface",
            pre_use_attachment_test_passed=False,
        ),
    )

    assert failed is not None
    assert failed.outcome == SessionConditionOutcome.FAILED


def test_product_action_adapter_rejects_component_or_feature_leakage():
    constraint = pre_use_constraint(
        constraint_key="minimum_bond_time_h",
        value=24.0,
        operator=ConstraintOperator.GTE,
    )
    candidate = tool_attachment_action_candidate(constraint)
    _, session = recommendation_session(candidate)
    condition = next(
        condition
        for condition in session.active_pending_conditions
        if condition.condition_kind == SessionConditionKind.PRE_USE_ACTION
    )

    with pytest.raises(ValueError, match="exact component instance"):
        derive_product_action_session_resolution(
            session,
            candidate_id=candidate.configuration.candidate_id,
            condition_id=condition.condition_id,
            runtime_state=ProductConstraintRuntimeState(
                component_ref="component:other",
                installation_feature_id="feature:surface",
                bond_elapsed_h=24.0,
            ),
        )

    with pytest.raises(ValueError, match="installation-feature binding"):
        derive_product_action_session_resolution(
            session,
            candidate_id=candidate.configuration.candidate_id,
            condition_id=condition.condition_id,
            runtime_state=ProductConstraintRuntimeState(
                component_ref="component:attachment",
                installation_feature_id="feature:other",
                bond_elapsed_h=24.0,
            ),
        )
