from tetherlens_ingest.adapters import HiltiAdapter
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    TetherOption,
)
from tetherlens_ingest.compatibility import FeatureKind, FeatureRole
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
)
from tetherlens_ingest.declared_compatibility import (
    connection_contexts_from_compatibility_declarations,
    resolve_connector_interface_compatibility_declarations,
)
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentBasis,
    EndpointAssignmentSemantics,
    TetherEndpointAssignmentDeclaration,
)
from tetherlens_ingest.field_recommendation import (
    FieldInputRequirementKind,
    FieldRecommendationCatalogue,
    FieldRecommendationState,
    FieldToolCatalogueEntry,
    FieldToolObservation,
    run_field_recommendation,
)
from tetherlens_ingest.field_tool_search import candidate_tool_refs_from_text_search
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.operational_profile import (
    OperationalProfileDescriptor,
    resolve_operational_tool_profiles,
)
from tetherlens_ingest.recommendation import RecommendationState
from tetherlens_ingest.resolution import (
    resolve_connection_interfaces,
    resolve_connector_specs,
    resolve_tool_interface_features,
)
from tetherlens_ingest.tool_attachment_installation import (
    EvidenceBoundToolAttachmentAssemblyOption,
    resolve_tool_attachment_installation_bindings,
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
STRAP_URL = "https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2293133"
TETHER_URL = "https://www.hilti.com/c/CLS_HEALTH_SAFETY/CLS_SAFETY_GEAR/2261970"
MANUAL_URL = "https://productdata.hilti.com/APQ_HC_RAW/PUB_SF4_22_000.pdf"


def _tool_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL,
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        url=TOOL_URL,
        manufacturer_ids={"technical_family": "r13275669"},
    )


def _web_artifact(body: str, *, url: str, metadata=None) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
        metadata=metadata or {},
    )


def _tool_claims():
    manual = SourceArtifact(
        url=MANUAL_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            "SF 4-22 (02), SF 4H-22 (02). Fall arrest. "
            "As drop arrester for this product, use only a combination of the Hilti "
            "retaining strap #2293133 and the Hilti tool tether #2261970. "
            "Secure the retaining strap to the installation openings for accessories. "
            "Check that it holds securely. Secure one carabiner of the tool tether to "
            "the retaining strap and secure the second carabiner to a load-bearing "
            "structure. Check that both carabiners hold securely."
        ),
        metadata={"role": "operating_instruction"},
    )
    return HiltiAdapter().extract(
        _tool_identity(),
        [
            _web_artifact(
                "<h1>SF 4-22 Cordless drill driver</h1>"
                "<div>#2253847</div><div>Tool body weight: 2.9 lb</div>",
                url=TOOL_URL,
            ),
            _web_artifact(
                "<h1>B 22-55 Nuron battery</h1><div>Weight: 1.21 lb</div>",
                url=BATTERY_55_URL,
                metadata={"role": "battery", "battery_model": "B 22-55"},
            ),
            _web_artifact(
                "<h1>B 22-85 Nuron battery</h1><div>Weight: 1.67 lb</div>",
                url=BATTERY_85_URL,
                metadata={"role": "battery", "battery_model": "B 22-85"},
            ),
            manual,
        ],
    )


def _descriptors() -> list[OperationalProfileDescriptor]:
    return [
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


def _strap_assembly(tool_claims) -> EvidenceBoundToolAttachmentAssemblyOption:
    identity = ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="Retaining strap 15lb cordl.",
        sku="2293133",
        url=STRAP_URL,
    )
    strap_claims = HiltiAdapter().extract(
        identity,
        [
            _web_artifact(
                "<h1>Retaining strap 15lb cordl.</h1><div>#2293133</div>"
                "<div>1x 15lb (6.8kg) Retaining strap assy</div>"
                "<p>Accessory for connecting compatible power tools to a Hilti tool lanyard</p>",
                url=STRAP_URL,
            )
        ],
    )
    provided_interfaces = resolve_connection_interfaces(strap_claims)
    capacity = next(
        float(claim.value)
        for claim in strap_claims
        if claim.property_key == "rated_capacity_kg"
    )
    bindings = resolve_tool_attachment_installation_bindings(
        tool_claims,
        tool_ref="Hilti:2253847",
        attachment_product_refs={"2293133": "Hilti:2293133"},
    )
    return EvidenceBoundToolAttachmentAssemblyOption(
        assembly_ref="Hilti:2293133:assembly",
        components=[
            CandidateComponentOption(
                component_ref="Hilti:2293133:component",
                source_product_ref="Hilti:2293133",
                rated_capacity_kg=capacity,
            )
        ],
        provided_interfaces=provided_interfaces,
        installation_bindings=bindings,
    )


def _tether() -> TetherOption:
    identity = ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TETHER,
        name="Tool tether 15lbs double carabiner",
        sku="2261970",
        url=TETHER_URL,
    )
    claims = HiltiAdapter().extract(
        identity,
        [
            _web_artifact(
                "<h1>Tool tether 15lbs double carabiner</h1><div>#2261970</div>"
                "<div>Maximum load: 6.8 kg</div>"
                "<p>double carabiner, self-locking carabiner, double-action</p>",
                url=TETHER_URL,
            )
        ],
    )
    endpoints = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    capacity = next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )
    assignment = TetherEndpointAssignmentDeclaration(
        declaration_id="Hilti:2261970:reversible",
        tether_ref="Hilti:2261970",
        endpoint_refs=["connection_point_1", "connection_point_2"],
        semantics=EndpointAssignmentSemantics.REVERSIBLE_TOOL_ANCHOR_PAIR,
        basis=EndpointAssignmentBasis.DERIVED_ENDPOINT_EQUIVALENCE,
        issuer_manufacturer="Hilti",
        scope=(
            "double-carabiner tether endpoints are physically equivalent; the operating "
            "instruction assigns one carabiner to the retaining strap and one to structure"
        ),
        source_urls=[TETHER_URL, MANUAL_URL],
    )
    return TetherOption(
        tether_ref="Hilti:2261970",
        component=CandidateComponentOption(
            component_ref="Hilti:2261970:component",
            source_product_ref="Hilti:2261970",
            rated_capacity_kg=capacity,
        ),
        endpoints=endpoints,
        connector_specs=specs,
        endpoint_assignment_declarations=[assignment],
    )


