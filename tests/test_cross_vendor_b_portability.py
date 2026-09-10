from __future__ import annotations

from tetherlens_ingest.adapters import FallTechAdapter, GRIPPSAdapter
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    RuntimeVerificationStatus,
    TetherSide,
    evaluate_endpoint_engagement,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import resolve_connection_interfaces, resolve_connector_specs


GRIPPS_URL = "https://gripps.com/products/webbing-extra-heavy-duty-dual-action-tether"
FALLTECH_URL = "https://www.falltech.com/product/5027b/"


def _artifact(body: str, url: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _gripps_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Tether Heavy-Duty Dual-Action Carabiner - 36.3kg / 80lb",
        sku="H01079",
        url=GRIPPS_URL,
    )


def _gripps_body() -> str:
    return """
    <h1>Webbing Tether Heavy-Duty Dual-Action Carabiner - 36.3kg / 80lb</h1>
    <p>Engineered for exceptional performance, this tether has a load rating of up to
    36.9kg/81lbs and two heavy-duty carabiners.</p>
    <p>Featuring dual-action carabiners at both ends, this tether ensures secure attachment.</p>
    <div>Max Load: 36.3 kg | 80 lb</div>
    <p>NOTE: The GRIPPS Webbing Tether Extra Heavy-Duty Dual-Action has a dedicated
    Anchor end large carabiner and a dedicated Tool end, the small carabiner.</p>
    """


def _falltech_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.TETHER,
        name='15 lb Tool Tether with choke-on cinch-loop and steel carabiner, 36"',
        sku="5027B",
        url=FALLTECH_URL,
    )


def _falltech_body() -> str:
    return """
    <h1>15 lb Tool Tether with choke-on cinch-loop and steel carabiner, 36&quot;</h1>
    <div>Filter - Tool Weight Capacity: 15 lb max.</div>
    <div>Filter - Attachment Type: Choke-on Loop</div>
    <div>Features elastic choke-loop with nylon cord lock for a more secure attachment.</div>
    <div>Includes self-closing steel carabiner.</div>
    <h2>Similar Products to 5027B</h2>
    <div>15 lb Tool Tether with dual steel screwgate carabiners, 36&quot;</div>
    """


def test_gripps_keeps_conflicting_first_party_capacity_unreconciled() -> None:
    adapter = GRIPPSAdapter()
    claims = adapter.extract(
        _gripps_identity(),
        [_artifact(_gripps_body(), GRIPPS_URL)],
    )

    capacities = sorted(
        float(claim.value)
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.property_key == "rated_capacity_kg"
    )
    assert capacities == [36.3, 36.9]

    issues = adapter.readiness_issues(claims, [])
    assert issues is not None
    assert len(issues) == 1
    assert issues[0].code == "EVIDENCE_CONFLICT"
    assert issues[0].property_key == "rated_capacity_kg"
    assert "no value is recommendation-ready" in (issues[0].detail or "")


