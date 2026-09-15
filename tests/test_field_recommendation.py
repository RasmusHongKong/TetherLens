import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.field_recommendation import (
    FieldInputRequirementKind,
    FieldReadinessIssueCode,
    FieldRecommendationCatalogue,
    FieldRecommendationState,
    FieldToolCatalogueEntry,
    FieldToolObservation,
    FieldToolResolutionSource,
    OperationalToolProfile,
    run_field_recommendation,
)
from tetherlens_ingest.recommendation import RecommendationState


def direct_ring(label: str = "tool") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=f"{label}:ring",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="ring",
    )


def container_ring() -> ConnectionInterface:
    return ConnectionInterface(
        interface_id="container:ring",
        role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
        interface_type="ring",
    )


def resolved_tool(tool_ref: str = "tool:drill", *, mass_kg: float | None = 2.0):
    return ResolvedToolCandidate(
        tool_ref=tool_ref,
        object_mass_kg=mass_kg,
        direct_interfaces=[direct_ring(tool_ref)],
    )


def profile(
    profile_ref: str,
    *,
    tool_ref: str = "tool:drill",
    mass_kg: float | None = 2.0,
    configuration_refs: list[str] | None = None,
) -> OperationalToolProfile:
    return OperationalToolProfile(
        profile_ref=profile_ref,
        display_name=profile_ref,
        tool=resolved_tool(tool_ref, mass_kg=mass_kg),
        configuration_product_refs=configuration_refs or [],
    )


def tool_entry(*profiles: OperationalToolProfile) -> FieldToolCatalogueEntry:
    return FieldToolCatalogueEntry(
        tool_ref="tool:drill",
        display_name="Example cordless drill",
        operational_profiles=list(profiles),
    )


def tether_option(label: str, *, capacity_kg: float = 5.0) -> TetherOption:
    tether_ref = f"product:tether-{label}"
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"component:tether-{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=capacity_kg,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id=f"endpoint:{label}:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id=f"endpoint:{label}:anchor",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec_ref,
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


def anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path-1",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor-1",
                source_product_ref="product:anchor-1",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[container_ring()],
    )


def catalogue(
    *profiles: OperationalToolProfile,
    tethers: list[TetherOption] | None = None,
) -> FieldRecommendationCatalogue:
    return FieldRecommendationCatalogue(
        tools=[tool_entry(*profiles)],
        tethers=tethers if tethers is not None else [tether_option("primary")],
        anchor_paths=[anchor_path()],
    )


def test_recognition_candidates_require_explicit_tool_confirmation_before_run():
    result = run_field_recommendation(
        FieldToolObservation(candidate_tool_refs=["tool:drill"]),
        catalogue(profile("profile:base")),
    )

    assert result.state == FieldRecommendationState.NEEDS_INPUT
    assert result.recommendation_run is None
    assert result.recommendation is None
    assert [requirement.kind for requirement in result.tool_resolution.requirements] == [
        FieldInputRequirementKind.TOOL_CONFIRMATION
    ]
    assert result.tool_resolution.requirements[0].options[0].ref == "tool:drill"


def test_multiple_operational_profiles_require_targeted_profile_selection():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(
            profile(
                "profile:battery-small",
                mass_kg=2.0,
                configuration_refs=["battery:small"],
            ),
            profile(
                "profile:battery-large",
                mass_kg=3.0,
                configuration_refs=["battery:large"],
            ),
        ),
    )

    assert result.state == FieldRecommendationState.NEEDS_INPUT
    requirement = result.tool_resolution.requirements[0]
    assert requirement.kind == FieldInputRequirementKind.OPERATIONAL_PROFILE_SELECTION
    assert [option.ref for option in requirement.options] == [
        "profile:battery-small",
        "profile:battery-large",
    ]
    assert result.recommendation_run is None


