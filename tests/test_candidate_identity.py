from tetherlens_ingest.candidate_generation import (
    CandidateComponentRole,
    CandidatePathSelection,
    CandidateSelectedComponent,
    _candidate_id,
)


def selection(component_ref: str) -> CandidatePathSelection:
    return CandidatePathSelection(
        tool_ref="tool:1",
        tether_ref="tether:1",
        anchor_path_ref="anchor:path-1",
        tool_endpoint_id="endpoint:tool",
        tool_target_interface_id="target:tool",
        anchor_endpoint_id="endpoint:anchor",
        anchor_target_interface_id="target:anchor",
        components=[
            CandidateSelectedComponent(
                component_ref=component_ref,
                source_product_ref="product:attachment-1",
                role=CandidateComponentRole.TOOL_ATTACHMENT,
            )
        ],
    )


def test_candidate_identity_changes_when_selected_component_instance_changes():
    first = selection("component:attachment-a")
    second = selection("component:attachment-b")

    assert _candidate_id(first) != _candidate_id(second)
    assert '"component_refs":["component:attachment-a"]' in _candidate_id(first)
