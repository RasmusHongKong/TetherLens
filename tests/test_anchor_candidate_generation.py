import pytest

from tetherlens_ingest.anchor_installation import (
    AnchorAttachmentInstallationRule,
    AnchorEligibilityPath,
    AnchorFeaturePredicate,
    AnchorInstallationMethod,
    PrimaryAnchorFeature,
    PrimaryAnchorFeatureKind,
    ResolvedPrimaryAnchor,
    bound_anchor_installation_evaluation,
    evaluate_anchor_installation_eligibility,
    resolve_anchor_installation_bindings,
)
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.recommendation import (
    CandidateCheckStatus,
    CandidateConfiguration,
    RecommendationState,
    evaluate_candidate_configuration,
)


def _direct_tool_ring() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="tool-ring",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )


def _anchor_d_ring() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="anchor-d-ring",
        role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        attributes={"ring_form": "d_ring"},
    )


def _tether() -> TetherOption:
    tool_spec = "tether:tool-carabiner"
    anchor_spec = "tether:anchor-carabiner"
    return TetherOption(
        tether_ref="tether:1",
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref="tether:1",
            rated_capacity_kg=10.0,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="tool-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec,
            ),
            ConnectionInterface(
                interface_id="anchor-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec,
            ),
        ],
        connector_specs={
            tool_spec: ConnectorSpec(
                connector_spec_id=tool_spec,
                opening_action_count=2,
            ),
            anchor_spec: ConnectorSpec(
                connector_spec_id=anchor_spec,
                opening_action_count=2,
            ),
        },
    )


def _wrap_rule() -> AnchorAttachmentInstallationRule:
    return AnchorAttachmentInstallationRule(
        rule_id="wrap-beam",
        source_product_ref="anchor-product:1",
        installation_method=AnchorInstallationMethod.WRAP,
        paths=[
            AnchorEligibilityPath(
                binding_name="beam",
                requirements=[
                    AnchorFeaturePredicate(
                        property_key="feature_kind",
                        value=PrimaryAnchorFeatureKind.BEAM.value,
                    )
                ],
            )
        ],
        source_urls=["https://manufacturer.example/anchor-product"],
    )


def _binding():
    rule = _wrap_rule()
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="primary-anchor:beam-zone",
        features=[
            PrimaryAnchorFeature(
                feature_id="beam:west",
                feature_kind=PrimaryAnchorFeatureKind.BEAM,
            )
        ],
    )
    [binding] = resolve_anchor_installation_bindings(rule, anchor)
    return binding


def _bound_anchor_path() -> AnchorPathOption:
    binding = _binding()
    return AnchorPathOption(
        anchor_path_ref="anchor-path:beam-west",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor-strap",
                source_product_ref="anchor-product:1",
                rated_capacity_kg=10.0,
            )
        ],
        target_interfaces=[_anchor_d_ring()],
        installation_binding=binding,
        installation_eligibility=bound_anchor_installation_evaluation(binding),
    )


def test_bound_anchor_path_requires_selected_component_product_to_match_rule() -> None:
    binding = _binding()

    with pytest.raises(ValueError, match="selected anchor component product"):
        AnchorPathOption(
            anchor_path_ref="anchor-path:1",
            components=[
                CandidateComponentOption(
                    component_ref="component:other-anchor",
                    source_product_ref="anchor-product:other",
                    rated_capacity_kg=10.0,
                )
            ],
            target_interfaces=[_anchor_d_ring()],
            installation_binding=binding,
            installation_eligibility=bound_anchor_installation_evaluation(binding),
        )


