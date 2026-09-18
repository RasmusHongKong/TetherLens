from __future__ import annotations

from tetherlens_ingest.adapters import GRIPPSAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.anchor_installation import AnchorInstallationMethod
from tetherlens_ingest.declared_compatibility import (
    resolve_connector_interface_compatibility_declarations,
)
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


class RedirectingFetcher:
    def __init__(self, requested_url: str, artifact: SourceArtifact):
        self.requested_url = requested_url
        self.artifact = artifact

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        assert url == self.requested_url
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
        product_type=ProductType.KIT,
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
    }
    # The wrapper names only the H01085 family. Do not silently select one of the
    # separately sold H01085-S/M/L variants just to make the kit executable.
    assert not any(
        relationship.object_product_identifier == "H01085"
        for relationship in relationships
    )

    assert result.readiness_assessed is True
    assert [issue.code for issue in result.issues] == ["KIT_COMPONENT_IDENTITY_CONFLICT"]
    assert "H01085 Slip-On Wrist Anchor" in (result.issues[0].detail or "")


def test_related_products_without_kit_contents_do_not_create_kit_membership() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
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
    connection_declarations = resolve_connector_interface_compatibility_declarations(
        claims,
        product_refs_by_identifier={
            "H01067": "GRIPPS:H01067",
            "H01085-S": "GRIPPS:H01085-S",
        },
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
    assert relationships[0].quantity is None

    assert len(connection_declarations) == 1
    connection_declaration = connection_declarations[0]
    assert connection_declaration.connector_spec_ref is None
    assert connection_declaration.source_interface_type is None
    assert connection_declaration.target_interface_type is None
    assert connection_declaration.target_role is None
    assert connection_declaration.source_product_ref == "GRIPPS:H01067"
    assert connection_declaration.target_product_ref == "GRIPPS:H01085-S"
    assert connection_declaration.issuer_manufacturer == "GRIPPS"

    target_identity_claim = next(
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        and claim.property_key == "connection_compatibility.target_product_identifier"
    )
    assert target_identity_claim.value == "H01085-S"
    assert target_identity_claim.raw_value == "SKU: H01085-S"
    assert target_identity_claim.evidence_method == "manufacturer_product_identity"

    source_identity_claim = next(
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        and claim.property_key == "connection_compatibility.source_product_identifier"
    )
    assert source_identity_claim.value == "H01067"
    assert "H01067" in (source_identity_claim.raw_value or "")
    assert source_identity_claim.evidence_method == "manufacturer_pairing"



def test_h01085_family_h1_does_not_authorize_unstated_exact_variant_connection() -> None:
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
        <p>Available in Small, Medium and Large.</p>
        <p>Suitable for use with our H01067 wrist tethers.</p>
        <p>Built-in load-rated tether anchor point.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        for claim in claims
    )

def test_h01085_sibling_variant_mention_does_not_authorize_requested_variant() -> None:
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
        <p>SKU: H01085-S</p>
        <p>Also available as H01085-M.</p>
        <p>Suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        for claim in claims
    )


def test_h01085_multiple_identity_bearing_variants_fail_closed() -> None:
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
        <p>SKU: H01085-S</p>
        <p>SKU: H01085-M</p>
        <p>Suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        for claim in claims
    )


def test_h01085_connection_declaration_fails_closed_without_exact_variant_mapping() -> None:
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
        <p>Suitable for use with our H01060, H01062 and H01067 wrist tethers.</p>
        <p>Built-in load-rated tether anchor point.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_connector_interface_compatibility_declarations(
        claims,
        product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
    ) == []


def test_h01085_unrelated_comma_negation_does_not_block_suitability() -> None:
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
        <p>No special tools are required, this product is suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        for claim in claims
    )