def test_gripps_explicit_direction_flows_into_existing_side_semantics_without_equivalence() -> None:
    claims = GRIPPSAdapter().extract(
        _gripps_identity(),
        [_artifact(_gripps_body(), GRIPPS_URL)],
    )

    assert not any(
        claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT
        for claim in claims
    )
    assert not any(claim.evidence_method == "derived_endpoint_equivalence" for claim in claims)

    interfaces = {interface.interface_id: interface for interface in resolve_connection_interfaces(claims)}
    specs = resolve_connector_specs(claims)
    anchor_endpoint = interfaces["anchor_side"]
    tool_endpoint = interfaces["tool_side"]

    assert anchor_endpoint.tether_side == TetherSide.ANCHOR_SIDE
    assert anchor_endpoint.connector_spec_ref == "anchor_carabiner"
    assert tool_endpoint.tether_side == TetherSide.TOOL_SIDE
    assert tool_endpoint.connector_spec_ref == "tool_carabiner"
    assert specs["anchor_carabiner"].opening_action_count == 2
    assert specs["anchor_carabiner"].attributes["relative_size"] == "large"
    assert specs["tool_carabiner"].opening_action_count == 2
    assert specs["tool_carabiner"].attributes["relative_size"] == "small"

    tool_target = ConnectionInterface(
        interface_id="tool_attachment_ring",
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )
    anchor_target = ConnectionInterface(
        interface_id="anchor_ring",
        role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        interface_type="ring",
    )

    tool_forward = evaluate_endpoint_engagement(
        tool_endpoint,
        tool_target,
        connector_specs=specs,
    )
    anchor_forward = evaluate_endpoint_engagement(
        anchor_endpoint,
        anchor_target,
        connector_specs=specs,
    )
    anchor_reversed = evaluate_endpoint_engagement(
        anchor_endpoint,
        tool_target,
        connector_specs=specs,
    )
    tool_reversed = evaluate_endpoint_engagement(
        tool_endpoint,
        anchor_target,
        connector_specs=specs,
    )

    assert tool_forward.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert anchor_forward.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert tool_forward.verification_family == "gated_connector_to_closed_interface.v1"
    assert anchor_forward.verification_family == "gated_connector_to_closed_interface.v1"
    assert anchor_reversed.status == ConnectionStatus.INCOMPATIBLE
    assert anchor_reversed.basis == CompatibilityBasis.VALIDATED_INTERFACE_CLASS
    assert anchor_reversed.rule_results[0].rule_id == "endpoint_side_semantics.v1"
    assert tool_reversed.status == ConnectionStatus.INCOMPATIBLE
    assert tool_reversed.basis == CompatibilityBasis.VALIDATED_INTERFACE_CLASS
    assert tool_reversed.rule_results[0].rule_id == "endpoint_side_semantics.v1"


def test_falltech_mixed_endpoints_resolve_into_existing_cinch_loop_family() -> None:
    claims = FallTechAdapter().extract(
        _falltech_identity(),
        [_artifact(_falltech_body(), FALLTECH_URL)],
    )

    capacity = next(claim for claim in claims if claim.property_key == "rated_capacity_kg")
    assert capacity.value == 6.803886
    assert not any(
        claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT
        for claim in claims
    )

    interfaces = {interface.interface_id: interface for interface in resolve_connection_interfaces(claims)}
    specs = resolve_connector_specs(claims)
    loop_endpoint = interfaces["cinch_loop_end"]
    carabiner_endpoint = interfaces["carabiner_end"]

    assert loop_endpoint.interface_type == "loop"
    assert loop_endpoint.tether_side == TetherSide.UNKNOWN
    assert loop_endpoint.connector_spec_ref == "cinch_loop"
    assert carabiner_endpoint.interface_type == "carabiner"
    assert carabiner_endpoint.tether_side == TetherSide.UNKNOWN
    assert carabiner_endpoint.connector_spec_ref == "steel_carabiner"
    assert specs["cinch_loop"].attributes["engagement_method"] == "cinch"
    assert specs["steel_carabiner"].attributes["material"] == "steel"

    tool_target = ConnectionInterface(
        interface_id="tool_captive_hole",
        role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        interface_type="captive_hole",
    )
    result = evaluate_endpoint_engagement(
        loop_endpoint,
        tool_target,
        connector_specs=specs,
    )

    assert result.status == ConnectionStatus.REQUIRES_VERIFICATION
    assert result.basis == CompatibilityBasis.RUNTIME_VERIFICATION
    assert result.verification_family == "cinch_loop_to_closed_interface.v1"
    assert result.verification_status == RuntimeVerificationStatus.PENDING
    assert result.verification_connector_spec == specs["cinch_loop"]


def test_falltech_related_product_copy_cannot_retype_current_product_heading() -> None:
    body = """
    <h1>15 lb Tool Tether with dual steel carabiners, 36&quot;</h1>
    <div>Filter - Tool Weight Capacity: 15 lb max.</div>
    <h2>Similar Products</h2>
    <div>15 lb Tool Tether with choke-on cinch-loop and steel carabiner, 36&quot;</div>
    """
    claims = FallTechAdapter().extract(
        _falltech_identity(),
        [_artifact(body, FALLTECH_URL)],
    )

    assert not any(
        claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
        for claim in claims
    )
    assert not any(claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC for claim in claims)
