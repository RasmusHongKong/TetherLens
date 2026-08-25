from tetherlens_ingest.adapters import KleinAdapter, NLGAdapter
from tetherlens_ingest.compatibility import EligibilityStatus, evaluate_attachment_eligibility
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
    resolve_tool_interface_features,
)


def artifact(body: str, *, url: str = "https://example.test/product") -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def provided_ring_claims() -> list[CandidateClaim]:
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tether_side_ring",
            property_key="interface.role",
            value="tool_attachment_tether_side",
            source_url="https://example.test/attachment",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="tether_side_ring",
            property_key="interface.type",
            value="ring",
            source_url="https://example.test/attachment",
            extractor="test",
        ),
    ]


def test_provided_ring_claims_resolve_to_distinct_connection_interface():
    interfaces = resolve_connection_interfaces(provided_ring_claims())

    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "tether_side_ring"
    assert interface.role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interface.interface_type == "ring"


def test_incomplete_physical_interface_claims_do_not_become_connection_interface():
    claims = [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="ambiguous_ring",
            property_key="interface.type",
            value="ring",
            source_url="https://example.test/attachment",
            extractor="test",
        )
    ]

    assert resolve_connection_interfaces(claims) == []


def test_nlg_explicit_d_ring_tether_point_resolves_as_provided_interface():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("The D Ring creates a secure tether point to attach a tool lanyard.")],
    )

    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 1
    assert interfaces[0].interface_id == "tether_side_ring"
    assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"


def test_nlg_inline_markup_preserves_d_ring_tether_point_evidence():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("<p>The <strong>D Ring</strong> creates a secure tether point.</p>")],
    )

    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 1
    assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"


def test_nlg_block_boundary_does_not_join_unrelated_ring_and_tether_point_copy():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("<p>D Ring construction</p><p>Creates a secure tether point.</p>")],
    )

    assert resolve_connection_interfaces(claims) == []


def test_nlg_pre_ring_negation_blocks_prohibited_lanyard_relation():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("<p>Do not use the D Ring to attach a tool lanyard.</p>")],
    )

    assert resolve_connection_interfaces(claims) == []


def test_nlg_pre_ring_permission_and_safety_prohibitions_block_interface_claims():
    prohibited = (
        "It is not permitted to use the D Ring to attach a tool lanyard.",
        "It is not allowed to use the D Ring to attach a tool lanyard.",
        "It is not safe to use the D Ring to attach a tool lanyard.",
    )

    for body in prohibited:
        claims = NLGAdapter().extract(
            ProductIdentity(
                manufacturer="NLG",
                product_type=ProductType.TOOL_ATTACHMENT,
                name="D Ring Attachment",
                sku="example",
                url="https://example.test/nlg/attachment",
            ),
            [artifact(f"<p>{body}</p>")],
        )

        assert resolve_connection_interfaces(claims) == [], body


def test_nlg_avoidance_prohibitions_block_interface_claims():
    prohibited = (
        "Avoid using the D Ring to attach a tool lanyard.",
        "Using the D Ring to attach a tool lanyard should be avoided.",
    )

    for body in prohibited:
        claims = NLGAdapter().extract(
            ProductIdentity(
                manufacturer="NLG",
                product_type=ProductType.TOOL_ATTACHMENT,
                name="D Ring Attachment",
                sku="example",
                url="https://example.test/nlg/attachment",
            ),
            [artifact(f"<p>{body}</p>")],
        )

        assert resolve_connection_interfaces(claims) == [], body


def test_nlg_avoidance_of_other_hazard_does_not_suppress_positive_ring_guidance():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("<p>Avoid snagging by using the D Ring to attach a tool lanyard.</p>")],
    )

    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 1
    assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"


def test_nlg_unrelated_pre_ring_negation_does_not_suppress_positive_relation():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Attachment",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("<p>This is not a disposable component; the D Ring creates a secure tether point.</p>")],
    )

    interfaces = resolve_connection_interfaces(claims)

    assert len(interfaces) == 1
    assert interfaces[0].role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"


def test_nlg_bare_d_ring_or_loop_evidence_does_not_invent_provided_interface():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="D Ring Loop Tool Tether",
            sku="example",
            url="https://example.test/nlg/attachment",
        ),
        [artifact("Climbing cord loop allows quick cinching. D Ring construction.")],
    )

    assert resolve_connection_interfaces(claims) == []


