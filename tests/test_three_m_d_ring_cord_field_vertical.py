from tetherlens_ingest.adapters import GRIPPSAdapter, MilwaukeeAdapter, ThreeMAdapter
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
THREE_M_URL = "https://www.3m.com/3M/en_US/p/d/v100323824/"
THREE_M_MANUAL = (
    "https://multimedia.3m.com/mws/media/1300990O/"
    "ifu-5903828-python-d-ring-cord-a3-a3-size-instructions-manual.pdf"
)
GRIPPS_TETHER_URL = "https://gripps.com/products/webbing-extra-heavy-duty-dual-action-tether"


def _artifact(
    body: str,
    *,
    url: str,
    source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=source_type,
        content_type=(
            "application/pdf"
            if source_type == SourceType.MANUFACTURER_DOCUMENT
            else "text/html"
        ),
        body=body,
    )


def _milwaukee_profile() -> OperationalToolProfile:
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.TOOL,
        name="14L Aluminum Pipe Wrench with POWERLENGTH Handle",
        sku="48-22-7215",
        url=MILWAUKEE_URL,
    )
    claims = MilwaukeeAdapter().extract(
        identity,
        [
            _artifact(
                "<h1>48-22-7215 14L Aluminum Pipe Wrench with POWERLENGTH Handle</h1>"
                "<p>Tether-ready lanyard hole</p>",
                url=MILWAUKEE_URL,
            )
        ],
    )
    features = resolve_tool_interface_features(claims)
    assert len(features) == 1

    return OperationalToolProfile(
        profile_ref="Milwaukee:48-22-7215:catalogue",
        display_name="48-22-7215 14L Aluminum Pipe Wrench",
        tool=ResolvedToolCandidate(
            tool_ref="Milwaukee:48-22-7215",
            object_mass_kg=mass_to_kg(2.85, "lb"),
            features=features,
        ),
    )


def _three_m_attachment() -> ToolAttachmentAssemblyOption:
    identity = ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA D-Ring Attachment with Cord",
        sku="1500009",
        url=THREE_M_URL,
    )
    claims = ThreeMAdapter().extract(
        identity,
        [
            _artifact(
                "<html><body>"
                "<h1>3M DBI-SALA D-Ring Attachment with Cord 1500009, 10 EA/PACK</h1>"
                "<div>3M Product Number 1500009</div>"
                "</body></html>",
                url=THREE_M_URL,
            ),
            _artifact(
                "Installation and Use Instructions for Python Safety D-Ring Cord Attachment. "
                "Simply pass the loop end of a D-Ring Cord through a pre-drilled hole or closed "
                "handle to create an instant attachment point. On tools weighing up to 5 lbs "
                "(2.3 kg). Python Safety attachment points require the use of an appropriate "
                "Python Safety Lanyard, Tether or Retractor for safe connection. "
                "Pass the Ring side of the D-Ring Cord through the loop of the Cord. "
                "Pull tightly to cinch and create a secure connection. "
                "1500009 Load Rating 5lbs (2.3kg).",
                url=THREE_M_MANUAL,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
            ),
        ],
    )

    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    method = resolve_tool_attachment_installation_method(
        claims,
        source_product_ref="3M:1500009",
    )
    assert method is not None
    capacity = next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )

    return ToolAttachmentAssemblyOption(
        assembly_ref="3M:1500009:assembly",
        components=[
            CandidateComponentOption(
                component_ref="3M:1500009:component",
                source_product_ref="3M:1500009",
                rated_capacity_kg=capacity,
                product_constraints=resolve_product_constraints(
                    claims,
                    source_product_ref="3M:1500009",
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
                display_name=(
                    "Milwaukee 48-22-7215 14L Aluminum Pipe Wrench "
                    "with POWERLENGTH Handle"
                ),
                operational_profiles=[profile],
            )
        ],
        tethers=[_gripps_tether()],
        anchor_paths=[_nlg_anchor()],
        tool_attachment_assemblies=[_three_m_attachment()],
    )


def test_3m_d_ring_cord_completes_mixed_manufacturer_worker_recommendation() -> None:
    result = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="Milwaukee:48-22-7215"),
        _catalogue(),
    )

    assert result.state == FieldRecommendationState.SELECTED
    assert result.recommendation_run is not None
    assert len(result.recommendation_run.generated_candidates) == 1

    summary = result.recommendation
    assert summary is not None
    assert summary.operational_profile_ref == "Milwaukee:48-22-7215:catalogue"
    assert summary.operational_mass_kg == mass_to_kg(2.85, "lb")
    assert summary.path_selection.installation_feature_id == "tether_ready_opening"
    assert summary.path_selection.attachment_assembly_ref == "3M:1500009:assembly"
    assert summary.path_selection.tether_ref == "GRIPPS:H01079"
    assert summary.path_selection.anchor_path_ref == "NLG:101366:installed-belt-loop"

    method = summary.path_selection.attachment_installation_method
    assert method is not None
    assert method.source_product_ref == "3M:1500009"
    assert method.attachment_method_code == "cinch"
    assert method.source_urls == [THREE_M_MANUAL]

    assert summary.evaluation.recommendation_state == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    assert summary.pending_verification_checks
    assert all(
        check.check_type == CandidateCheckType.CONNECTION_COMPATIBILITY
        for check in summary.pending_verification_checks
    )

    # 3M's family-level prescription is not converted into a technical mixed-brand
    # exclusion. The ordinary generator therefore evaluates this route on neutral
    # topology/capacity facts and leaves unproven connector engagement as verification.
    assert {
        component.source_product_ref
        for component in result.recommendation_run.selection.selected.generated_candidate.configuration.components
    } == {
        "3M:1500009",
        "GRIPPS:H01079",
        "NLG:101366",
    }
