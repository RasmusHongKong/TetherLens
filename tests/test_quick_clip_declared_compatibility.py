from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
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
from tetherlens_ingest.recommendation import (
    RecommendationState,
    evaluate_candidate_configuration,
)


SOURCE_URL = "https://go.neverletgo.com/hubfs/Product/Datasheet/101456.pdf"


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url=SOURCE_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="text/html",
        body=body,
    )


def identity(*, sku: str = "not-a-golden-sku") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Retractable Quick Clip Attachment",
        sku=sku,
        url="https://neverletgo.com/products/retractable-quick-clip-attachment/",
    )


def declaration_claims(body: str):
    return [
        claim
        for claim in NLGAdapter().extract(identity(), [artifact(body)])
        if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
    ]


def accepted_declaration():
    claims = declaration_claims(
        "<p>Featuring the Quick Clip™ it can be quickly and easily attached to a D Ring.</p>"
    )
    return resolve_connector_interface_compatibility_declarations(claims)[0]


def quick_clip_endpoint(
    endpoint_id: str = "tether:anchor-clip",
    *,
    side: TetherSide = TetherSide.ANCHOR_SIDE,
) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=endpoint_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="clip",
        tether_side=side,
        connector_spec_ref="quick_clip",
    )


def d_ring_anchor(interface_id: str = "anchor:d-ring") -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        attributes={"ring_form": "d_ring"},
    )


def test_quick_clip_d_ring_declaration_is_evidence_led_not_sku_led():
    claims = declaration_claims(
        "<p>Featuring the Quick Clip™ it can be quickly and easily attached to a D Ring.</p>"
    )

    assert {claim.property_key for claim in claims} == {
        "connection_compatibility.connector_spec_ref",
        "connection_compatibility.source_interface_type",
        "connection_compatibility.target_interface_type",
        "connection_compatibility.target_role",
        "connection_compatibility.target_attribute.ring_form",
        "connection_compatibility.issuer_manufacturer",
        "connection_compatibility.scope",
    }
    assert {claim.subject_ref for claim in claims} == {"quick_clip_to_d_ring_anchor"}
    assert {claim.source_url for claim in claims} == {SOURCE_URL}
    assert any(claim.value == "d_ring" for claim in claims)


def test_quick_clip_d_ring_declaration_rejects_cross_block_question_and_negation():
    bodies = (
        "<p>Quick Clips provide secure attachment.</p><p>Attach the lanyard to a D Ring.</p>",
        "<p>Can a Quick Clip be attached to a D Ring?</p>",
        "<p>The Quick Clip should not be attached to a D Ring.</p>",
    )
    for body in bodies:
        assert declaration_claims(body) == [], body


def test_designed_anchor_wording_also_establishes_the_same_declaration():
    claims = declaration_claims(
        "<p>The Retractable Quick Clip Attachment has been specifically designed to "
        "securely anchor the lanyard to a D Ring style anchor point.</p>"
    )

    assert claims
    declaration = resolve_connector_interface_compatibility_declarations(claims)[0]
    assert declaration.connector_spec_ref == "quick_clip"
    assert declaration.source_interface_type == "clip"
    assert declaration.target_interface_type == "ring"
    assert declaration.target_role == ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE
    assert declaration.target_attributes == {"ring_form": "d_ring"}
    assert declaration.issuer_manufacturer == "NLG"
    assert declaration.source_urls == [SOURCE_URL]


def test_declaration_binds_to_exact_d_ring_anchor_and_uses_existing_manufacturer_basis():
    endpoint = quick_clip_endpoint()
    target = d_ring_anchor()
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref="product:tether-a",
        endpoints=[endpoint],
        target_owner_ref="product:anchor-a",
        target_interfaces=[target],
        declarations=[accepted_declaration()],
    )

    assert len(contexts) == 1
    result = evaluate_endpoint_engagement(
        endpoint,
        target,
        manufacturer_assessments=contexts[0].manufacturer_assessments,
    )

    assert result.status == ConnectionStatus.COMPATIBLE
    assert result.basis == CompatibilityBasis.MANUFACTURER_DECLARED
    assert result.verification_family is None
    assert result.manufacturer_assessments[0].issuer_manufacturer == "NLG"
    assert result.manufacturer_assessments[0].claim_or_evidence_ref == SOURCE_URL