def test_tether_endpoint_claims_resolve_to_runtime_connection_interfaces():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TETHER,
            name="Retractable Tool Lanyard",
            sku="example",
            url="https://example.test/nlg/tether",
        ),
        [
            artifact(
                "Integral carabiner connects to the belt anchor while the Rotobiner provides tool attachment. "
                "Max Load: 3 kg."
            )
        ],
    )

    interfaces = resolve_connection_interfaces(claims)
    by_id = {interface.interface_id: interface for interface in interfaces}

    assert by_id["anchor_side"].role == ConnectionInterfaceRole.TETHER_CONNECTION
    assert by_id["anchor_side"].tether_side == TetherSide.ANCHOR_SIDE
    assert by_id["tool_side"].role == ConnectionInterfaceRole.TETHER_CONNECTION
    assert by_id["tool_side"].tether_side == TetherSide.TOOL_SIDE
    assert by_id["tool_side"].interface_type == "carabiner"
    assert by_id["tool_side"].connector_spec_ref == "tool_rotobiner"


def test_tool_side_endpoint_to_attachment_ring_is_unresolved_without_geometry():
    endpoint = ConnectionInterface(
        interface_id="tool_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.TOOL_SIDE,
        connector_spec_ref="rotobiner",
    )
    target = resolve_connection_interfaces(provided_ring_claims())[0]

    result = evaluate_endpoint_engagement(endpoint, target)

    assert result.status == ConnectionStatus.UNRESOLVED
    assert result.compatible is False
    assert "geometry" in result.reason


def test_anchor_side_only_endpoint_cannot_serve_tool_attachment_interface():
    endpoint = ConnectionInterface(
        interface_id="anchor_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.ANCHOR_SIDE,
    )
    target = resolve_connection_interfaces(provided_ring_claims())[0]

    result = evaluate_endpoint_engagement(endpoint, target)

    assert result.status == ConnectionStatus.INCOMPATIBLE
    assert "anchor-side-only" in result.reason


def test_connection_evaluation_is_identity_agnostic_for_equivalent_topology():
    target = resolve_connection_interfaces(provided_ring_claims())[0]
    first = ConnectionInterface(
        interface_id="brand_a_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.EITHER,
    )
    second = ConnectionInterface(
        interface_id="brand_b_endpoint",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=TetherSide.EITHER,
    )

    assert evaluate_endpoint_engagement(first, target).status == ConnectionStatus.UNRESOLVED
    assert evaluate_endpoint_engagement(second, target).status == ConnectionStatus.UNRESOLVED


def test_klein_nlg_attachment_tether_vertical_slice_stops_at_missing_engagement_geometry():
    tool_claims = KleinAdapter().extract(
        ProductIdentity(
            manufacturer="Klein Tools",
            product_type=ProductType.TOOL,
            name="Insulated Screwdriver",
            sku="6826INS",
            url="https://example.test/klein/6826ins",
        ),
        [artifact("The tether hole in the handle provides added safety when working at height.")],
    )
    features = resolve_tool_interface_features(tool_claims)

    attachment_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            name="360 D Ring Loop Tool Tether",
            sku="101363",
            url="https://example.test/nlg/101363",
        ),
        [
            artifact(
                "The D Ring creates a secure tether point to attach a tool lanyard. "
                "Create a tether point on any tool with a captive hole or handle and cinch it around the tool."
            )
        ],
    )
    eligibility = resolve_attachment_eligibility(attachment_claims)
    assert eligibility is not None
    assert evaluate_attachment_eligibility(eligibility, features).status == EligibilityStatus.ELIGIBLE

    attachment_interfaces = resolve_connection_interfaces(attachment_claims)
    assert len(attachment_interfaces) == 1
    attachment_interface = attachment_interfaces[0]
    assert attachment_interface.role == ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
    assert attachment_interface.interface_type == "ring"

    tether_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TETHER,
            name="Retractable Tool Lanyard",
            sku="example",
            url="https://example.test/nlg/tether",
        ),
        [artifact("Integral carabiner connects to the belt anchor while the Rotobiner provides tool attachment. Max Load: 3 kg.")],
    )

    tether_interfaces = resolve_connection_interfaces(tether_claims)
    tool_endpoint = next(
        interface for interface in tether_interfaces if interface.tether_side == TetherSide.TOOL_SIDE
    )

    engagement = evaluate_endpoint_engagement(tool_endpoint, attachment_interface)
    assert engagement.status == ConnectionStatus.UNRESOLVED
    assert engagement.reason == (
        "interface topology is plausible but no validated geometry rule proves engagement"
    )
