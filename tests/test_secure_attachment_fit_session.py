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
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
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


def secure_fit_candidate() -> GeneratedCandidate:
    constraint = ResolvedProductConstraint(
        constraint_id="attachment:1:product:self:secure_attachment_fit_required:1",
        source_product_ref="attachment:1",
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref="self",
        constraint_key="secure_attachment_fit_required",
        operator=ConstraintOperator.REQUIRES,
        value=True,
        disposition=ProductConstraintDisposition.PRE_USE_OBLIGATION,
    )
    action_evaluation = evaluate_product_constraints(
        [constraint], ProductConstraintContext()
    )[0].model_copy(update={"component_ref": "component:attachment"})

    selection = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="anchor:1",
        attachment_assembly_ref="assembly:1",
        installation_feature_id="feature:handle",
        eligibility_proofs=[EligibilityProof(path_index=0, binding_name="handle")],
        tool_endpoint_id="endpoint:tool",
        tool_target_interface_id="attachment:ring",
        anchor_endpoint_id="endpoint:anchor",
        anchor_target_interface_id="anchor:ring",
        components=[
            CandidateSelectedComponent(
                component_ref="component:attachment",
                source_product_ref="attachment:1",
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
            object_mass_kg=0.25,
            load_bearing_components=[
                LoadBearingComponent(
                    component_id="component:attachment",
                    rated_capacity_kg=0.5,
                ),
                LoadBearingComponent(
                    component_id="component:tether",
                    rated_capacity_kg=1.0,
                ),
            ],
            product_constraint_evaluations=[action_evaluation],
            attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
            attachment_eligibility=EligibilityEvaluation(
                status=EligibilityStatus.ELIGIBLE,
                matches=[
                    EligibilityMatch(
                        path_index=0,
                        binding_name="handle",
                        feature_id="feature:handle",
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


def active_session(candidate: GeneratedCandidate):
    evaluation = evaluate_candidate_configuration(candidate.configuration)
    selection = rank_and_select_candidates([candidate], [evaluation])
    run = RecommendationRunResult(
        generated_candidates=[candidate],
        evaluations=[evaluation],
        selection=selection,
    )
    return resolve_recommendation_session(run)


def test_secure_fit_session_condition_remains_pending_without_fit_observation() -> None:
    candidate = secure_fit_candidate()
    session = active_session(candidate)
    condition = next(
        item
        for item in session.active_pending_conditions
        if item.condition_kind == SessionConditionKind.PRE_USE_ACTION
    )

    resolution = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=ProductConstraintRuntimeState(
            component_ref="component:attachment",
            installation_feature_id="feature:handle",
        ),
    )

    assert resolution is None


def test_secure_fit_session_condition_maps_confirmed_and_unachievable_fit() -> None:
    candidate = secure_fit_candidate()
    session = active_session(candidate)
    condition = next(
        item
        for item in session.active_pending_conditions
        if item.condition_kind == SessionConditionKind.PRE_USE_ACTION
    )
    runtime_state = ProductConstraintRuntimeState(
        component_ref="component:attachment",
        installation_feature_id="feature:handle",
    )

    passed = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=runtime_state,
        secure_attachment_fit_confirmed=True,
    )
    failed = derive_product_action_session_resolution(
        session,
        candidate_id=candidate.configuration.candidate_id,
        condition_id=condition.condition_id,
        runtime_state=runtime_state,
        secure_attachment_fit_confirmed=False,
    )

    assert passed is not None
    assert passed.outcome == SessionConditionOutcome.SATISFIED
    assert failed is not None
    assert failed.outcome == SessionConditionOutcome.FAILED