def _anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="field:load-bearing-structure",
        components=[
            CandidateComponentOption(
                component_ref="field:anchor-component",
                source_product_ref="field:anchor",
                rated_capacity_kg=6.8,
            )
        ],
        target_interfaces=[
            ConnectionInterface(
                interface_id="field:anchor-ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )


def test_selected_hilti_operational_profile_reaches_complete_recommendation_pipeline():
    tool_claims = _tool_claims()
    features = resolve_tool_interface_features(tool_claims)
    assert len(features) == 1
    assert features[0].feature_kind == FeatureKind.OTHER
    assert features[0].feature_role == FeatureRole.ACCESSORY_MOUNT

    profiles = resolve_operational_tool_profiles(
        tool_claims,
        tool_ref="Hilti:2253847",
        descriptors=_descriptors(),
        features=features,
    )
    strap = _strap_assembly(tool_claims)
    tether = _tether()
    declarations = resolve_connector_interface_compatibility_declarations(
        tool_claims,
        product_refs_by_identifier={
            "2261970": tether.component.source_product_ref,
            "2293133": strap.components[0].source_product_ref,
        },
    )
    connection_contexts = connection_contexts_from_compatibility_declarations(
        tether_ref=tether.tether_ref,
        tether_product_ref=tether.component.source_product_ref,
        endpoints=tether.endpoints,
        target_owner_ref=strap.assembly_ref,
        target_product_refs={component.source_product_ref for component in strap.components},
        target_interfaces=strap.provided_interfaces,
        declarations=declarations,
    )

    catalogue = FieldRecommendationCatalogue(
        tools=[
            FieldToolCatalogueEntry(
                tool_ref="Hilti:2253847",
                display_name="Hilti 2253847 SF 4-22 Cordless drill driver",
                operational_profiles=profiles,
            )
        ],
        tethers=[tether],
        anchor_paths=[_anchor_path()],
        evidence_bound_tool_attachment_assemblies=[strap],
    )

    candidates = candidate_tool_refs_from_text_search("Hilti 2253847", catalogue)
    assert candidates == ["Hilti:2253847"]

    confirmation = run_field_recommendation(
        FieldToolObservation(candidate_tool_refs=candidates),
        catalogue,
        connection_contexts=connection_contexts,
    )
    assert confirmation.state == FieldRecommendationState.NEEDS_INPUT
    assert confirmation.tool_resolution.requirements[0].kind == (
        FieldInputRequirementKind.TOOL_CONFIRMATION
    )

    profile_choice = run_field_recommendation(
        FieldToolObservation(confirmed_tool_ref="Hilti:2253847"),
        catalogue,
        connection_contexts=connection_contexts,
    )
    assert profile_choice.state == FieldRecommendationState.NEEDS_INPUT
    assert profile_choice.tool_resolution.requirements[0].kind == (
        FieldInputRequirementKind.OPERATIONAL_PROFILE_SELECTION
    )

    result = run_field_recommendation(
        FieldToolObservation(
            confirmed_tool_ref="Hilti:2253847",
            selected_operational_profile_ref="2253847+B 22-85",
        ),
        catalogue,
        connection_contexts=connection_contexts,
    )

    assert result.state == FieldRecommendationState.SELECTED
    assert result.operational_profile_binding is not None
    assert result.operational_profile_binding.profile_ref == "2253847+B 22-85"
    assert result.operational_profile_binding.configuration_product_refs == [
        "Hilti:B 22-85"
    ]
    assert result.recommendation_run is not None
    assert result.recommendation_run.tool is not None
    assert result.recommendation_run.tool.object_mass_kg == 2.072917

    summary = result.recommendation
    assert summary is not None
    assert summary.operational_mass_kg == 2.072917
    assert summary.configuration_product_refs == ["Hilti:B 22-85"]
    assert summary.path_selection.attachment_assembly_ref == "Hilti:2293133:assembly"
    assert summary.path_selection.installation_feature_id == "accessory_installation_openings"
    assert summary.path_selection.tether_ref == "Hilti:2261970"
    assert summary.attachment_installation_binding is not None
    assert summary.attachment_installation_binding.binding_id == (
        "retaining_strap_accessory_openings"
    )
    assert summary.attachment_installation_binding.tool_ref == "Hilti:2253847"
    assert summary.attachment_installation_binding.source_product_ref == "Hilti:2293133"
    assert summary.evaluation.recommendation_state == (
        RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )

    assert summary.evaluation.connections[0].basis == CompatibilityBasis.MANUFACTURER_DECLARED
    assert summary.evaluation.connections[0].status.value == "compatible"
    assert summary.evaluation.connections[1].basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert summary.evaluation.connections[1].status.value == "requires_verification"
    assert len(summary.pending_verification_checks) == 1

    capacity_checks = [
        check
        for check in summary.evaluation.checks
        if check.check_type.value == "load_capacity"
    ]
    assert len(capacity_checks) == 3
    assert {check.status.value for check in capacity_checks} == {"passed"}
