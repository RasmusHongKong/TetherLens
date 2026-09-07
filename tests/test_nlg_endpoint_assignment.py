from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentBasis,
    EndpointAssignmentSemantics,
    resolve_tether_endpoint_assignment_declarations,
)
from tetherlens_ingest.models import ClaimSubjectType, ClaimType, ProductIdentity, ProductType, SourceArtifact


URL = "https://neverletgo.com/products/extended-bungee-tool-lanyard"


def _artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url=URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _identity(name: str = "Extended Bungee Tool Lanyard") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name=name,
        sku="101434",
        url=URL,
    )


def _assignment_claims(body: str):
    claims = NLGAdapter().extract(_identity(), [_artifact(body)])
    return [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT
    ]


def test_nlg_derives_reversible_quick_clip_pair_from_equivalent_endpoints_and_pair_use():
    html = """
    <h1>Extended Bungee Tool Lanyard</h1>
    <div>
      The Extended Bungee Lanyard easily extends to 2m allowing heavier tools to be
      connected to anchor points, both on and off the user.
    </div>
    <div>
      Equipped with the 360° Quick Clip™ connectors at each end, the lanyard remains
      tangle-free. Dual Quick Clips™ provide effortless and secure attachment.
    </div>
    """

    claims = _assignment_claims(html)

    assert len(claims) == 6
    assert {claim.subject_ref for claim in claims} == {
        "endpoint_assignment:quick_clip_equivalent_pair"
    }
    assert {claim.evidence_method for claim in claims} == {
        "derived_endpoint_equivalence"
    }
    assert {claim.claim_type for claim in claims} == {ClaimType.DERIVED}

    declaration = resolve_tether_endpoint_assignment_declarations(
        claims,
        tether_ref="product:NLG:101434",
    )[0]
    assert declaration.endpoint_refs == ["connection_point_1", "connection_point_2"]
    assert declaration.semantics == EndpointAssignmentSemantics.REVERSIBLE_TOOL_ANCHOR_PAIR
    assert declaration.basis == EndpointAssignmentBasis.DERIVED_ENDPOINT_EQUIVALENCE
    assert declaration.issuer_manufacturer == "NLG"
    assert declaration.source_urls == [URL]


def test_nlg_does_not_derive_reversibility_from_dual_quick_clips_and_pair_use_alone():
    html = """
    <h1>Example Dual Quick Clip Tool Lanyard</h1>
    <div>Dual Quick Clips™ provide easy attachment to the tool and anchor point.</div>
    """

    assert _assignment_claims(html) == []


def test_nlg_does_not_derive_reversibility_from_equivalent_endpoints_without_pair_use():
    html = """
    <h1>Example Dual Quick Clip Tool Lanyard</h1>
    <div>Dual Quick Clips™.</div>
    <div>Quick Clip™ connectors at each end reduce tangles.</div>
    """

    assert _assignment_claims(html) == []


def test_nlg_does_not_treat_negated_tool_anchor_use_as_positive_assignment_evidence():
    html = """
    <h1>Example Dual Quick Clip Tool Lanyard</h1>
    <div>Dual Quick Clips™.</div>
    <div>Quick Clip™ connectors at each end reduce tangles.</div>
    <div>Never attach tools to anchor points using this lanyard.</div>
    """

    assert _assignment_claims(html) == []


def test_nlg_does_not_derive_reversibility_when_endpoint_labels_are_directional():
    html = """
    <h1>Example Dual Quick Clip Tool Lanyard</h1>
    <div>Tools are connected to anchor points using the lanyard.</div>
    <div>Quick Clip™ connectors at each end.</div>
    <div>Use the tool-end Quick Clip for the tool connection.</div>
    """

    assert _assignment_claims(html) == []


def test_nlg_does_not_derive_reversibility_from_separately_assigned_quick_clips():
    html = """
    <h1>Example Dual Quick Clip Tool Lanyard</h1>
    <div>Dual Quick Clips™.</div>
    <div>Quick Clip™ connectors at each end.</div>
    <div>Attach the red Quick Clip to the tool and the blue Quick Clip to the anchor point.</div>
    """

    assert _assignment_claims(html) == []


def test_nlg_101756_directional_double_carabiner_remains_a_negative_control():
    html = """
    <h1>Heavy Duty Retractable Lanyard, Double Carabiner</h1>
    <div>
      Integral carabiner for belt or anchor and 360° Rotobiner for tool attachment.
    </div>
    """
    claims = NLGAdapter().extract(
        _identity("Heavy Duty Retractable Lanyard, Double Carabiner"),
        [_artifact(html)],
    )

    assert not any(
        claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT
        for claim in claims
    )
    roles = {
        (claim.subject_ref, claim.value)
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
        and claim.property_key == "connection_point.role"
    }
    assert roles == {("anchor_side", "anchor_side"), ("tool_side", "tool_side")}


def test_nlg_does_not_generalize_derived_equivalence_to_dual_carabiners_yet():
    html = """
    <h1>Example Twin Carabiner Tool Lanyard</h1>
    <div>Tools are connected to anchor points using the lanyard.</div>
    <div>Twin carabiners at both ends.</div>
    """

    assert _assignment_claims(html) == []
