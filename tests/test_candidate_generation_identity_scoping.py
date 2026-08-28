import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ProductConstraintRuntimeState,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    EligibilityPath,
    FeatureKind,
    FeaturePredicate,
    ToolInterfaceFeature,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import (
    ProductConstraintDisposition,
    ProductConstraintStatus,
    ResolvedProductConstraint,
)
from tetherlens_ingest.models import ClaimSubjectType, ConstraintOperator
from tetherlens_ingest.recommendation import (
    CandidateCheckType,
    RecommendationState,
    evaluate_candidate_configuration,
)


def direct_ring(interface_id: str) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )


def attachment_ring(interface_id: str) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )


def container_ring(interface_id: str) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )


def carabiner_endpoint(
    interface_id: str,
    *,
    side: TetherSide,
    connector_spec_ref: str,
) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref=connector_spec_ref,
    )


def tether_option() -> TetherOption:
    return TetherOption(
        tether_ref="product:tether",
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref="product:tether",
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            carabiner_endpoint(
                "tool_side",
                side=TetherSide.TOOL_SIDE,
                connector_spec_ref="connector:tool",
            ),
            carabiner_endpoint(
                "anchor_side",
                side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref="connector:anchor",
            ),
        ],
        connector_specs={
            "connector:tool": ConnectorSpec(
                connector_spec_id="connector:tool",
                opening_action_count=2,
            ),
            "connector:anchor": ConnectorSpec(
                connector_spec_id="connector:anchor",
                opening_action_count=2,
            ),
        },
        max_length_mm=1200.0,
    )


def anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor",
                source_product_ref="product:anchor",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[container_ring("anchor_ring")],
    )


def handle_eligibility() -> AttachmentEligibility:
    return AttachmentEligibility(
        paths=[
            EligibilityPath(
                binding_name="handle",
                requirements=[
                    FeaturePredicate(property_key="feature_kind", value="handle")
                ],
            )
        ]
    )


def minimum_bond_time_constraint() -> ResolvedProductConstraint:
    return ResolvedProductConstraint(
        constraint_id="product:adhesive:product:self:minimum_bond_time_h:1",
        source_product_ref="product:adhesive",
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref="self",
        constraint_key="minimum_bond_time_h",
        operator=ConstraintOperator.GTE,
        value=24.0,
        unit="h",
        disposition=ProductConstraintDisposition.PRE_USE_OBLIGATION,
    )


def test_resolved_tool_rejects_duplicate_feature_ids_before_eligibility_binding():
    with pytest.raises(ValueError, match="feature ids must be unique"):
        ResolvedToolCandidate(
            tool_ref="tool:1",
            features=[
                ToolInterfaceFeature(
                    feature_id="feature:shared",
                    feature_kind=FeatureKind.HANDLE,
                ),
                ToolInterfaceFeature(
                    feature_id="feature:shared",
                    feature_kind=FeatureKind.SURFACE,
                    attributes={"surface_profile": "flat"},
                ),
            ],
        )


def test_owner_local_interface_ids_must_be_unique():
    with pytest.raises(ValueError, match="direct interface ids must be unique"):
        ResolvedToolCandidate(
            tool_ref="tool:1",
            direct_interfaces=[direct_ring("shared"), direct_ring("shared")],
        )

    with pytest.raises(ValueError, match="provided interface ids must be unique"):
        ToolAttachmentAssemblyOption(
            assembly_ref="assembly:1",
            components=[
                CandidateComponentOption(
                    component_ref="component:attachment",
                    source_product_ref="product:attachment",
                )
            ],
            eligibility=handle_eligibility(),
            provided_interfaces=[attachment_ring("shared"), attachment_ring("shared")],
        )

    with pytest.raises(ValueError, match="target interface ids must be unique"):
        AnchorPathOption(
            anchor_path_ref="anchor:path",
            target_interfaces=[container_ring("shared"), container_ring("shared")],
        )


def test_repeated_source_product_instances_keep_canonical_constraint_and_instance_identity():
    constraint = minimum_bond_time_constraint()
    assembly = ToolAttachmentAssemblyOption(
        assembly_ref="assembly:two-adhesives",
        components=[
            CandidateComponentOption(
                component_ref="component:adhesive-a",
                source_product_ref="product:adhesive",
                rated_capacity_kg=3.0,
                product_constraints=[constraint],
            ),
            CandidateComponentOption(
                component_ref="component:adhesive-b",
                source_product_ref="product:adhesive",
                rated_capacity_kg=3.0,
                product_constraints=[constraint],
            ),
        ],
        eligibility=handle_eligibility(),
        provided_interfaces=[attachment_ring("attachment_ring")],
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            features=[
                ToolInterfaceFeature(
                    feature_id="feature:handle",
                    feature_kind=FeatureKind.HANDLE,
                )
            ],
        ),
        [tether_option()],
        [anchor_path()],
        tool_attachment_assemblies=[assembly],
        product_runtime_state={
            "component:adhesive-a": ProductConstraintRuntimeState(bond_elapsed_h=24.0),
            "component:adhesive-b": ProductConstraintRuntimeState(bond_elapsed_h=2.0),
        },
    )

    assert len(generated) == 1
    evaluations = generated[0].configuration.product_constraint_evaluations
    adhesive_evaluations = [
        evaluation
        for evaluation in evaluations
        if evaluation.constraint_id == constraint.constraint_id
    ]
    assert len(adhesive_evaluations) == 2
    assert {evaluation.constraint_id for evaluation in adhesive_evaluations} == {
        constraint.constraint_id
    }
    assert {
        evaluation.component_ref: evaluation.status
        for evaluation in adhesive_evaluations
    } == {
        "component:adhesive-a": ProductConstraintStatus.PASSED,
        "component:adhesive-b": ProductConstraintStatus.REQUIRES_ACTION,
    }

    result = evaluate_candidate_configuration(generated[0].configuration)
    assert result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS

    constraint_checks = [
        check
        for check in result.checks
        if check.check_type == CandidateCheckType.PRODUCT_CONSTRAINT
    ]
    assert {check.check_id for check in constraint_checks} == {
        "product_constraint:component=component:adhesive-a|constraint="
        + constraint.constraint_id,
        "product_constraint:component=component:adhesive-b|constraint="
        + constraint.constraint_id,
    }
    assert {
        tuple(check.subject_refs)
        for check in constraint_checks
    } == {
        ("component:adhesive-a",),
        ("component:adhesive-b",),
    }
    assert result.pending_action_constraint_ids == [
        "component=component:adhesive-b|constraint=" + constraint.constraint_id
    ]
