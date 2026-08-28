import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    CandidateComponentRole,
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
    CandidateAttachmentMode,
    CandidateCheckStatus,
    RecommendationState,
    evaluate_candidate_configuration,
)


def direct_ring(interface_id: str = "tool_ring") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )


def attachment_ring(interface_id: str = "attachment_ring") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )


def container_ring(interface_id: str = "container_ring") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )


def carabiner_endpoint(
    endpoint_id: str,
    *,
    side: TetherSide,
    spec_ref: str,
) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=endpoint_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref=spec_ref,
    )


def tether_option() -> TetherOption:
    return TetherOption(
        tether_ref="product:tether-1",
        component=CandidateComponentOption(
            component_ref="component:tether-1",
            source_product_ref="product:tether-1",
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            carabiner_endpoint(
                "tether:tool-end",
                side=TetherSide.TOOL_SIDE,
                spec_ref="connector:tool-end",
            ),
            carabiner_endpoint(
                "tether:anchor-end",
                side=TetherSide.ANCHOR_SIDE,
                spec_ref="connector:anchor-end",
            ),
        ],
        connector_specs={
            "connector:tool-end": ConnectorSpec(
                connector_spec_id="connector:tool-end",
                opening_action_count=2,
            ),
            "connector:anchor-end": ConnectorSpec(
                connector_spec_id="connector:anchor-end",
                opening_action_count=2,
            ),
        },
        max_length_mm=1200.0,
    )


def anchor_path(*, target: ConnectionInterface | None = None) -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path-1",
        components=[
            CandidateComponentOption(
                component_ref="component:container-1",
                source_product_ref="product:container-1",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[target or container_ring()],
    )


def surface_profile_constraint(
    *,
    source_product_ref: str = "product:attachment-1",
) -> ResolvedProductConstraint:
    return ResolvedProductConstraint(
        constraint_id=(
            f"{source_product_ref}:product:self:installation_surface_profile:1"
        ),
        source_product_ref=source_product_ref,
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref="self",
        constraint_key="installation_surface_profile",
        operator=ConstraintOperator.REQUIRES,
        value="flat",
        disposition=ProductConstraintDisposition.HARD,
    )


def test_direct_candidate_generation_binds_endpoint_sides_and_existing_evaluator():
    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[direct_ring()],
        ),
        [tether_option()],
        [anchor_path()],
    )

    assert len(generated) == 1
    candidate = generated[0]
    assert candidate.selection.attachment_assembly_ref is None
    assert candidate.selection.installation_feature_id is None
    assert candidate.selection.tool_endpoint_id == "tether:tool-end"
    assert candidate.selection.anchor_endpoint_id == "tether:anchor-end"
    assert candidate.configuration.attachment_mode == CandidateAttachmentMode.DIRECT
    assert [component.role for component in candidate.selection.components] == [
        CandidateComponentRole.TETHER,
        CandidateComponentRole.ANCHOR,
    ]

    result = evaluate_candidate_configuration(candidate.configuration)
    assert result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert result.pending_verification_connection_ids == [
        "connection:tether:tool-end->tool_ring",
        "connection:tether:anchor-end->container_ring",
    ]


def test_tool_attachment_generation_creates_one_candidate_per_bound_feature():
    tool = ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        features=[
            ToolInterfaceFeature(
                feature_id="feature:flat",
                feature_kind=FeatureKind.SURFACE,
                attributes={"surface_profile": "flat"},
            ),
            ToolInterfaceFeature(
                feature_id="feature:curved",
                feature_kind=FeatureKind.SURFACE,
                attributes={"surface_profile": "curved"},
            ),
        ],
    )
    assembly = ToolAttachmentAssemblyOption(
        assembly_ref="assembly:adhesive-ring",
        components=[
            CandidateComponentOption(
                component_ref="component:attachment-1",
                source_product_ref="product:attachment-1",
                rated_capacity_kg=3.0,
                product_constraints=[surface_profile_constraint()],
            )
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="surface",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="surface")
                    ],
                )
            ]
        ),
        provided_interfaces=[attachment_ring()],
    )

    generated = generate_candidate_configurations(
        tool,
        [tether_option()],
        [anchor_path()],
        tool_attachment_assemblies=[assembly],
    )

    assert {candidate.selection.installation_feature_id for candidate in generated} == {
        "feature:flat",
        "feature:curved",
    }
    assert all(
        candidate.configuration.attachment_mode == CandidateAttachmentMode.TOOL_ATTACHMENT
        for candidate in generated
    )
    assert all(
        len(candidate.configuration.attachment_eligibility.matches) == 1
        for candidate in generated
    )

    by_feature = {
        candidate.selection.installation_feature_id: candidate for candidate in generated
    }
    flat_constraint = by_feature["feature:flat"].configuration.product_constraint_evaluations[0]
    curved_constraint = by_feature["feature:curved"].configuration.product_constraint_evaluations[0]

    assert flat_constraint.installation_feature_id == "feature:flat"
    assert flat_constraint.status == ProductConstraintStatus.PASSED
    assert curved_constraint.installation_feature_id == "feature:curved"
    assert curved_constraint.status == ProductConstraintStatus.FAILED

    flat_result = evaluate_candidate_configuration(by_feature["feature:flat"].configuration)
    curved_result = evaluate_candidate_configuration(by_feature["feature:curved"].configuration)
    assert flat_result.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert curved_result.recommendation_state is None
    assert any(
        check.status == CandidateCheckStatus.FAILED
        for check in curved_result.checks
        if check.check_id.startswith("product_constraint:")
    )


