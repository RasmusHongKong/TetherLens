import pytest

from tetherlens_ingest.compatibility import (
    EligibilityEvaluation,
    EligibilityMatch,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
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
    ProductConstraintResolutionError,
    ProductConstraintStatus,
    evaluate_product_constraints,
    resolve_product_constraints,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimType,
    ConstraintOperator,
)
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateCheckStatus,
    CandidateConfiguration,
    LoadBearingComponent,
    PolicyApplicability,
    RecommendationState,
    evaluate_candidate_configuration,
)


def claim(
    key: str,
    value,
    *,
    operator: ConstraintOperator | None = None,
    claim_type: ClaimType | None = ClaimType.DECLARED_CONSTRAINT,
    unit: str | None = None,
    source_url: str = "https://example.test/source-a",
) -> CandidateClaim:
    return CandidateClaim(
        property_key=key,
        value=value,
        unit=unit,
        raw_value=f"{key}={value}",
        source_url=source_url,
        extractor="test.v1",
        claim_type=claim_type,
        constraint_operator=operator,
    )


def test_resolver_normalizes_supported_constraints_without_flattening_atomic_conditions():
    claims = [
        claim(
            "installation_surface_profile",
            "flat",
            operator=ConstraintOperator.REQUIRES,
        ),
        claim(
            "required_surface_condition",
            "clean",
            operator=ConstraintOperator.REQUIRES,
        ),
        claim(
            "required_surface_condition",
            "clean",
            operator=ConstraintOperator.REQUIRES,
            source_url="https://example.test/source-b",
        ),
        claim(
            "required_surface_condition",
            "grease_free",
            operator=ConstraintOperator.REQUIRES,
        ),
        claim(
            "prohibited_tool_part_type",
            "removable_cover_or_door",
            operator=ConstraintOperator.PROHIBITS,
        ),
        claim(
            "minimum_bond_time_h",
            24.0,
            operator=ConstraintOperator.GTE,
            unit="h",
        ),
        claim(
            "pre_use_attachment_test_required",
            True,
            operator=ConstraintOperator.REQUIRES,
        ),
        # Transitional NLG limit: this predates declared-constraint metadata but has
        # already-established max-lanyard semantics.
        claim(
            "max_lanyard_length_mm",
            1500.0,
            claim_type=None,
            operator=None,
            unit="mm",
        ),
        # Category scope remains outside the generic technical evaluator until its
        # manufacturer-assessment/technical meaning is explicitly resolved.
        claim(
            "applicable_tool_category_code",
            "angle_grinder",
            operator=ConstraintOperator.REQUIRES,
        ),
    ]

    resolved = resolve_product_constraints(claims)

    assert len(resolved) == 7
    assert {constraint.constraint_key for constraint in resolved} == {
        "installation_surface_profile",
        "required_surface_condition",
        "prohibited_tool_part_type",
        "minimum_bond_time_h",
        "pre_use_attachment_test_required",
        "max_lanyard_length_mm",
    }

    clean = next(
        constraint
        for constraint in resolved
        if constraint.constraint_key == "required_surface_condition"
        and constraint.value == "clean"
    )
    assert clean.source_urls == [
        "https://example.test/source-a",
        "https://example.test/source-b",
    ]

    lanyard = next(
        constraint for constraint in resolved if constraint.constraint_key == "max_lanyard_length_mm"
    )
    assert lanyard.operator == ConstraintOperator.LTE


def test_resolver_fails_closed_on_wrong_operator_for_supported_constraint():
    with pytest.raises(ProductConstraintResolutionError, match="expected 'requires'"):
        resolve_product_constraints(
            [
                claim(
                    "installation_surface_profile",
                    "flat",
                    operator=ConstraintOperator.PROHIBITS,
                )
            ]
        )


def test_installation_constraints_stay_bound_to_one_feature():
    constraints = resolve_product_constraints(
        [
            claim(
                "installation_surface_profile",
                "flat",
                operator=ConstraintOperator.REQUIRES,
            ),
            claim(
                "prohibited_tool_part_type",
                "removable_cover_or_door",
                operator=ConstraintOperator.PROHIBITS,
            ),
        ]
    )

    flat_but_removable = ToolInterfaceFeature(
        feature_id="battery_door",
        feature_kind=FeatureKind.SURFACE,
        attributes={
            "surface_profile": "flat",
            "part_type": "removable_cover_or_door",
        },
    )
    curved_but_fixed = ToolInterfaceFeature(
        feature_id="fixed_housing",
        feature_kind=FeatureKind.SURFACE,
        attributes={
            "surface_profile": "curved",
            "part_type": "fixed_housing",
        },
    )

    first = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(installation_feature=flat_but_removable),
    )
    second = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(installation_feature=curved_but_fixed),
    )

    assert [evaluation.status for evaluation in first] == [
        ProductConstraintStatus.PASSED,
        ProductConstraintStatus.FAILED,
    ]
    assert [evaluation.status for evaluation in second] == [
        ProductConstraintStatus.FAILED,
        ProductConstraintStatus.PASSED,
    ]
    assert not all(evaluation.status == ProductConstraintStatus.PASSED for evaluation in first)
    assert not all(evaluation.status == ProductConstraintStatus.PASSED for evaluation in second)


def test_missing_feature_local_fact_remains_unresolved():
    constraints = resolve_product_constraints(
        [
            claim(
                "required_surface_condition",
                "grease_free",
                operator=ConstraintOperator.REQUIRES,
            )
        ]
    )
    feature = ToolInterfaceFeature(
        feature_id="surface-a",
        feature_kind=FeatureKind.SURFACE,
        attributes={"surface_profile": "flat"},
    )

    result = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(installation_feature=feature),
    )[0]

    assert result.status == ProductConstraintStatus.UNRESOLVED
    assert result.subject_refs == ["surface-a"]


