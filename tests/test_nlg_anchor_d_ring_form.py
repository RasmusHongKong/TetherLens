from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
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
from tetherlens_ingest.resolution import resolve_connection_interfaces


ANCHOR_URL = "https://neverletgo.com/products/wristband/"
DECLARATION_URL = "https://go.neverletgo.com/hubfs/Product/Datasheet/101456.pdf"


def artifact(body: str, *, url: str = ANCHOR_URL) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def anchor_identity(*, name: str = "Generic Wrist Anchor", sku: str = "not-a-rule-sku"):
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name=name,
        sku=sku,
        url=ANCHOR_URL,
    )


def physical_claims(body: str, *, name: str = "Generic Wrist Anchor"):
    return [
        claim
        for claim in NLGAdapter().extract(
            anchor_identity(name=name),
            [artifact(body)],
        )
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "lanyard_anchor_d_ring"
    ]


def keyed(claims):
    return {claim.property_key: claim.value for claim in claims}


def test_singular_anchor_d_ring_relation_emits_role_type_and_form_without_sku_logic():
    claims = physical_claims(
        "<p>The Adjustable Wristband creates a universal fit anchor point on the wrist "
        "and utilises a durable plastic D ring for quick and easy lanyard attachment.</p>",
        name="Anchor product without D-ring naming",
    )
    out = keyed(claims)

    assert out == {
        "interface.role": "anchor_attachment_tether_side",
        "interface.type": "ring",
        "interface.attribute.ring_form": "d_ring",
    }
    assert {claim.source_url for claim in claims} == {ANCHOR_URL}

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "lanyard_anchor_d_ring"
    assert interface.role == ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE
    assert interface.interface_type == "ring"
    assert interface.attributes == {"ring_form": "d_ring"}


def test_product_name_or_bare_d_ring_does_not_create_anchor_target():
    bodies = (
        "<p>Comfortable wrist anchor point for small tools.</p>",
        "<p>Durable D Ring construction.</p>",
    )
    for body in bodies:
        assert physical_claims(body, name="Adjustable D Ring Wrist Anchor") == [], body


def test_generic_ring_lanyard_relation_does_not_upgrade_to_d_ring():
    claims = physical_claims(
        "<p>The wristband uses a durable ring for quick and easy lanyard attachment.</p>"
    )
    assert claims == []


def test_cross_block_d_ring_and_lanyard_copy_is_not_joined():
    claims = physical_claims(
        "<p>The wristband includes a durable plastic D Ring.</p>"
        "<p>For quick and easy lanyard attachment.</p>"
    )
    assert claims == []


def test_plural_d_ring_lanyard_set_fails_closed_instead_of_collapsing_identity():
    claims = physical_claims(
        "<p>The integrated load-rated D rings provide secure anchor points for directly "
        "attaching tool lanyards.</p>"
    )
    assert claims == []


def test_brace_mounting_d_ring_is_not_a_lanyard_target():
    claims = physical_claims("<p>The D Ring is used to attach the braces.</p>")
    assert claims == []


def test_local_negation_and_question_fail_closed():
    bodies = (
        "<p>Do not attach a tool lanyard to the D Ring.</p>",
        "<p>Avoid attaching a tool lanyard to the D Ring.</p>",
        "<p>Is a tool lanyard attached to the D Ring?</p>",
        "<p>Attach a tool lanyard to the D Ring, but do not use it that way.</p>",
    )
    for body in bodies:
        assert physical_claims(body) == [], body


def test_unrelated_negation_does_not_suppress_positive_d_ring_relation():
    claims = physical_claims(
        "<p>The wristband does not contain metal and utilises a durable plastic D Ring "
        "for quick and easy lanyard attachment.</p>"
    )
    assert keyed(claims)["interface.attribute.ring_form"] == "d_ring"


def test_container_d_ring_form_does_not_become_anchor_attachment_target():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.CONTAINER,
            name="Tall Tool Bag",
            sku="example",
            url="https://example.test/container",
        ),
        [
            artifact(
                "<p>6 integrated D Rings for tool lanyard attachment.</p>",
                url="https://example.test/container",
            )
        ],
    )
    interfaces = resolve_connection_interfaces(claims)
    assert not any(
        interface.role == ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE
        and interface.attributes.get("ring_form") == "d_ring"
        for interface in interfaces
    )


def test_extracted_anchor_d_ring_unlocks_existing_quick_clip_declaration_path():
    anchor_claims = NLGAdapter().extract(
        anchor_identity(),
        [
            artifact(
                "<p>The Adjustable Wristband creates a universal fit anchor point on the wrist "
                "and utilises a durable plastic D Ring for quick and easy lanyard attachment.</p>"
            )
        ],
    )
    target = next(
        interface
        for interface in resolve_connection_interfaces(anchor_claims)
        if interface.interface_id == "lanyard_anchor_d_ring"
    )

    declaration_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.ANCHOR_ATTACHMENT,
            name="Retractable Quick Clip Attachment",
            sku="different-product-entirely",
            url="https://example.test/quick-clip",
        ),
        [
            artifact(
                "<p>Featuring the Quick Clip it can be quickly and easily attached to a D Ring.</p>",
                url=DECLARATION_URL,
            )
        ],
    )
    declarations = resolve_connector_interface_compatibility_declarations(
        [
            claim
            for claim in declaration_claims
            if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
        ]
    )
    assert len(declarations) == 1

    endpoint = ConnectionInterface(
        interface_id="anchor_quick_clip",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="clip",
        tether_side=TetherSide.ANCHOR_SIDE,
        connector_spec_ref="quick_clip",
    )
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref="product:any-quick-clip-tether",
        endpoints=[endpoint],
        target_owner_ref="product:any-anchor",
        target_interfaces=[target],
        declarations=declarations,
    )

    assert len(contexts) == 1
    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        manufacturer_assessments=contexts[0].manufacturer_assessments,
    )
    assert result.status == ConnectionStatus.COMPATIBLE
    assert result.basis == CompatibilityBasis.MANUFACTURER_DECLARED
