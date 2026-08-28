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
    ProductConstraintEvaluation,
    ProductConstraintStatus,
    resolve_product_constraints,
)
from tetherlens_ingest.models import CandidateClaim, ClaimType, ConstraintOperator
from tetherlens_ingest.recommendation import (
    CandidateAttachmentMode,
    CandidateCheckStatus,
    CandidateConfiguration,
    LoadBearingComponent,
    PolicyApplicability,
    evaluate_candidate_configuration,
)


def _compatible_connection(
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
        reason="review regression connection is compatible",
    )


def _candidate(
    *,
    eligible_feature_ids: list[str],
    constraint_evaluations: list[ProductConstraintEvaluation],
) -> CandidateConfiguration:
    return CandidateConfiguration(
        candidate_id="review-regression-candidate",
        object_mass_kg=1.0,
        load_bearing_components=[
            LoadBearingComponent(component_id="attachment", rated_capacity_kg=2.0),
            LoadBearingComponent(component_id="tether", rated_capacity_kg=3.0),
        ],
        attachment_mode=CandidateAttachmentMode.TOOL_ATTACHMENT,
        attachment_eligibility=EligibilityEvaluation(
            status=EligibilityStatus.ELIGIBLE,
            matches=[
                EligibilityMatch(
                    path_index=index,
                    binding_name="surface",
                    feature_id=feature_id,
                )
                for index, feature_id in enumerate(eligible_feature_ids)
            ],
        ),
        product_constraint_evaluations=constraint_evaluations,
        tool_side_connection=_compatible_connection(
            endpoint_id="tool-endpoint",
            target_id="attachment-ring",
            target_role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
            tether_side=TetherSide.TOOL_SIDE,
        ),
        anchor_side_connection=_compatible_connection(
            endpoint_id="anchor-endpoint",
            target_id="container-ring",
            target_role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
            tether_side=TetherSide.ANCHOR_SIDE,
        ),
        policy_applicability=PolicyApplicability.NOT_APPLICABLE,
    )


def _passed_feature_constraint(
    constraint_id: str,
    feature_id: str,
    *,
    source_urls: list[str] | None = None,
) -> ProductConstraintEvaluation:
    return ProductConstraintEvaluation(
        constraint_id=constraint_id,
        constraint_key="opaque_feature_scoped_constraint",
        status=ProductConstraintStatus.PASSED,
        reason="constraint passed on its evaluated installation feature",
        subject_refs=[feature_id],
        source_urls=source_urls or [],
        installation_feature_id=feature_id,
    )


def test_feature_scoped_constraint_cannot_pass_on_different_feature_than_attachment_eligibility():
    result = evaluate_candidate_configuration(
        _candidate(
            eligible_feature_ids=["surface-a"],
            constraint_evaluations=[
                _passed_feature_constraint("constraint-b", "surface-b")
            ],
        )
    )

    assert result.recommendation_state is None
    check = next(
        check
        for check in result.checks
        if check.check_id == "product_constraint:constraint-b"
    )
    assert check.status == CandidateCheckStatus.UNRESOLVED
    assert "not an eligible ToolAttachment feature" in check.reason


def test_feature_scoped_constraints_must_share_one_eligible_feature():
    result = evaluate_candidate_configuration(
        _candidate(
            eligible_feature_ids=["surface-a", "surface-b"],
            constraint_evaluations=[
                _passed_feature_constraint("constraint-a", "surface-a"),
                _passed_feature_constraint("constraint-b", "surface-b"),
            ],
        )
    )

    assert result.recommendation_state is None
    product_checks = [
        check
        for check in result.checks
        if check.check_type.value == "product_constraint"
    ]
    assert product_checks
    assert all(check.status == CandidateCheckStatus.UNRESOLVED for check in product_checks)
    assert all("multiple installation features" in check.reason for check in product_checks)


def test_product_constraint_provenance_survives_candidate_composition():
    evidence_urls = [
        "https://manufacturer.test/instructions.pdf",
        "https://manufacturer.test/product-page",
    ]
    result = evaluate_candidate_configuration(
        _candidate(
            eligible_feature_ids=["surface-a"],
            constraint_evaluations=[
                _passed_feature_constraint(
                    "constraint-a",
                    "surface-a",
                    source_urls=evidence_urls,
                )
            ],
        )
    )

    check = next(
        check
        for check in result.checks
        if check.check_id == "product_constraint:constraint-a"
    )
    assert check.status == CandidateCheckStatus.PASSED
    assert check.source_urls == evidence_urls


def test_resolution_coalesces_numeric_forms_and_retains_all_supporting_urls():
    claims = [
        CandidateClaim(
            property_key="minimum_bond_time_h",
            value=24,
            unit=None,
            source_url="https://example.test/primary-a",
            supporting_source_urls=["https://example.test/support-a"],
            extractor="review-regression.v1",
            claim_type=ClaimType.DECLARED_CONSTRAINT,
            constraint_operator=ConstraintOperator.GTE,
        ),
        CandidateClaim(
            property_key="minimum_bond_time_h",
            value=24.0,
            unit="h",
            source_url="https://example.test/primary-b",
            supporting_source_urls=[
                "https://example.test/support-b",
                "https://example.test/primary-a",
            ],
            extractor="review-regression.v1",
            claim_type=ClaimType.DECLARED_CONSTRAINT,
            constraint_operator=ConstraintOperator.GTE,
        ),
    ]

    resolved = resolve_product_constraints(claims)

    assert len(resolved) == 1
    constraint = resolved[0]
    assert constraint.value == 24.0
    assert constraint.unit == "h"
    assert constraint.source_urls == [
        "https://example.test/primary-a",
        "https://example.test/support-a",
        "https://example.test/primary-b",
        "https://example.test/support-b",
    ]
