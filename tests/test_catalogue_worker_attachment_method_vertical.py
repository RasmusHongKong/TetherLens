from tetherlens_ingest.adapters import GRIPPSAdapter, MilwaukeeAdapter, NLGAdapter
from tetherlens_ingest.attachment_method import resolve_tool_attachment_installation_method
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from tetherlens_ingest.connection import ConnectionInterface, ConnectionInterfaceRole
from tetherlens_ingest.constraints import resolve_product_constraints
from tetherlens_ingest.field_recommendation import (
    FieldInputRequirementKind,
    FieldRecommendationCatalogue,
    FieldRecommendationState,
    FieldToolCatalogueEntry,
    FieldToolObservation,
    OperationalToolProfile,
    run_field_recommendation,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.normalize import mass_to_kg
from tetherlens_ingest.recommendation import CandidateCheckType, RecommendationState
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
    resolve_connector_specs,
    resolve_tool_interface_features,
)


MILWAUKEE_URL = (
    "https://www.milwaukeetool.com/products/details/"
    "14l-aluminum-pipe-wrench-with-powerlength-handle/48-22-7215"
)
NLG_ATTACHMENT_URL = "https://neverletgo.com/products/360-d-ring-loop-tool-tether"
NLG_GUIDE_URL = "https://neverletgo.com/pages/tool-tether-guide"
GRIPPS_TETHER_URL = "https://gripps.com/products/webbing-extra-heavy-duty-dual-action-tether"
NLG_ANCHOR_URL = "https://neverletgo.com/products/belt-loop-anchor"


def _artifact(body: str, *, url: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _milwaukee_profile() -> OperationalToolProfile:
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.TOOL,
        name='14L Aluminum Pipe Wrench with POWERLENGTH Handle',
        sku="48-22-7215",
        url=MILWAUKEE_URL,
    )
    claims = MilwaukeeAdapter().extract(
        identity,
        [
            _artifact(
                """
                <h1>48-22-7215 14L Aluminum Pipe Wrench with POWERLENGTH Handle</h1>
                <p>Tether-ready lanyard hole</p>
                """,
                url=MILWAUKEE_URL,
            )
        ],
    )
    features = resolve_tool_interface_features(claims)
    assert len(features) == 1

    # The normalized catalogue field is backed by Milwaukee's current product
    # specification (Weight: 2.85 lb). This demand-side vertical starts from accepted
    # catalogue facts; it does not broaden Milwaukee mass extraction in this slice.
    operational_mass_kg = mass_to_kg(2.85, "lb")
    return OperationalToolProfile(
        profile_ref="Milwaukee:48-22-7215:catalogue",
        display_name='48-22-7215 14L Aluminum Pipe Wrench',
        tool=ResolvedToolCandidate(
            tool_ref="Milwaukee:48-22-7215",
            object_mass_kg=operational_mass_kg,
            features=features,
        ),
    )


def _nlg_attachment() -> ToolAttachmentAssemblyOption:
    identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="360 D Ring Loop Tool Tether",
        sku="101363",
        url=NLG_ATTACHMENT_URL,
    )
    claims = NLGAdapter().extract(
        identity,
        [
            _artifact(
                "The 360 D Ring Loop Tool Tether is a quick and easy way to create a "
                "secure tether point on small tools with a captive hole. NLG's 360 D Ring "
                "Loop Tool Tether can create a tether point on any tool with a captive hole "
                "or handle and cinch it around the tool itself. Max Load: 3 KG / 6.6 LBS. "
                "The D Ring creates a secure tether point to attach a tool lanyard.",
                url=NLG_ATTACHMENT_URL,
            ),
            _artifact(
                "D Ring Loop Tool Tether. Pass the loop end through the captive handle or "
                "hole of the tool. Lift the D Ring end over the tool and pass through the "
                "open loop to create a cinch. Pull tightly to secure. Test the tether point "
                "before putting the tool into use.",
                url=NLG_GUIDE_URL,
            ),
        ],
    )
    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    method = resolve_tool_attachment_installation_method(
        claims,
        source_product_ref="NLG:101363",
    )
    assert method is not None
    capacity = next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )
    return ToolAttachmentAssemblyOption(
        assembly_ref="NLG:101363:assembly",
        components=[
            CandidateComponentOption(
                component_ref="NLG:101363:component",
                source_product_ref="NLG:101363",
                rated_capacity_kg=capacity,
                product_constraints=resolve_product_constraints(
                    claims,
                    source_product_ref="NLG:101363",
                ),
            )
        ],
        eligibility=eligibility,
        provided_interfaces=interfaces,
        installation_method=method,
    )