def test_selected_operational_profile_drives_load_reasoning_without_bare_tool_fallback():
    result = run_field_recommendation(
        FieldToolObservation(
            confirmed_tool_ref="tool:drill",
            selected_operational_profile_ref="profile:battery-large",
        ),
        catalogue(
            profile(
                "profile:battery-small",
                mass_kg=2.0,
                configuration_refs=["battery:small"],
            ),
            profile(
                "profile:battery-large",
                mass_kg=3.0,
                configuration_refs=["battery:large"],
            ),
            tethers=[tether_option("too-light", capacity_kg=2.5)],
        ),
    )

    assert result.state == FieldRecommendationState.NO_SUITABLE_RECOMMENDATION
    assert result.recommendation_run is not None
    assert result.recommendation_run.tool.object_mass_kg == 3.0
    assert {
        generated.configuration.object_mass_kg
        for generated in result.recommendation_run.generated_candidates
    } == {3.0}
    assert all(
        evaluation.recommendation_state is None
        for evaluation in result.recommendation_run.evaluations
    )


def test_single_ready_profile_runs_complete_pipeline_and_builds_structured_field_summary():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(
            profile(
                "profile:battery-small",
                mass_kg=2.0,
                configuration_refs=["battery:small"],
            ),
            tethers=[
                tether_option("blocked", capacity_kg=1.0),
                tether_option("viable", capacity_kg=5.0),
            ],
        ),
    )

    assert result.state == FieldRecommendationState.SELECTED
    assert result.recommendation_run is not None
    assert result.tool_resolution.resolved is not None
    assert (
        result.recommendation_run.tool
        == result.tool_resolution.resolved.operational_profile.tool
    )
    assert len(result.recommendation_run.generated_candidates) == 2
    assert len(result.recommendation_run.evaluations) == 2

    summary = result.recommendation
    assert summary is not None
    assert summary.operational_profile_ref == "profile:battery-small"
    assert summary.operational_mass_kg == 2.0
    assert summary.configuration_product_refs == ["battery:small"]
    assert summary.path_selection.tether_ref == "product:tether-viable"
    assert (
        summary.evaluation.recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )
    assert [check.check_id for check in summary.pending_verification_checks] == (
        summary.evaluation.pending_verification_connection_ids
    )
    assert summary.pending_action_checks == []


def test_deserialized_selected_result_rejects_profile_mass_that_differs_from_run_tool():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(profile("profile:base")),
    )
    payload = result.model_dump(mode="python")
    payload["tool_resolution"]["resolved"]["operational_profile"]["tool"][
        "object_mass_kg"
    ] = 4.0
    payload["recommendation"]["operational_mass_kg"] = 4.0

    with pytest.raises(ValueError, match="run Tool must match"):
        type(result).model_validate(payload)


def test_missing_operational_mass_fails_before_candidate_generation():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(profile("profile:mass-missing", mass_kg=None)),
    )

    assert result.state == FieldRecommendationState.NOT_READY
    assert result.recommendation_run is None
    assert result.recommendation is None
    assert result.tool_resolution.issues[0].code == (
        FieldReadinessIssueCode.OPERATIONAL_MASS_NOT_ESTABLISHED
    )


def test_session_local_generic_profile_is_explicit_and_does_not_require_catalogue_identity():
    generic = profile(
        "session-profile:measured",
        tool_ref="session-tool:unlisted",
        mass_kg=1.5,
    )
    result = run_field_recommendation(
        FieldToolObservation(generic_profile=generic),
        FieldRecommendationCatalogue(
            tools=[],
            tethers=[tether_option("generic", capacity_kg=5.0)],
            anchor_paths=[anchor_path()],
        ),
    )

    assert result.state == FieldRecommendationState.SELECTED
    assert result.tool_resolution.resolved is not None
    assert (
        result.tool_resolution.resolved.source
        == FieldToolResolutionSource.SESSION_LOCAL_GENERIC
    )
    assert result.recommendation is not None
    assert result.recommendation.path_selection.tool_ref == "session-tool:unlisted"


def test_empty_tether_set_remains_no_generated_candidates_not_no_suitable():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(profile("profile:base"), tethers=[]),
    )

    assert result.state == FieldRecommendationState.NO_GENERATED_CANDIDATES
    assert result.recommendation_run is not None
    assert result.recommendation_run.generated_candidates == []
    assert result.recommendation is None


def test_deserialized_empty_run_rejects_profile_tool_that_differs_from_retained_run_tool():
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="tool:drill"),
        catalogue(profile("profile:base"), tethers=[]),
    )
    payload = result.model_dump(mode="python")
    payload["tool_resolution"]["resolved"]["operational_profile"]["tool"][
        "object_mass_kg"
    ] = 4.0

    with pytest.raises(ValueError, match="run Tool must match"):
        type(result).model_validate(payload)
