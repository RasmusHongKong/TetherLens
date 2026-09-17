from tetherlens_ingest.adapters.hilti_tool_attachment import HiltiAdapter
from tetherlens_ingest.compatibility import CaptiveState, FeatureKind, FeatureRole
from tetherlens_ingest.connection import ConnectionInterface, ConnectionInterfaceRole
from tetherlens_ingest.declared_compatibility import (
    connection_contexts_from_compatibility_declarations,
    resolve_connector_interface_compatibility_declarations,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import resolve_tool_interface_features
from tetherlens_ingest.tool_attachment_installation import (
    resolve_tool_attachment_installation_bindings,
)


TOOL_URL = (
    "https://www.hilti.com/c/CLS_POWER_TOOLS_7125/"
    "CLS_DRILL_DRIVERS_SCREW_DRIVERS__7125/r13275669"
)
MANUAL_URL = "https://www.hilti.com/medias/sys_master/documents/example/SF4-22.pdf"


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL,
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        url=TOOL_URL,
        manufacturer_ids={"technical_family": "r13275669"},
    )


def _primary() -> SourceArtifact:
    return SourceArtifact(
        url=TOOL_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>",
    )


def _manual() -> SourceArtifact:
    return SourceArtifact(
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


def _claims():
    return HiltiAdapter().extract(_identity(), [_primary(), _manual()])


def _resolved_connection_declaration():
    declarations = resolve_connector_interface_compatibility_declarations(
        _claims(),
        product_refs_by_identifier={
            "2261970": "Hilti:2261970",
            "2293133": "Hilti:2293133",
        },
    )
    assert len(declarations) == 1
    return declarations[0]


def test_hilti_manual_resolves_conservative_accessory_installation_feature_and_binding():
    claims = _claims()
    features = resolve_tool_interface_features(claims)

    assert len(features) == 1
    feature = features[0]
    assert feature.feature_id == "accessory_installation_openings"
    assert feature.feature_kind == FeatureKind.OTHER
    assert feature.feature_role == FeatureRole.ACCESSORY_MOUNT
    assert feature.captive_state == CaptiveState.UNKNOWN
    assert feature.location_description == "installation openings for accessories"
    assert feature.dimensions_mm == {}

    bindings = resolve_tool_attachment_installation_bindings(
        claims,
        tool_ref="Hilti:2253847",
        attachment_product_refs={"2293133": "Hilti:2293133"},
    )
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.binding_id == "retaining_strap_accessory_openings:2293133"
    assert binding.tool_ref == "Hilti:2253847"
    assert binding.source_product_ref == "Hilti:2293133"
    assert binding.installation_feature_id == feature.feature_id
    assert binding.issuer_manufacturer == "Hilti"
    assert binding.source_urls == [MANUAL_URL]

    # The operating instruction establishes a location/relationship, not geometry.
    assert not any(
        claim.property_key == "feature.captive_state"
        or claim.property_key.startswith("feature.dimension.")
        or (
            claim.property_key == "feature.kind"
            and str(claim.value) in {"through_opening", "ring"}
        )
        for claim in claims
    )


def test_unmapped_attachment_reference_does_not_become_runtime_installation_binding():
    bindings = resolve_tool_attachment_installation_bindings(
        _claims(),
        tool_ref="Hilti:2253847",
        attachment_product_refs={},
    )
    assert bindings == []


def test_hilti_manual_retains_product_scoped_connection_evidence_without_inventing_form():
    claims = _claims()

    # Product-scoped manufacturer evidence cannot execute until both identifiers have
    # been resolved by catalogue composition; it must not silently widen to a generic rule.
    assert resolve_connector_interface_compatibility_declarations(claims) == []

    declaration = _resolved_connection_declaration()
    assert declaration.declaration_id == "tool_tether_to_retaining_strap:2261970:2293133"
    assert declaration.connector_spec_ref == "tether_connector"
    assert declaration.source_interface_type == "carabiner"
    assert declaration.target_interface_type == "attachment_point"
    assert declaration.target_role.value == "tool_attachment_tether_side"
    assert declaration.source_product_ref == "Hilti:2261970"
    assert declaration.target_product_ref == "Hilti:2293133"
    assert declaration.issuer_manufacturer == "Hilti"
    assert declaration.source_urls == [MANUAL_URL]

    audit_scope = {
        claim.property_key: claim.value
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        and claim.subject_ref == "tool_tether_to_retaining_strap:2261970:2293133"
    }
    assert audit_scope["connection_compatibility.source_product_identifier"] == "2261970"
    assert audit_scope["connection_compatibility.target_product_identifier"] == "2293133"


def test_hilti_product_scoped_connection_evidence_does_not_leak_to_matching_primitives():
    declaration = _resolved_connection_declaration()
    endpoint = ConnectionInterface(
        interface_id="connection_point_1",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        connector_spec_ref="tether_connector",
    )
    target = ConnectionInterface(
        interface_id="tether_attachment_point",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="attachment_point",
    )

    matching = connection_contexts_from_compatibility_declarations(
        tether_ref="Hilti:2261970",
        tether_product_ref="Hilti:2261970",
        endpoints=[endpoint],
        target_owner_ref="Hilti:2293133:assembly",
        target_product_refs={"Hilti:2293133"},
        target_interfaces=[target],
        declarations=[declaration],
    )
    assert len(matching) == 1

    wrong_tether = connection_contexts_from_compatibility_declarations(
        tether_ref="Other:2261970-shaped",
        tether_product_ref="Other:tether",
        endpoints=[endpoint],
        target_owner_ref="Hilti:2293133:assembly",
        target_product_refs={"Hilti:2293133"},
        target_interfaces=[target],
        declarations=[declaration],
    )
    assert wrong_tether == []

    wrong_attachment = connection_contexts_from_compatibility_declarations(
        tether_ref="Hilti:2261970",
        tether_product_ref="Hilti:2261970",
        endpoints=[endpoint],
        target_owner_ref="Other:attachment:assembly",
        target_product_refs={"Other:attachment"},
        target_interfaces=[target],
        declarations=[declaration],
    )
    assert wrong_attachment == []