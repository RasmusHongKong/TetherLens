import pytest

from tetherlens_ingest.attachment_method import (
    AttachmentMethodResolutionError,
    ToolAttachmentInstallationMethod,
    resolve_tool_attachment_installation_method,
)
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.compatibility import CaptiveState, FeatureKind, ToolInterfaceFeature
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    TetherSide,
)
from tetherlens_ingest.models import CandidateClaim
from tetherlens_ingest.resolution import resolve_attachment_eligibility


def _method_claim(
    value: str | int | float | bool,
    url: str,
    *,
    supporting: list[str] | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        property_key="attachment_method_code",
        value=value,
        source_url=url,
        supporting_source_urls=supporting or [],
        extractor="test",
    )


def _eligibility():
    resolved = resolve_attachment_eligibility(
        [
            CandidateClaim(
                property_key="attachment_selection_class",
                value="captive_handle_attachment",
                source_url="https://manufacturer.test/attachment",
                extractor="test",
            )
        ]
    )
    assert resolved is not None
    return resolved


def _assembly(method: ToolAttachmentInstallationMethod | None) -> ToolAttachmentAssemblyOption:
    return ToolAttachmentAssemblyOption(
        assembly_ref="attachment:assembly",
        components=[
            CandidateComponentOption(
                component_ref="attachment:component",
                source_product_ref="NLG:101363",
                rated_capacity_kg=3.0,
            )
        ],
        eligibility=_eligibility(),
        provided_interfaces=[
            ConnectionInterface(
                interface_id="attachment:d-ring",
                role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
                interface_type="ring",
                attributes={"ring_form": "d_ring"},
            )
        ],
        installation_method=method,
    )


def _tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="tool:example",
        object_mass_kg=2.0,
        features=[
            ToolInterfaceFeature(
                feature_id="tool:captive-handle",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.CAPTIVE,
            )
        ],
    )


def _tether() -> TetherOption:
    return TetherOption(
        tether_ref="tether:example",
        component=CandidateComponentOption(
            component_ref="tether:component",
            source_product_ref="tether:example",
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="tether:tool-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
            ),
            ConnectionInterface(
                interface_id="tether:anchor-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
            ),
        ],
    )


def _anchor() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:example",
        target_interfaces=[
            ConnectionInterface(
                interface_id="anchor:ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )


def test_method_resolution_retains_canonical_code_and_all_accepted_source_urls() -> None:
    resolved = resolve_tool_attachment_installation_method(
        [
            _method_claim(
                "cinch",
                "https://manufacturer.test/product",
                supporting=["https://manufacturer.test/instructions"],
            ),
            _method_claim("cinch", "https://manufacturer.test/datasheet"),
        ],
        source_product_ref="NLG:101363",
    )

    assert resolved == ToolAttachmentInstallationMethod(
        source_product_ref="NLG:101363",
        attachment_method_code="cinch",
        source_urls=[
            "https://manufacturer.test/datasheet",
            "https://manufacturer.test/instructions",
            "https://manufacturer.test/product",
        ],
    )


def test_conflicting_accepted_method_codes_fail_closed() -> None:
    with pytest.raises(AttachmentMethodResolutionError, match="conflicting accepted"):
        resolve_tool_attachment_installation_method(
            [
                _method_claim("cinch", "https://manufacturer.test/product"),
                _method_claim("wrap", "https://manufacturer.test/instructions"),
            ],
            source_product_ref="NLG:101363",
        )


@pytest.mark.parametrize("value", [1, 1.0, True])
def test_non_string_accepted_method_codes_fail_closed(value: int | float | bool) -> None:
    with pytest.raises(AttachmentMethodResolutionError, match="must be a string"):
        resolve_tool_attachment_installation_method(
            [_method_claim(value, "https://manufacturer.test/product")],
            source_product_ref="NLG:101363",
        )


def test_non_string_method_does_not_collapse_with_same_textual_string() -> None:
    with pytest.raises(AttachmentMethodResolutionError, match="must be a string"):
        resolve_tool_attachment_installation_method(
            [
                _method_claim(1, "https://manufacturer.test/product"),
                _method_claim("1", "https://manufacturer.test/instructions"),
            ],
            source_product_ref="NLG:101363",
        )


def test_empty_string_method_code_fails_closed() -> None:
    with pytest.raises(AttachmentMethodResolutionError, match="must be non-empty"):
        resolve_tool_attachment_installation_method(
            [_method_claim("   ", "https://manufacturer.test/product")],
            source_product_ref="NLG:101363",
        )


def test_assembly_rejects_method_provenance_owned_by_unselected_product() -> None:
    with pytest.raises(ValueError, match="must belong to a selected assembly component"):
        _assembly(
            ToolAttachmentInstallationMethod(
                source_product_ref="NLG:other",
                attachment_method_code="cinch",
                source_urls=["https://manufacturer.test/product"],
            )
        )


def test_generation_retains_method_without_changing_candidate_identity_or_eligibility() -> None:
    method = ToolAttachmentInstallationMethod(
        source_product_ref="NLG:101363",
        attachment_method_code="cinch",
        source_urls=["https://manufacturer.test/product"],
    )
    with_method = generate_candidate_configurations(
        _tool(),
        [_tether()],
        [_anchor()],
        tool_attachment_assemblies=[_assembly(method)],
    )
    without_method = generate_candidate_configurations(
        _tool(),
        [_tether()],
        [_anchor()],
        tool_attachment_assemblies=[_assembly(None)],
    )

    assert len(with_method) == len(without_method) == 1
    selected = with_method[0]
    baseline = without_method[0]

    assert selected.selection.attachment_installation_method == method
    assert selected.selection.installation_feature_id == "tool:captive-handle"
    assert selected.configuration.attachment_eligibility == baseline.configuration.attachment_eligibility
    assert selected.configuration.candidate_id == baseline.configuration.candidate_id