def test_h01085_contradictory_suitability_wording_is_not_executable() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Slip-On Wrist Anchor",
        sku="H01085-M",
        url="https://gripps.com/products/slip-on-wrist-anchor",
    )
    contradictory_phrases = (
        "No product is suitable for use with our H01067 wrist tethers.",
        "Suitable for use with our H01067 wrist tethers, but must not be connected that way.",
        "Suitable for use with our H01067 wrist tethers, but this tether must not be connected that way.",
        "Suitable for use with our H01067 wrist tethers, but cannot be used that way.",
        "Suitable for use with our H01067 wrist tethers, however never attach them that way.",
        "Suitable for use with our H01067 wrist tethers, yet do not tether them that way.",
        "Suitable for use with our H01067 wrist tethers. However, do not connect it this way.",
        "Suitable for use with our H01067 wrist tethers. Yet never attach it that way.",
        "Suitable for use with our H01067 wrist tethers. Do not connect this tether to the anchor.",
        "Suitable for use with our H01067 wrist tethers. Never attach this tether to the anchor.",
        "Suitable for use with our H01067 wrist tethers. Cannot be used with this anchor.",
        "Suitable for use with our H01060 wrist tethers; not H01067 wrist tethers.",
        "Suitable for use with our H01060 wrist tethers, except H01067 wrist tethers.",
        "Suitable for use with our H01060 wrist tethers, excluding H01067 wrist tethers.",
        "Suitable for use with our H01060 wrist tethers; H01067 is not suitable for wrist tethers.",
        "Suitable for use with our H01060 wrist tethers, but H01067 is not suitable for wrist tethers.",
        "Suitable for use with our H01060 wrist tethers, H01067 isn't suitable for wrist tethers.",
        "Suitable for use with our H01067 wrist tethers. H01067 is not compatible with this anchor.",
        "Suitable for use with our H01067 wrist tethers. H01067 is not suitable for this anchor.",
        "Suitable for use with our H01067 wrist tethers. This tether is not compatible with this anchor.",
        "Suitable for use with our H01067 wrist tethers. However, H01067 is not compatible with this anchor.",
        "Suitable for use with our H01067 wrist tethers. H01067 isn't compatible with this anchor.",
        "Suitable for use with our H01067 wrist tethers. H01067 is incompatible with this anchor.",
        "Suitable for use with our H01067 wrist tethers. H01067 is unsuitable for this anchor.",
    )

    for phrase in contradictory_phrases:
        artifact = _artifact(
            identity.url,
            f"""
            <h1>Slip-On Wrist Anchor - 2.5kg / 5.5lb</h1>
            <p>SKU: H01085-M</p>
            <p>{phrase}</p>
            """,
        )

        claims = GRIPPSAdapter().extract(identity, [artifact])

        assert not any(
            claim.subject_type in {
                ClaimSubjectType.DECLARED_RELATIONSHIP,
                ClaimSubjectType.CONNECTION_COMPATIBILITY,
            }
            for claim in claims
        ), phrase


def test_h01085_family_identity_does_not_widen_exact_connection_evidence() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Slip-On Wrist Anchor",
        sku="H01085",
        url="https://gripps.com/products/slip-on-wrist-anchor",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Slip-On Wrist Anchor - 2.5kg / 5.5lb</h1>
        <p>Suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        for claim in claims
    )

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



def test_kit_contents_label_does_not_capture_later_related_products_table() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
        name="Incomplete Kit Wrapper",
        sku="H09997",
        url="https://gripps.com/products/incomplete-kit-wrapper",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Incomplete Kit Wrapper</h1><p>SKU H09997</p>
        <h3>Kit Contents</h3><p>See package for contents.</p>
        <h3>Related Products</h3>
        <table><tr><td>H01067</td><td>Webbing Wrist Tether</td><td>1</td></tr></table>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        for claim in claims
    )



def test_cross_sell_copy_does_not_create_kit_identity_conflict() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
        name="Slip-On Wrist Anchor With Tool Tether",
        sku="H01087-M",
        url="https://gripps.com/products/slip-on-wrist-anchor-with-tool-tether",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Slip-On Wrist Anchor With Tool Tether - 2.5kg / 5.5lb</h1>
        <p>SKU H01087-M</p>
        <p>The slip-on wrist anchor is supplied with a tool tether.</p>
        <h3>Kit Contents</h3>
        <table>
          <tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td><td>1</td></tr>
          <tr><td>H01085-M</td><td>Slip-On Wrist Anchor</td><td>1</td></tr>
        </table>
        <h3>Related Products</h3>
        <p>The Adjustable Wrist Anchor uses industrial-grade Velcro.</p>
        """,
    )

    result = IngestionRunner(StaticFetcher(artifact)).ingest(identity, GRIPPSAdapter())

    assert not any(
        issue.code == "KIT_COMPONENT_IDENTITY_CONFLICT"
        for issue in result.issues
    )


def test_h01085_cross_sell_copy_does_not_create_tether_endorsement() -> None:
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
        <p>SKU H01085-S</p>
        <p>The GRIPPS Slip-On Wrist Anchor is a wrist-mounted tether anchor.</p>
        <p>Just slip it on, secure your tool, and start your task.</p>
        <h3>Related Products</h3>
        <p>Suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        and claim.property_key == "declared_relationship.object_product_identifier"
        and claim.value == "H01067"
        for claim in claims
    )
    assert not any(
        claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        for claim in claims
    )


def test_kit_membership_survives_blank_or_omitted_quantity() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
        name="Example Kit",
        sku="H09996",
        url="https://gripps.com/products/example-kit",
    )
    rows = (
        "<tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td><td></td></tr>",
        "<tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td></tr>",
    )

    for row in rows:
        artifact = _artifact(
            identity.url,
            f"""
            <h1>Example Kit</h1><p>SKU H09996</p>
            <h3>Kit Contents</h3>
            <table>{row}</table>
            """,
        )

        claims = GRIPPSAdapter().extract(identity, [artifact])
        relationship_claims = [
            claim
            for claim in claims
            if claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        ]
        resolved = resolve_declared_product_relationships(
            relationship_claims,
            subject_product_ref="GRIPPS:H09996",
            product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
        )

        assert any(
            claim.property_key == "declared_relationship.object_product_identifier"
            and claim.value == "H01067"
            for claim in relationship_claims
        )
        assert not any(
            claim.property_key == "declared_relationship.quantity"
            for claim in relationship_claims
        )
        assert len(resolved) == 1
        assert resolved[0].quantity is None



def test_malformed_kit_quantity_does_not_become_unknown_membership() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
        name="Malformed Kit",
        sku="H09995",
        url="https://gripps.com/products/malformed-kit",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Malformed Kit</h1><p>SKU H09995</p>
        <h3>Kit Contents</h3>
        <table>
          <tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td><td>Ea</td></tr>
        </table>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        for claim in claims
    )



def test_sibling_kit_contents_outside_requested_product_region_are_ignored() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.KIT,
        name="Primary Kit",
        sku="H09994",
        url="https://gripps.com/products/primary-kit",
    )
    artifact = _artifact(
        identity.url,
        """
        <h1>Primary Kit</h1><p>SKU H09994</p>
        <p>This product has no published component table.</p>
        <h1>Sibling Kit</h1>
        <h3>Kit Contents</h3>
        <table>
          <tr><td>H01067</td><td>Webbing Wrist Tether Single-Action</td><td>1</td></tr>
        </table>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        for claim in claims
    )