def test_candidate_generation_preserves_exact_anchor_binding_and_hard_check() -> None:
    path = _bound_anchor_path()
    binding = path.installation_binding
    assert binding is not None

    [candidate] = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[_direct_tool_ring()],
        ),
        [_tether()],
        [path],
    )

    assert candidate.selection.anchor_installation_binding == binding
    assert candidate.configuration.anchor_installation_eligibility is not None
    assert {
        match.feature_id
        for match in candidate.configuration.anchor_installation_eligibility.matches
    } == {"beam:west"}
    assert "primary-anchor:beam-zone" in candidate.configuration.candidate_id
    assert "beam:west" in candidate.configuration.candidate_id
    assert "wrap-beam" in candidate.configuration.candidate_id

    evaluation = evaluate_candidate_configuration(candidate.configuration)
    anchor_check = next(
        check
        for check in evaluation.checks
        if check.check_id == "anchor_installation_eligibility"
    )
    assert anchor_check.status == CandidateCheckStatus.PASSED
    assert anchor_check.subject_refs == [
        "anchor-product:1",
        "primary-anchor:beam-zone",
        "wrap-beam",
        "beam:west",
    ]
    assert anchor_check.source_urls == ["https://manufacturer.example/anchor-product"]
    assert evaluation.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS


def test_direct_candidate_evaluation_blocks_ambiguous_anchor_feature_matches() -> None:
    [candidate] = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[_direct_tool_ring()],
        ),
        [_tether()],
        [_bound_anchor_path()],
    )
    ambiguous_eligibility = evaluate_anchor_installation_eligibility(
        _wrap_rule(),
        ResolvedPrimaryAnchor(
            primary_anchor_ref="primary-anchor:beam-zone",
            features=[
                PrimaryAnchorFeature(
                    feature_id="beam:east",
                    feature_kind=PrimaryAnchorFeatureKind.BEAM,
                ),
                PrimaryAnchorFeature(
                    feature_id="beam:west",
                    feature_kind=PrimaryAnchorFeatureKind.BEAM,
                ),
            ],
        ),
    )
    direct_configuration = CandidateConfiguration.model_validate(
        {
            **candidate.configuration.model_dump(),
            "anchor_installation_eligibility": ambiguous_eligibility.model_dump(),
        }
    )

    evaluation = evaluate_candidate_configuration(direct_configuration)
    anchor_check = next(
        check
        for check in evaluation.checks
        if check.check_id == "anchor_installation_eligibility"
    )

    assert anchor_check.status == CandidateCheckStatus.UNRESOLVED
    assert "one concrete installation feature" in anchor_check.reason
    assert anchor_check.subject_refs == [
        "anchor-product:1",
        "primary-anchor:beam-zone",
        "wrap-beam",
        "beam:east",
        "beam:west",
    ]
    assert evaluation.recommendation_state is None


def test_generated_candidate_rejects_anchor_eligibility_for_different_feature() -> None:
    binding = _binding()
    wrong_binding = binding.model_copy(update={"installation_feature_id": "beam:east"})

    with pytest.raises(ValueError, match="selected primary-anchor feature"):
        AnchorPathOption(
            anchor_path_ref="anchor-path:bad-binding",
            components=[
                CandidateComponentOption(
                    component_ref="component:anchor-strap",
                    source_product_ref="anchor-product:1",
                    rated_capacity_kg=10.0,
                )
            ],
            target_interfaces=[_anchor_d_ring()],
            installation_binding=wrong_binding,
            installation_eligibility=bound_anchor_installation_evaluation(binding),
        )


def test_unbound_legacy_anchor_path_preserves_canonical_candidate_id() -> None:
    path = AnchorPathOption(
        anchor_path_ref="anchor-path:legacy",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor-legacy",
                source_product_ref="anchor-product:legacy",
                rated_capacity_kg=10.0,
            )
        ],
        target_interfaces=[_anchor_d_ring()],
    )

    [candidate] = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:1",
            object_mass_kg=2.0,
            direct_interfaces=[_direct_tool_ring()],
        ),
        [_tether()],
        [path],
    )

    assert candidate.configuration.candidate_id == (
        'candidate:{"anchor_endpoint_id":"anchor-end",'
        '"anchor_path_ref":"anchor-path:legacy",'
        '"anchor_target_interface_id":"anchor-d-ring",'
        '"attachment_assembly_ref":null,'
        '"component_refs":["component:tether","component:anchor-legacy"],'
        '"installation_feature_id":null,'
        '"tether_ref":"tether:1",'
        '"tool_endpoint_id":"tool-end",'
        '"tool_ref":"tool:1",'
        '"tool_target_interface_id":"tool-ring"}'
    )
