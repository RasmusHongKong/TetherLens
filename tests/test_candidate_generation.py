import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    CandidateComponentRole,
    ConnectionEvaluationContext,
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
    PolicyStatus,
    ToolInterfaceFeature,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionRuleResult,
    ConnectionStatus,
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
    PolicyApplicability,
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


def tether_option(
    *,
    tether_ref: str = "product:tether-1",
    component_ref: str = "component:tether-1",
    tool_endpoint_id: str = "tether:tool-end",
    anchor_endpoint_id: str = "tether:anchor-end",
) -> TetherOption:
    tool_spec_ref = f"{tether_ref}:connector:tool-end"
    anchor_spec_ref = f"{tether_ref}:connector:anchor-end"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=component_ref,
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            carabiner_endpoint(
                tool_endpoint_id,
                side=TetherSide.TOOL_SIDE,
                spec_ref=tool_spec_ref,
            ),
            carabiner_endpoint(
                anchor_endpoint_id,
                side=TetherSide.ANCHOR_SIDE,
                spec_ref=anchor_spec_ref,
            ),
        ],
        connector_specs={
            tool_spec_ref: ConnectorSpec(
                connector_spec_id=tool_spec_ref,
                opening_action_count=2,
            ),
            anchor_spec_ref: ConnectorSpec(
                connector_spec_id=anchor_spec_ref,
                opening_action_count=2,
            ),
        },
        max_length_mm=1200.0,
    )


def anchor_path(
    *,
    anchor_path_ref: str = "anchor:path-1",
    component_ref: str = "component:container-1",
    target: ConnectionInterface | None = None,
    policy_applicability: PolicyApplicability = PolicyApplicability.NOT_APPLICABLE,
    policy_status: PolicyStatus | None = None,
) -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref=anchor_path_ref,
        components=[
            CandidateComponentOption(
                component_ref=component_ref,
                source_product_ref=f"product:{anchor_path_ref}",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[target or container_ring()],
        policy_applicability=policy_applicability,
        policy_status=policy_status,
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
    assert candidate.selection.eligibility_proofs == []
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


def test_overlapping_eligibility_paths_are_proofs_for_one_physical_candidate():
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
        assembly_ref="assembly:overlap",
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
                    binding_name="handle-general",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle")
                    ],
                ),
                EligibilityPath(
                    binding_name="handle-alternate-proof",
                    requirements=[
                        FeaturePredicate(property_key="feature_kind", value="handle")
                    ],
                ),
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

    assert len(generated) == 1
    candidate = generated[0]
    assert candidate.selection.installation_feature_id == "feature:handle"
    assert [(proof.path_index, proof.binding_name) for proof in candidate.selection.eligibility_proofs] == [
        (0, "handle-general"),
        (1, "handle-alternate-proof"),
    ]
    assert len(candidate.configuration.attachment_eligibility.matches) == 2
    assert {
        match.feature_id for match in candidate.configuration.attachment_eligibility.matches
    } == {"feature:handle"}
    assert "eligibility_path=" not in candidate.configuration.candidate_id


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


def test_connection_contexts_are_scoped_by_owning_tether_and_target_option():
    tool_target = direct_ring("tether_side_ring")
    first_tether = tether_option(
        tether_ref="product:tether-a",
        component_ref="component:tether-a",
        tool_endpoint_id="tool_side",
        anchor_endpoint_id="anchor_side",
    )
    second_tether = tether_option(
        tether_ref="product:tether-b",
        component_ref="component:tether-b",
        tool_endpoint_id="tool_side",
        anchor_endpoint_id="anchor_side",
    )
    context = ConnectionEvaluationContext(
        tether_ref="product:tether-a",
        target_owner_ref="tool:1",
        endpoint_id="tool_side",
        target_interface_id="tether_side_ring",
        derived_results=[
            ConnectionRuleResult(
                rule_id="test.scoped-compatible",
                basis=CompatibilityBasis.VALIDATED_INTERFACE_CLASS,
                status=ConnectionStatus.COMPATIBLE,
                reason="test scoped context establishes compatibility",
            )
        ],
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[tool_target],
        ),
        [first_tether, second_tether],
        [anchor_path()],
        connection_contexts=[context],
    )

    by_tether = {candidate.selection.tether_ref: candidate for candidate in generated}
    assert by_tether["product:tether-a"].configuration.tool_side_connection.status == ConnectionStatus.COMPATIBLE
    assert by_tether["product:tether-b"].configuration.tool_side_connection.status == ConnectionStatus.REQUIRES_VERIFICATION


def test_policy_is_scoped_to_each_anchor_path_not_broadcast_across_generation():
    permitted = anchor_path(
        anchor_path_ref="anchor:structural",
        component_ref="component:structural",
    )
    prohibited = anchor_path(
        anchor_path_ref="anchor:person",
        component_ref="component:person",
        policy_applicability=PolicyApplicability.APPLICABLE,
        policy_status=PolicyStatus.PROHIBITED,
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[direct_ring()],
        ),
        [tether_option()],
        [permitted, prohibited],
    )

    by_anchor = {candidate.selection.anchor_path_ref: candidate for candidate in generated}
    assert by_anchor["anchor:structural"].configuration.policy_applicability == PolicyApplicability.NOT_APPLICABLE
    assert by_anchor["anchor:structural"].configuration.policy_status is None
    assert by_anchor["anchor:person"].configuration.policy_applicability == PolicyApplicability.APPLICABLE
    assert by_anchor["anchor:person"].configuration.policy_status == PolicyStatus.PROHIBITED

    assert evaluate_candidate_configuration(
        by_anchor["anchor:structural"].configuration
    ).recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert evaluate_candidate_configuration(
        by_anchor["anchor:person"].configuration
    ).recommendation_state is None


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


def test_duplicate_option_refs_are_rejected_before_context_scoping():
    with pytest.raises(ValueError, match="tether_ref values must be unique"):
        generate_candidate_configurations(
            ResolvedToolCandidate(
                tool_ref="tool:1",
                object_mass_kg=2.0,
                direct_interfaces=[direct_ring()],
            ),
            [
                tether_option(component_ref="component:tether-a"),
                tether_option(component_ref="component:tether-b"),
            ],
            [anchor_path()],
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
