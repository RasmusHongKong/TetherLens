import pytest

from tetherlens_ingest.adapters import HiltiAdapter
from tetherlens_ingest.field_recommendation import (
    FieldInputRequirementKind,
    FieldReadinessIssueCode,
    FieldRecommendationCatalogue,
    FieldToolCatalogueEntry,
    FieldToolObservation,
    FieldToolResolutionState,
    resolve_field_tool,
)
from tetherlens_ingest.field_tool_search import candidate_tool_refs_from_text_search
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.operational_profile import (
    OperationalProfileDescriptor,
    OperationalProfileResolutionError,
    resolve_operational_tool_profiles,
)


TOOL_URL = (
    "https://www.hilti.com/c/CLS_POWER_TOOLS_7125/"
    "CLS_DRILL_DRIVERS_SCREW_DRIVERS__7125/r13275669"
)
BATTERY_55_URL = (
    "https://www.hilti.com/c/CLS_POWER_TOOLS_7125/"
    "CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250264"
)
BATTERY_85_URL = (
    "https://www.hilti.com/c/CLS_POWER_TOOLS_7125/"
    "CLS_BATT_CHARGERS_POWER_STATIONS_7125/r13250303"
)


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL,
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        url=TOOL_URL,
        manufacturer_ids={"technical_family": "r13275669"},
    )


def _artifact(
    body: str,
    *,
    url: str,
    role: str | None = None,
    battery_model: str | None = None,
) -> SourceArtifact:
    metadata = {}
    if role is not None:
        metadata["role"] = role
    if battery_model is not None:
        metadata["battery_model"] = battery_model
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
        metadata=metadata,
    )


def _hilti_claims() -> list[CandidateClaim]:
    return HiltiAdapter().extract(
        _identity(),
        [
            _artifact(
                "<h1>SF 4-22 Cordless drill driver</h1>"
                "<div>#2253847</div><div>Tool body weight: 2.9 lb</div>",
                url=TOOL_URL,
            ),
            _artifact(
                "<h1>B 22-55 Nuron battery</h1><div>Weight: 1.21 lb</div>",
                url=BATTERY_55_URL,
                role="battery",
                battery_model="B 22-55",
            ),
            _artifact(
                "<h1>B 22-85 Nuron battery</h1><div>Weight: 1.67 lb</div>",
                url=BATTERY_85_URL,
                role="battery",
                battery_model="B 22-85",
            ),
        ],
    )


def _descriptors(*, include_unready: bool = False) -> list[OperationalProfileDescriptor]:
    descriptors = [
        OperationalProfileDescriptor(
            profile_ref="2253847+B 22-55",
            display_name="SF 4-22 with B 22-55 battery",
            configuration_product_refs=["Hilti:B 22-55"],
        ),
        OperationalProfileDescriptor(
            profile_ref="2253847+B 22-85",
            display_name="SF 4-22 with B 22-85 battery",
            configuration_product_refs=["Hilti:B 22-85"],
        ),
    ]
    if include_unready:
        descriptors.append(
            OperationalProfileDescriptor(
                profile_ref="2253847+B 22-999",
                display_name="SF 4-22 with B 22-999 battery",
                configuration_product_refs=["Hilti:B 22-999"],
            )
        )
    return descriptors


