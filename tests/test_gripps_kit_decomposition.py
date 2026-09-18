from __future__ import annotations

from tetherlens_ingest.adapters import GRIPPSAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.anchor_installation import AnchorInstallationMethod
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentBasis,
    resolve_tether_endpoint_assignment_declarations,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.product_relationship import (
    DeclaredProductRelationshipType,
    resolve_declared_product_relationships,
)
from tetherlens_ingest.resolution import (
    resolve_connection_interfaces,
    resolve_connector_specs,
)
from tetherlens_ingest.runner import IngestionRunner


class StaticFetcher:
    def __init__(self, artifact: SourceArtifact):
        self.artifact = artifact

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        assert url == self.artifact.url
        return self.artifact.model_copy(deep=True, update={"source_type": source_type})


def _artifact(url: str, body: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_h01088_extracts_kit_relationships_but_identity_conflict_blocks_readiness() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.UNKNOWN,
        name="Adjustable Wrist Anchor With Tool Tether",
        sku="H01088",
        url="https://gripps.com/products/adjustable-wrist-anchor-with-webbing-wrist-tether-single-action",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Adjustable Wrist Anchor With Tool Tether - 2.5kg / 5.5lb</h1>
        <p>SKU: H01088</p>
        <p>The GRIPPS Adjustable Wrist Anchor uses industrial-grade Velcro.</p>
        <h3>Kit Contents</h3>
        <table>
          <tr><th>Part No.</th><th>Description</th><th>Qty</th></tr>
          <tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td><td>1</td></tr>
          <tr><td>H01085</td><td>Slip-On Wrist Anchor</td><td>1</td></tr>
        </table>
        <h3>Related Products</h3>
        <table>
          <tr><td>H09999</td><td>Unrelated Product</td><td>1</td></tr>
        </table>
        """,
    )

    result = IngestionRunner(StaticFetcher(artifact)).ingest(identity, GRIPPSAdapter())

    relationship_claims = [
        claim
        for claim in result.claims
        if claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
    ]
    assert {
        claim.value
        for claim in relationship_claims
        if claim.property_key == "declared_relationship.object_product_identifier"
    } == {"H01067", "H01085"}
    assert not any(
        claim.value == "H09999"
        for claim in relationship_claims
        if claim.property_key == "declared_relationship.object_product_identifier"
    )

    relationships = resolve_declared_product_relationships(
        relationship_claims,
        subject_product_ref="GRIPPS:H01088",
        product_refs_by_identifier={
            "H01067": "GRIPPS:H01067",
            "H01085": "GRIPPS:H01085-S",
        },
    )
    assert {
        (
            relationship.object_product_ref,
            relationship.relationship_type,
            relationship.quantity,
        )
        for relationship in relationships
    } == {
        ("GRIPPS:H01067", DeclaredProductRelationshipType.KIT_RELATIONSHIP, 1),
        ("GRIPPS:H01085-S", DeclaredProductRelationshipType.KIT_RELATIONSHIP, 1),
    }

    assert result.readiness_assessed is True
    assert [issue.code for issue in result.issues] == ["KIT_COMPONENT_IDENTITY_CONFLICT"]
    assert "H01085 Slip-On Wrist Anchor" in (result.issues[0].detail or "")


def test_related_products_without_kit_contents_do_not_create_kit_membership() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.UNKNOWN,
        name="Example Wrapper",
        sku="H09998",
        url="https://gripps.com/products/example-wrapper",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Example Wrapper</h1><p>SKU H09998</p>
        <h3>Related Products</h3>
        <table><tr><td>H01067</td><td>Webbing Wrist Tether</td><td>1</td></tr></table>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        for claim in claims
    )


def test_h01067_compiles_existing_reversible_endpoint_assignment_semantics() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Wrist Tether Single-Action",
        sku="H01067",
        url="https://gripps.com/products/webbing-single-action-wrist-tether",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Webbing Wrist Tether Single-Action - 2.5kg / 5.5lb</h1>
        <p>SKU H01067</p>
        <p>This tether facilitates secure attachment of hand tools to GRIPPS gloves or wrist anchors.</p>
        <p>Two swivel-head single-action carabiners.</p>
        <p>Max Load: 2.5 kg | 5.5 lb</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])
    interfaces = resolve_connection_interfaces(claims)
    specs = resolve_connector_specs(claims)
    declarations = resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    )

    assert {interface.interface_id for interface in interfaces} == {
        "connection_point_1",
        "connection_point_2",
    }
    assert all(interface.tether_side.value == "unknown" for interface in interfaces)
    assert all(interface.interface_type == "carabiner" for interface in interfaces)
    assert all(
        interface.connector_spec_ref == "wrist_tether_carabiner"
        for interface in interfaces
    )

    spec = specs["wrist_tether_carabiner"]
    assert spec.opening_action_count == 1
    assert spec.swivel is True

    assert len(declarations) == 1
    declaration = declarations[0]
    assert declaration.endpoint_refs == ["connection_point_1", "connection_point_2"]
    assert declaration.basis == EndpointAssignmentBasis.DERIVED_ENDPOINT_EQUIVALENCE
    assert declaration.issuer_manufacturer == "GRIPPS"


def test_h01067_pair_without_tool_to_wrist_use_does_not_invent_reversibility() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Wrist Tether Single-Action",
        sku="H01067",
        url="https://gripps.com/products/webbing-single-action-wrist-tether",
    )
    artifact = _artifact(
        identity.url,
        "<h1>Webbing Wrist Tether</h1><p>SKU H01067</p>"
        "<p>Two swivel-head single-action carabiners.</p>",
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    ) == []


def test_h01085_uses_slip_on_wrist_path_and_preserves_h01067_endorsement() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Slip-On Wrist Anchor",
        sku="H01085-S",
        url="https://gripps.com/products/slip-on-wrist-anchor",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Slip-On Wrist Anchor - 2.5kg / 5.5lb</h1>
        <p>SKU: H01085-S</p>
        <p>The GRIPPS Slip-On Wrist Anchor is a wrist-mounted tether anchor.</p>
        <p>Just slip it on, secure your tool, and start your task.</p>
        <p>Suitable for use with our H01060, H01062 and H01067 wrist tethers.</p>
        <p>Built-in load-rated tether anchor point.</p>
        <p>Max Load: 2.5 kg | 5.5 lb</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="GRIPPS:H01085-S",
    )
    interfaces = resolve_connection_interfaces(claims)
    relationships = resolve_declared_product_relationships(
        claims,
        subject_product_ref="GRIPPS:H01085-S",
        product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
    )

    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.SLIP_ON
    assert [path.binding_name for path in rule.paths] == ["wrist"]
    assert {
        predicate.property_key: predicate.value
        for predicate in rule.paths[0].requirements
    } == {"feature_kind": "wrist"}

    assert len(interfaces) == 1
    assert interfaces[0].role.value == "anchor_attachment_tether_side"
    assert interfaces[0].interface_type == "unknown"

    assert len(relationships) == 1
    assert relationships[0].relationship_type == (
        DeclaredProductRelationshipType.EXPLICITLY_ENDORSED
    )
    assert relationships[0].object_product_ref == "GRIPPS:H01067"


def test_h01085_does_not_turn_size_labels_into_numeric_wrist_fit() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Slip-On Wrist Anchor",
        sku="H01085-M",
        url="https://gripps.com/products/slip-on-wrist-anchor",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Slip-On Wrist Anchor - 2.5kg / 5.5lb</h1>
        <p>SKU: H01085-M</p>
        <p>Available in Small, Medium and Large.</p>
        <p>The wrist-mounted tether anchor is easy to use. Just slip it on.</p>
        <p>Built-in load-rated tether anchor point.</p>
        <p>Max Load: 2.5kg / 5.5lb</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in claims
    )
