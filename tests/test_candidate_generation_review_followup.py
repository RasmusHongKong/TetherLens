import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    CandidateComponentRole,
    CandidatePathSelection,
    CandidatePolicyContext,
    CandidateSelectedComponent,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
    _candidate_id,
    generate_candidate_configurations,
)
from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    EligibilityPath,
    FeaturePredicate,
    PolicyStatus,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.recommendation import (
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


def container_ring(interface_id: str = "anchor_ring") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )


def endpoint(interface_id: str, *, side: TetherSide, spec_ref: str) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref=spec_ref,
    )


def tether(tether_ref: str, component_ref: str) -> TetherOption:
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=component_ref,
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            endpoint("tool_end", side=TetherSide.TOOL_SIDE, spec_ref=tool_spec_ref),
            endpoint("anchor_end", side=TetherSide.ANCHOR_SIDE, spec_ref=anchor_spec_ref),
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
    )


def anchor_path(**kwargs) -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor",
                source_product_ref="product:anchor",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[container_ring()],
        **kwargs,
    )


def handle_eligibility() -> AttachmentEligibility:
    return AttachmentEligibility(
        paths=[
            EligibilityPath(
                binding_name="handle",
                requirements=[FeaturePredicate(property_key="feature_kind", value="handle")],
            )
        ]
    )


def test_tool_attachment_assembly_requires_a_load_bearing_component():
    with pytest.raises(ValueError, match="at least one load-bearing component"):
        ToolAttachmentAssemblyOption(
            assembly_ref="assembly:non-load-bearing",
            components=[
                CandidateComponentOption(
                    component_ref="component:retainer",
                    source_product_ref="product:retainer",
                    load_bearing=False,
                )
            ],
            eligibility=handle_eligibility(),
            provided_interfaces=[attachment_ring()],
        )


def test_tether_rejects_connector_spec_map_key_identity_mismatch():
    with pytest.raises(ValueError, match="map keys must match"):
        TetherOption(
            tether_ref="product:tether",
            component=CandidateComponentOption(
                component_ref="component:tether",
                source_product_ref="product:tether",
                rated_capacity_kg=5.0,
            ),
            endpoints=[
                endpoint(
                    "tool_end",
                    side=TetherSide.TOOL_SIDE,
                    spec_ref="connector:tool",
                ),
                endpoint(
                    "anchor_end",
                    side=TetherSide.ANCHOR_SIDE,
                    spec_ref="connector:anchor",
                ),
            ],
            connector_specs={
                "connector:tool": ConnectorSpec(
                    connector_spec_id="connector:other",
                    opening_action_count=2,
                ),
                "connector:anchor": ConnectorSpec(
                    connector_spec_id="connector:anchor",
                    opening_action_count=2,
                ),
            },
        )


def test_candidate_id_structured_encoding_prevents_delimiter_collisions():
    component = CandidateSelectedComponent(
        component_ref="component:tether",
        source_product_ref="product:tether",
        role=CandidateComponentRole.TETHER,
    )
    first = CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="final",
        tool_endpoint_id="tool_end",
        tool_target_interface_id="target|anchor_path=shadow",
        anchor_endpoint_id="anchor_end",
        anchor_target_interface_id="anchor_ring",
        components=[component],
    )
    second = first.model_copy(
        update={
            "tool_target_interface_id": "target",
            "anchor_path_ref": "shadow|anchor_path=final",
        }
    )

    def legacy_id(selection: CandidatePathSelection) -> str:
        component_refs = ",".join(
            selected.component_ref for selected in selection.components
        )
        return "candidate|" + "|".join(
            [
                f"tool={selection.tool_ref}",
                "attachment=direct",
                "feature=none",
                f"tether={selection.tether_ref}",
                f"tool_endpoint={selection.tool_endpoint_id}",
                f"tool_target={selection.tool_target_interface_id}",
                f"anchor_path={selection.anchor_path_ref}",
                f"anchor_endpoint={selection.anchor_endpoint_id}",
                f"anchor_target={selection.anchor_target_interface_id}",
                f"components={component_refs}",
            ]
        )

    assert first != second
    assert legacy_id(first) == legacy_id(second)
    assert _candidate_id(first) != _candidate_id(second)


def test_policy_contexts_are_scoped_to_complete_candidate_selection():
    first_tether = tether("product:tether-a", "component:tether-a")
    second_tether = tether("product:tether-b", "component:tether-b")
    contexts = [
        CandidatePolicyContext(
            tool_ref="tool:1",
            tether_ref="product:tether-a",
            anchor_path_ref="anchor:path",
            tool_endpoint_id="tool_end",
            tool_target_interface_id="tool_ring",
            anchor_endpoint_id="anchor_end",
            anchor_target_interface_id="anchor_ring",
            policy_applicability=PolicyApplicability.APPLICABLE,
            policy_status=PolicyStatus.PERMITTED,
        ),
        CandidatePolicyContext(
            tool_ref="tool:1",
            tether_ref="product:tether-b",
            anchor_path_ref="anchor:path",
            tool_endpoint_id="tool_end",
            tool_target_interface_id="tool_ring",
            anchor_endpoint_id="anchor_end",
            anchor_target_interface_id="anchor_ring",
            policy_applicability=PolicyApplicability.APPLICABLE,
            policy_status=PolicyStatus.PROHIBITED,
        ),
    ]

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[direct_ring()],
        ),
        [first_tether, second_tether],
        [anchor_path()],
        policy_contexts=contexts,
    )

    by_tether = {candidate.selection.tether_ref: candidate for candidate in generated}
    assert by_tether["product:tether-a"].configuration.policy_status == PolicyStatus.PERMITTED
    assert by_tether["product:tether-b"].configuration.policy_status == PolicyStatus.PROHIBITED
    assert (
        evaluate_candidate_configuration(
            by_tether["product:tether-a"].configuration
        ).recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )
    assert (
        evaluate_candidate_configuration(
            by_tether["product:tether-b"].configuration
        ).recommendation_state
        is None
    )


def test_legacy_anchor_policy_cannot_broadcast_to_multiple_candidates():
    with pytest.raises(ValueError, match="cannot be broadcast"):
        generate_candidate_configurations(
            ResolvedToolCandidate(
                tool_ref="tool:1",
                object_mass_kg=2.0,
                direct_interfaces=[direct_ring()],
            ),
            [
                tether("product:tether-a", "component:tether-a"),
                tether("product:tether-b", "component:tether-b"),
            ],
            [
                anchor_path(
                    policy_applicability=PolicyApplicability.APPLICABLE,
                    policy_status=PolicyStatus.PERMITTED,
                )
            ],
        )