def test_h01067_same_host_redirect_does_not_create_endpoint_semantics() -> None:
    requested = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Wrist Tether Single-Action",
        sku="H01067",
        url="https://gripps.com/products/webbing-single-action-wrist-tether",
    )
    redirected = _artifact(
        "https://gripps.com/products/different-tether",
        """
        <h1>Different Tether</h1><p>SKU H09993</p>
        <p>Two swivel-head single-action carabiners.</p>
        <p>Attachment of hand tools to gloves or wrist anchors.</p>
        <p>Max Load: 2.5 kg</p>
        """,
    )

    result = IngestionRunner(
        RedirectingFetcher(requested.url, redirected)
    ).ingest(requested, GRIPPSAdapter())

    assert result.claims == []


def test_h01067_cross_sell_pair_use_does_not_create_reversible_assignment() -> None:
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
        <h1>Webbing Wrist Tether Single-Action</h1><p>SKU H01067</p>
        <p>Two swivel-head single-action carabiners.</p>
        <h3>Related Products</h3>
        <p>Attachment of hand tools to gloves or wrist anchors.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    ) == []


def test_h01085_cross_sell_slip_action_does_not_create_installation_rule() -> None:
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
        <h1>Slip-On Wrist Anchor</h1><p>SKU H01085-S</p>
        <p>This wrist-mounted tether anchor has a load-rated tether point.</p>
        <h3>Related Products</h3>
        <p>Just slip it on, secure your tool, and start your task.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="GRIPPS:H01085-S",
    ) is None



def test_h01067_negated_pair_construction_does_not_create_endpoint_claims() -> None:
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
        <h1>Webbing Wrist Tether Single-Action</h1><p>SKU H01067</p>
        <p>This model does not have two swivel-head single-action carabiners.</p>
        <p>Attachment of hand tools to gloves or wrist anchors.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.property_key == "tether.connection_count"
        for claim in claims
    )
    assert resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    ) == []


def test_h01067_negated_pair_use_does_not_create_reversible_assignment() -> None:
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
        <h1>Webbing Wrist Tether Single-Action</h1><p>SKU H01067</p>
        <p>Two swivel-head single-action carabiners.</p>
        <p>This model is not approved for attachment of hand tools to wrist anchors.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert any(
        claim.property_key == "tether.connection_count"
        for claim in claims
    )
    assert resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    ) == []


def test_h01067_direction_after_carabiner_vetoes_reversible_assignment() -> None:
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
        <h1>Webbing Wrist Tether Single-Action</h1><p>SKU H01067</p>
        <p>Two swivel-head single-action carabiners.</p>
        <p>Attachment of hand tools to gloves or wrist anchors.</p>
        <p>One carabiner is dedicated to the tool end and the other to the anchor end.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="GRIPPS:H01067",
    ) == []


def test_h01085_negated_slip_instruction_does_not_create_installation_rule() -> None:
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
        <h1>Slip-On Wrist Anchor</h1><p>SKU H01085-S</p>
        <p>This is a wrist-mounted tether anchor, but do not just slip it on.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="GRIPPS:H01085-S",
    ) is None


def test_h01085_negated_h01067_suitability_does_not_create_endorsement() -> None:
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
        <h1>Slip-On Wrist Anchor</h1><p>SKU H01085-S</p>
        <p>This product is not suitable for use with our H01067 wrist tethers.</p>
        """,
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])

    assert not any(
        claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP
        and claim.property_key == "declared_relationship.object_product_identifier"
        and claim.value == "H01067"
        for claim in claims
    )