def _gripps_tether() -> TetherOption:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Tether Heavy-Duty Dual-Action Carabiner",
        sku="H01079",
        url=GRIPPS_TETHER_URL,
    )
    claims = GRIPPSAdapter().extract(
        identity,
        [
            _artifact(
                "The GRIPPS Webbing Tether Heavy-Duty Dual-Action features dual-action "
                "carabiners at both ends. Max Load: 36.3 kg | 80 lb. The H01079 has a "
                "dedicated Anchor end large carabiner and a dedicated Tool end, the small "
                "carabiner.",
                url=GRIPPS_TETHER_URL,
            )
        ],
    )
    endpoints = resolve_connection_interfaces(claims)
    connector_specs = resolve_connector_specs(claims)
    assert len(endpoints) == 2
    assert {spec.opening_action_count for spec in connector_specs.values()} == {2}
    capacity = next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )
    return TetherOption(
        tether_ref="GRIPPS:H01079",
        component=CandidateComponentOption(
            component_ref="GRIPPS:H01079:component",
            source_product_ref="GRIPPS:H01079",
            rated_capacity_kg=capacity,
        ),
        endpoints=endpoints,
        connector_specs=connector_specs,
    )


def _nlg_anchor() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="NLG:101366:installed-belt-loop",
        components=[
            CandidateComponentOption(
                component_ref="NLG:101366:component",
                source_product_ref="NLG:101366",
                rated_capacity_kg=3.0,
            )
        ],
        target_interfaces=[
            ConnectionInterface(
                interface_id="NLG:101366:welded-d-ring",
                role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
                interface_type="ring",
                attributes={"ring_form": "d_ring"},
            )
        ],
    )


def _catalogue() -> FieldRecommendationCatalogue:
    profile = _milwaukee_profile()
    return FieldRecommendationCatalogue(
        tools=[
            FieldToolCatalogueEntry(
                tool_ref="Milwaukee:48-22-7215",
                display_name='Milwaukee 48-22-7215 14L Aluminum Pipe Wrench',
                operational_profiles=[profile],
            )
        ],
        tethers=[_gripps_tether()],
        anchor_paths=[_nlg_anchor()],
        tool_attachment_assemblies=[_nlg_attachment()],
    )


def test_real_catalogue_worker_path_retains_cinch_method_after_explicit_tool_confirmation() -> None:
    catalogue = _catalogue()

    recognition = run_field_recommendation(
        FieldToolObservation(candidate_tool_refs=["Milwaukee:48-22-7215"]),
        catalogue,
    )
    assert recognition.state == FieldRecommendationState.NEEDS_INPUT
    assert [requirement.kind for requirement in recognition.tool_resolution.requirements] == [
        FieldInputRequirementKind.TOOL_CONFIRMATION
    ]

    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="Milwaukee:48-22-7215"),
        catalogue,
    )

    assert result.state == FieldRecommendationState.SELECTED
    assert result.recommendation_run is not None
    assert len(result.recommendation_run.generated_candidates) == 1

    summary = result.recommendation
    assert summary is not None
    assert summary.operational_profile_ref == "Milwaukee:48-22-7215:catalogue"
    assert summary.operational_mass_kg == mass_to_kg(2.85, "lb")
    assert summary.path_selection.installation_feature_id == "tether_ready_opening"
    assert summary.path_selection.attachment_assembly_ref == "NLG:101363:assembly"
    assert summary.path_selection.tether_ref == "GRIPPS:H01079"
    assert summary.path_selection.anchor_path_ref == "NLG:101366:installed-belt-loop"

    method = summary.path_selection.attachment_installation_method
    assert method is not None
    assert method.source_product_ref == "NLG:101363"
    assert method.attachment_method_code == "cinch"
    assert method.source_urls == [NLG_ATTACHMENT_URL, NLG_GUIDE_URL]

    assert summary.evaluation.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert len(summary.pending_verification_checks) == 2
    assert all(
        check.check_type == CandidateCheckType.CONNECTION_COMPATIBILITY
        for check in summary.pending_verification_checks
    )
    assert any(
        check.check_type == CandidateCheckType.PRODUCT_CONSTRAINT
        for check in summary.pending_action_checks
    )

    # The field summary is a projection of the exact retained generation-time path, not
    # a reconstruction that could relabel how the attachment was installed.
    selected_id = result.recommendation_run.selection.selected_candidate_id
    generated = next(
        candidate
        for candidate in result.recommendation_run.generated_candidates
        if candidate.configuration.candidate_id == selected_id
    )
    assert generated.selection == summary.path_selection
    assert generated.selection.attachment_installation_method == method