def test_declaration_does_not_widen_to_generic_ring_or_tool_attachment_d_ring():
    endpoint = quick_clip_endpoint()
    declaration = accepted_declaration()
    generic_ring = ConnectionInterface(
        interface_id="anchor:generic-ring",
        role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )
    tool_attachment_d_ring = ConnectionInterface(
        interface_id="tool-attachment:d-ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
        attributes={"ring_form": "d_ring"},
    )

    for target in (generic_ring, tool_attachment_d_ring):
        contexts = connection_contexts_from_compatibility_declarations(
            tether_ref="product:tether-a",
            endpoints=[endpoint],
            target_owner_ref="product:target-a",
            target_interfaces=[target],
            declarations=[declaration],
        )
        assert contexts == []
        result = evaluate_endpoint_engagement(endpoint, target)
        assert result.status == ConnectionStatus.UNRESOLVED
        assert result.basis == CompatibilityBasis.NONE


def test_bound_declaration_flows_through_candidate_generation_without_sku_pair_logic():
    tool_endpoint = ConnectionInterface(
        interface_id="tether:tool-carabiner",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.TOOL_SIDE,
        connector_spec_ref="tool_carabiner",
    )
    anchor_endpoint = quick_clip_endpoint()
    tether = TetherOption(
        tether_ref="product:tether-a",
        component=CandidateComponentOption(
            component_ref="component:tether-a",
            source_product_ref="product:tether-a",
            rated_capacity_kg=5.0,
        ),
        endpoints=[tool_endpoint, anchor_endpoint],
        connector_specs={
            "tool_carabiner": ConnectorSpec(
                connector_spec_id="tool_carabiner",
                opening_action_count=2,
            ),
            "quick_clip": ConnectorSpec(
                connector_spec_id="quick_clip",
                attributes={"opening_mechanism": "trigger_operated"},
            ),
        },
    )
    anchor_target = d_ring_anchor()
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref=tether.tether_ref,
        endpoints=tether.endpoints,
        target_owner_ref="anchor:path-a",
        target_interfaces=[anchor_target],
        declarations=[accepted_declaration()],
    )

    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:a",
            object_mass_kg=2.0,
            direct_interfaces=[
                ConnectionInterface(
                    interface_id="tool:ring",
                    role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                    interface_type="ring",
                )
            ],
        ),
        [tether],
        [
            AnchorPathOption(
                anchor_path_ref="anchor:path-a",
                components=[
                    CandidateComponentOption(
                        component_ref="component:anchor-a",
                        source_product_ref="product:anchor-a",
                        rated_capacity_kg=5.0,
                    )
                ],
                target_interfaces=[anchor_target],
            )
        ],
        connection_contexts=contexts,
    )

    assert len(generated) == 1
    candidate = generated[0]
    assert candidate.configuration.anchor_side_connection.status == ConnectionStatus.COMPATIBLE
    assert candidate.configuration.anchor_side_connection.basis == CompatibilityBasis.MANUFACTURER_DECLARED
    assert candidate.configuration.tool_side_connection.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert (
        evaluate_candidate_configuration(candidate.configuration).recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
    )


def test_declaration_does_not_promote_unknown_symmetric_endpoint_roles_to_either():
    tether = TetherOption(
        tether_ref="product:dual-quick-clip",
        component=CandidateComponentOption(
            component_ref="component:dual-quick-clip",
            source_product_ref="product:dual-quick-clip",
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            quick_clip_endpoint("clip:1", side=TetherSide.UNKNOWN),
            quick_clip_endpoint("clip:2", side=TetherSide.UNKNOWN),
        ],
        connector_specs={
            "quick_clip": ConnectorSpec(
                connector_spec_id="quick_clip",
                attributes={"opening_mechanism": "trigger_operated"},
            )
        },
    )
    target = d_ring_anchor()
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref=tether.tether_ref,
        endpoints=tether.endpoints,
        target_owner_ref="anchor:path-a",
        target_interfaces=[target],
        declarations=[accepted_declaration()],
    )

    assert len(contexts) == 2
    generated = generate_candidate_configurations(
        ResolvedToolCandidate(
            tool_ref="tool:a",
            object_mass_kg=2.0,
            direct_interfaces=[
                ConnectionInterface(
                    interface_id="tool:ring",
                    role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                    interface_type="ring",
                )
            ],
        ),
        [tether],
        [
            AnchorPathOption(
                anchor_path_ref="anchor:path-a",
                target_interfaces=[target],
            )
        ],
        connection_contexts=contexts,
    )

    assert generated == []
