import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ConnectionEvaluationContext,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from tetherlens_ingest.candidate_selection import CandidateSelectionState
from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    EligibilityPath,
    FeatureKind,
    FeaturePredicate,
    FeatureRole,
    ManufacturerPosition,
    ToolInterfaceFeature,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.recommendation_run import run_recommendation
from tetherlens_ingest.tool_attachment_installation import (
    EvidenceBoundToolAttachmentAssemblyOption,
    ToolAttachmentInstallationBinding,
)


def _tool(tool_ref: str) -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref=tool_ref,
        object_mass_kg=2.0,
        features=[
            ToolInterfaceFeature(
                feature_id="accessory-installation-location",
                feature_kind=FeatureKind.OTHER,
                feature_role=FeatureRole.ACCESSORY_MOUNT,
                location_description="installation openings for accessories",
            ),
            ToolInterfaceFeature(
                feature_id="handle",
                feature_kind=FeatureKind.HANDLE,
                feature_role=FeatureRole.GRIP,
            ),
        ],
    )


def _tether() -> TetherOption:
    tool_spec = "tether:tool-spec"
    anchor_spec = "tether:anchor-spec"
    return TetherOption(
        tether_ref="tether:supported",
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref="tether:supported",
            rated_capacity_kg=6.8,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="endpoint:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec,
            ),
            ConnectionInterface(
                interface_id="endpoint:anchor",
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


def _anchor() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor",
                source_product_ref="anchor:product",
                rated_capacity_kg=6.8,
            )
        ],
        target_interfaces=[
            ConnectionInterface(
                interface_id="anchor:ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )


def _evidence_assembly() -> EvidenceBoundToolAttachmentAssemblyOption:
    binding = ToolAttachmentInstallationBinding(
        binding_id="binding:hilti-strap",
        tool_ref="tool:documented",
        source_product_ref="attachment:documented",
        installation_feature_id="accessory-installation-location",
        issuer_manufacturer="Example OEM",
        scope="documented retaining strap installation",
        source_urls=["https://example.test/manual"],
    )
    return EvidenceBoundToolAttachmentAssemblyOption(
        assembly_ref="assembly:documented",
        components=[
            CandidateComponentOption(
                component_ref="component:documented-attachment",
                source_product_ref="attachment:documented",
                rated_capacity_kg=6.8,
            )
        ],
        provided_interfaces=[
            ConnectionInterface(
                interface_id="documented:attachment-point",
                role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
                interface_type="attachment_point",
            )
        ],
        installation_bindings=[binding],
    )


def _generic_competitor() -> ToolAttachmentAssemblyOption:
    return ToolAttachmentAssemblyOption(
        assembly_ref="assembly:generic-handle",
        components=[
            CandidateComponentOption(
                component_ref="component:generic-attachment",
                source_product_ref="attachment:generic",
                rated_capacity_kg=6.8,
            )
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(
                            property_key="feature_kind",
                            value=FeatureKind.HANDLE.value,
                        )
                    ],
                )
            ]
        ),
        provided_interfaces=[
            ConnectionInterface(
                interface_id="generic:ring",
                role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
                interface_type="ring",
            )
        ],
    )


def _documented_connection_context() -> ConnectionEvaluationContext:
    return ConnectionEvaluationContext(
        tether_ref="tether:supported",
        target_owner_ref="assembly:documented",
        endpoint_id="endpoint:tool",
        target_interface_id="documented:attachment-point",
        manufacturer_assessments=[
            ConnectionManufacturerAssessment(
                issuer_manufacturer="Example OEM",
                scope="documented tether carabiner to retaining strap",
                position=ManufacturerPosition.EXPLICITLY_COMPATIBLE,
                claim_or_evidence_ref="https://example.test/manual",
            )
        ],
    )


def test_evidence_bound_route_retains_exact_binding_without_removing_generic_competitor():
    result = run_recommendation(
        _tool("tool:documented"),
        [_tether()],
        [_anchor()],
        tool_attachment_assemblies=[_generic_competitor()],
        evidence_bound_tool_attachment_assemblies=[_evidence_assembly()],
        connection_contexts=[_documented_connection_context()],
    )

    assert result.selection.state == CandidateSelectionState.SELECTED
    assert {
        candidate.selection.attachment_assembly_ref
        for candidate in result.generated_candidates
    } == {"assembly:documented", "assembly:generic-handle"}

    bindings_by_candidate = {
        binding.candidate_id: binding
        for binding in result.generation_tool_bindings
    }
    documented = next(
        candidate
        for candidate in result.generated_candidates
        if candidate.selection.attachment_assembly_ref == "assembly:documented"
    )
    documented_binding = bindings_by_candidate[documented.configuration.candidate_id]
    assert documented.selection.installation_feature_id == "accessory-installation-location"
    assert documented_binding.installation_feature is not None
    assert documented_binding.installation_feature.feature_kind == FeatureKind.OTHER
    assert documented_binding.attachment_installation_binding is not None
    assert (
        documented_binding.attachment_installation_binding.binding_id
        == "binding:hilti-strap"
    )

    generic = next(
        candidate
        for candidate in result.generated_candidates
        if candidate.selection.attachment_assembly_ref == "assembly:generic-handle"
    )
    assert (
        bindings_by_candidate[generic.configuration.candidate_id]
        .attachment_installation_binding
        is None
    )


def test_documented_installation_does_not_leak_to_other_tool_with_same_feature_shape():
    result = run_recommendation(
        _tool("tool:other"),
        [_tether()],
        [_anchor()],
        tool_attachment_assemblies=[_generic_competitor()],
        evidence_bound_tool_attachment_assemblies=[_evidence_assembly()],
        connection_contexts=[_documented_connection_context()],
    )

    assert {
        candidate.selection.attachment_assembly_ref
        for candidate in result.generated_candidates
    } == {"assembly:generic-handle"}
    assert all(
        binding.attachment_installation_binding is None
        for binding in result.generation_tool_bindings
    )


def test_documented_installation_fails_closed_when_named_feature_is_not_resolved():
    tool = ResolvedToolCandidate(
        tool_ref="tool:documented",
        object_mass_kg=2.0,
        features=[
            ToolInterfaceFeature(
                feature_id="handle",
                feature_kind=FeatureKind.HANDLE,
            )
        ],
    )
    result = run_recommendation(
        tool,
        [_tether()],
        [_anchor()],
        evidence_bound_tool_attachment_assemblies=[_evidence_assembly()],
        connection_contexts=[_documented_connection_context()],
    )

    assert result.selection.state == CandidateSelectionState.NO_GENERATED_CANDIDATES
    assert result.generated_candidates == []


def test_duplicate_evidence_bound_assembly_refs_are_rejected_before_generation():
    duplicate = _evidence_assembly().model_copy(deep=True)

    with pytest.raises(
        ValueError,
        match="evidence-bound ToolAttachment assembly refs must be unique",
    ):
        run_recommendation(
            _tool("tool:documented"),
            [_tether()],
            [_anchor()],
            evidence_bound_tool_attachment_assemblies=[
                _evidence_assembly(),
                duplicate,
            ],
            connection_contexts=[_documented_connection_context()],
        )