def test_multi_component_attachment_assembly_keeps_component_identity_separate_from_load_path():
    tool = ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        features=[
            ToolInterfaceFeature(
                feature_id="feature:handle",
                feature_kind=FeatureKind.HANDLE,
            )
        ],
    )
    assembly = ToolAttachmentAssemblyOption(
        assembly_ref="assembly:two-part",
        components=[
            CandidateComponentOption(
                component_ref="component:strap",
                source_product_ref="product:strap",
                rated_capacity_kg=3.0,
            ),
            CandidateComponentOption(
                component_ref="component:retainer",
                source_product_ref="product:retainer",
                load_bearing=False,
            ),
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle")
                    ],
                )
            ]
        ),
        provided_interfaces=[attachment_ring()],
    )

    candidate = generate_candidate_configurations(
        tool,
        [tether_option()],
        [anchor_path()],
        tool_attachment_assemblies=[assembly],
    )[0]

    assert [component.component_ref for component in candidate.selection.components] == [
        "component:strap",
        "component:retainer",
        "component:tether-1",
        "component:container-1",
    ]
    assert [component.component_id for component in candidate.configuration.load_bearing_components] == [
        "component:strap",
        "component:tether-1",
        "component:container-1",
    ]


def test_generator_keeps_structurally_admissible_candidate_when_connection_is_unresolved():
    unknown_anchor = ConnectionInterface(
        interface_id="anchor:unknown-form",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="unknown",
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[direct_ring()],
        ),
        [tether_option()],
        [anchor_path(target=unknown_anchor)],
    )

    assert len(generated) == 1
    result = evaluate_candidate_configuration(generated[0].configuration)
    assert result.recommendation_state is None
    assert any(
        check.status == CandidateCheckStatus.UNRESOLVED
        and check.subject_refs == ["tether:anchor-end", "anchor:unknown-form"]
        for check in result.checks
    )


def test_unknown_endpoint_side_is_not_promoted_to_either_during_generation():
    tether = tether_option().model_copy(
        update={
            "endpoints": [
                *tether_option().endpoints,
                carabiner_endpoint(
                    "tether:unknown-end",
                    side=TetherSide.UNKNOWN,
                    spec_ref="connector:unknown-end",
                ),
            ]
        }
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[direct_ring()],
        ),
        [tether],
        [anchor_path()],
    )

    assert len(generated) == 1
    assert generated[0].selection.tool_endpoint_id == "tether:tool-end"
    assert generated[0].selection.anchor_endpoint_id == "tether:anchor-end"


def test_component_constraints_must_match_their_source_product_identity():
    with pytest.raises(ValueError, match="source product identity"):
        CandidateComponentOption(
            component_ref="component:attachment-1",
            source_product_ref="product:attachment-1",
            rated_capacity_kg=3.0,
            product_constraints=[
                surface_profile_constraint(source_product_ref="product:other")
            ],
        )


def test_ineligible_attachment_assembly_does_not_manufacture_an_unbound_candidate():
    assembly = ToolAttachmentAssemblyOption(
        assembly_ref="assembly:handle-only",
        components=[
            CandidateComponentOption(
                component_ref="component:attachment-1",
                source_product_ref="product:attachment-1",
                rated_capacity_kg=3.0,
            )
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle")
                    ],
                )
            ]
        ),
        provided_interfaces=[attachment_ring()],
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            features=[
                ToolInterfaceFeature(
                    feature_id="feature:opening",
                    feature_kind=FeatureKind.THROUGH_OPENING,
                )
            ],
        ),
        [tether_option()],
        [anchor_path()],
        tool_attachment_assemblies=[assembly],
    )

    assert generated == []