def test_lanyard_limit_is_evaluated_from_normalized_constraint():
    constraint = resolve_product_constraints(
        [
            claim(
                "max_lanyard_length_mm",
                1500.0,
                claim_type=None,
                unit="mm",
            )
        ]
    )

    within = evaluate_product_constraints(
        constraint,
        ProductConstraintContext(tether_max_length_mm=1200.0),
    )[0]
    too_long = evaluate_product_constraints(
        constraint,
        ProductConstraintContext(tether_max_length_mm=1800.0),
    )[0]

    assert within.status == ProductConstraintStatus.PASSED
    assert too_long.status == ProductConstraintStatus.FAILED


def test_pre_use_requirements_are_pending_actions_until_satisfied():
    constraints = resolve_product_constraints(
        [
            claim(
                "minimum_bond_time_h",
                24.0,
                operator=ConstraintOperator.GTE,
                unit="h",
            ),
            claim(
                "pre_use_attachment_test_required",
                True,
                operator=ConstraintOperator.REQUIRES,
            ),
        ]
    )

    pending = evaluate_product_constraints(constraints, ProductConstraintContext())
    completed = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(
            bond_elapsed_h=24.0,
            pre_use_attachment_test_passed=True,
        ),
    )
    failed_test = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(
            bond_elapsed_h=24.0,
            pre_use_attachment_test_passed=False,
        ),
    )

    assert all(
        evaluation.status == ProductConstraintStatus.REQUIRES_ACTION
        for evaluation in pending
    )
    assert all(
        evaluation.status == ProductConstraintStatus.PASSED
        for evaluation in completed
    )
    assert any(
        evaluation.constraint_key == "pre_use_attachment_test_required"
        and evaluation.status == ProductConstraintStatus.FAILED
        for evaluation in failed_test
    )


def compatible_connection(
    *,
    endpoint_id: str,
    target_id: str,
    target_role: ConnectionInterfaceRole,
    tether_side: TetherSide,
) -> ConnectionEvaluation:
    return ConnectionEvaluation(
        status=ConnectionStatus.COMPATIBLE,
        basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
        endpoint_id=endpoint_id,
        target_interface_id=target_id,
        endpoint_tether_side=tether_side,
        target_role=target_role,
        reason="test connection is compatible",
    )


def eligible_attachment() -> EligibilityEvaluation:
    return EligibilityEvaluation(
        status=EligibilityStatus.ELIGIBLE,
        matches=[
            EligibilityMatch(
                path_index=0,
                binding_name="surface",
                feature_id="surface-a",
            )
        ],
    )


def candidate_with_constraints(evaluations) -> CandidateConfiguration:
    return CandidateConfiguration(
        candidate_id="constraint-candidate",
        object_mass_kg=1.0,
        load_bearing_components=[
            LoadBearingComponent(component_id="attachment", rated_capacity_kg=2.0),
            LoadBearingComponent(component_id="tether", rated_capacity_kg=3.0),
        ],
        attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
        attachment_eligibility=eligible_attachment(),
        product_constraint_evaluations=evaluations,
        tool_side_connection=compatible_connection(
            endpoint_id="tool_endpoint",
            target_id="attachment_ring",
            target_role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
            tether_side=TetherSide.TOOL_SIDE,
        ),
        anchor_side_connection=compatible_connection(
            endpoint_id="anchor_endpoint",
            target_id="container_ring",
            target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
            tether_side=TetherSide.ANCHOR_SIDE,
        ),
        policy_applicability=PolicyApplicability.NOT_APPLICABLE,
    )


def test_pending_pre_use_action_produces_constrained_recommendation_without_claiming_verification():
    constraints = resolve_product_constraints(
        [
            claim(
                "minimum_bond_time_h",
                24.0,
                operator=ConstraintOperator.GTE,
                unit="h",
            )
        ]
    )
    evaluations = evaluate_product_constraints(constraints, ProductConstraintContext())

    result = evaluate_candidate_configuration(candidate_with_constraints(evaluations))

    assert result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert result.has_constraints is True
    assert result.requires_action is True
    assert result.requires_verification is False
    assert result.pending_verification_connection_ids == []
    assert result.pending_action_constraint_ids == [evaluations[0].constraint_id]
    assert any(
        check.status == CandidateCheckStatus.REQUIRES_ACTION
        for check in result.checks
    )


def test_failed_or_unresolved_product_constraint_blocks_candidate():
    constraint = resolve_product_constraints(
        [
            claim(
                "installation_surface_profile",
                "flat",
                operator=ConstraintOperator.REQUIRES,
            )
        ]
    )
    failed = evaluate_product_constraints(
        constraint,
        ProductConstraintContext(
            installation_feature=ToolInterfaceFeature(
                feature_id="surface-a",
                feature_kind=FeatureKind.SURFACE,
                attributes={"surface_profile": "curved"},
            )
        ),
    )
    unresolved = evaluate_product_constraints(constraint, ProductConstraintContext())

    failed_result = evaluate_candidate_configuration(candidate_with_constraints(failed))
    unresolved_result = evaluate_candidate_configuration(candidate_with_constraints(unresolved))

    assert failed_result.recommendation_state is None
    assert unresolved_result.recommendation_state is None
    assert failed_result.pending_action_constraint_ids == []
    assert unresolved_result.pending_action_constraint_ids == []