def test_real_hilti_profiles_flow_from_accepted_mass_claims_to_field_profile_selection():
    profiles = resolve_operational_tool_profiles(
        _hilti_claims(),
        tool_ref="Hilti:2253847",
        descriptors=_descriptors(),
    )

    assert [profile.profile_ref for profile in profiles] == [
        "2253847+B 22-55",
        "2253847+B 22-85",
    ]
    assert [profile.tool.object_mass_kg for profile in profiles] == [
        1.864265,
        2.072917,
    ]
    assert [profile.configuration_product_refs for profile in profiles] == [
        ["Hilti:B 22-55"],
        ["Hilti:B 22-85"],
    ]

    catalogue = FieldRecommendationCatalogue(
        tools=[
            FieldToolCatalogueEntry(
                tool_ref="Hilti:2253847",
                display_name="Hilti 2253847 SF 4-22 Cordless drill driver",
                operational_profiles=profiles,
            )
        ]
    )
    candidates = candidate_tool_refs_from_text_search("Hilti 2253847", catalogue)
    assert candidates == ["Hilti:2253847"]

    confirmation = resolve_field_tool(
        FieldToolObservation(candidate_tool_refs=candidates),
        catalogue.tools,
    )
    assert confirmation.state == FieldToolResolutionState.NEEDS_INPUT
    assert confirmation.requirements[0].kind == FieldInputRequirementKind.TOOL_CONFIRMATION

    profile_choice = resolve_field_tool(
        FieldToolObservation(confirmed_tool_ref="Hilti:2253847"),
        catalogue.tools,
    )
    assert profile_choice.state == FieldToolResolutionState.NEEDS_INPUT
    assert profile_choice.requirements[0].kind == (
        FieldInputRequirementKind.OPERATIONAL_PROFILE_SELECTION
    )
    assert [option.ref for option in profile_choice.requirements[0].options] == [
        "2253847+B 22-55",
        "2253847+B 22-85",
    ]

    resolved = resolve_field_tool(
        FieldToolObservation(
            confirmed_tool_ref="Hilti:2253847",
            selected_operational_profile_ref="2253847+B 22-85",
        ),
        catalogue.tools,
    )
    assert resolved.state == FieldToolResolutionState.RESOLVED
    assert resolved.resolved is not None
    assert resolved.resolved.operational_profile.tool.object_mass_kg == 2.072917
    assert resolved.resolved.operational_profile.configuration_product_refs == [
        "Hilti:B 22-85"
    ]


def test_known_configuration_without_operational_mass_remains_visible_and_fails_closed_when_selected():
    profiles = resolve_operational_tool_profiles(
        _hilti_claims(),
        tool_ref="Hilti:2253847",
        descriptors=_descriptors(include_unready=True),
    )
    assert profiles[-1].profile_ref == "2253847+B 22-999"
    assert profiles[-1].tool.object_mass_kg is None

    entry = FieldToolCatalogueEntry(
        tool_ref="Hilti:2253847",
        display_name="Hilti 2253847 SF 4-22 Cordless drill driver",
        operational_profiles=profiles,
    )
    choice = resolve_field_tool(
        FieldToolObservation(confirmed_tool_ref="Hilti:2253847"),
        [entry],
    )
    assert [option.ref for option in choice.requirements[0].options] == [
        "2253847+B 22-55",
        "2253847+B 22-85",
        "2253847+B 22-999",
    ]

    unresolved = resolve_field_tool(
        FieldToolObservation(
            confirmed_tool_ref="Hilti:2253847",
            selected_operational_profile_ref="2253847+B 22-999",
        ),
        [entry],
    )
    assert unresolved.state == FieldToolResolutionState.NOT_READY
    assert unresolved.issues[0].code == (
        FieldReadinessIssueCode.OPERATIONAL_MASS_NOT_ESTABLISHED
    )
    assert unresolved.issues[0].subject_ref == "2253847+B 22-999"


def test_operational_mass_claim_without_explicit_configuration_descriptor_is_rejected():
    claim = CandidateClaim(
        subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
        subject_ref="profile:unbound",
        property_key="operational_mass_kg",
        value=2.0,
        unit="kg",
        source_url="https://example.test/profile",
        extractor="test",
    )

    with pytest.raises(
        OperationalProfileResolutionError,
        match="no normalized configuration descriptor",
    ):
        resolve_operational_tool_profiles(
            [claim],
            tool_ref="tool:1",
            descriptors=[],
        )


def test_conflicting_accepted_operational_masses_are_not_prioritized_silently():
    claims = [
        CandidateClaim(
            subject_type=ClaimSubjectType.OPERATIONAL_PROFILE,
            subject_ref="profile:1",
            property_key="operational_mass_kg",
            value=value,
            unit="kg",
            source_url=f"https://example.test/{index}",
            extractor="test",
        )
        for index, value in enumerate((2.0, 2.1), start=1)
    ]

    with pytest.raises(OperationalProfileResolutionError, match="conflicting accepted"):
        resolve_operational_tool_profiles(
            claims,
            tool_ref="tool:1",
            descriptors=[
                OperationalProfileDescriptor(
                    profile_ref="profile:1",
                    display_name="Profile 1",
                    configuration_product_refs=["battery:1"],
                )
            ],
        )
