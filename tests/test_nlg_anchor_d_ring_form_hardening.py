from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


def anchor_d_ring_claims(body: str):
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.ANCHOR_ATTACHMENT,
            name="Generic Anchor",
            sku="not-a-rule-sku",
            url="https://example.test/anchor",
        ),
        [
            SourceArtifact(
                url="https://example.test/anchor",
                source_type=SourceType.MANUFACTURER_WEBPAGE,
                content_type="text/html",
                body=f"<p>{body}</p>",
            )
        ],
    )
    return [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
        and claim.subject_ref == "lanyard_anchor_d_ring"
    ]


def test_permission_and_safety_prohibitions_fail_closed():
    prohibited = (
        "It is not permitted to attach a tool lanyard to the D Ring.",
        "It is not allowed to attach a tool lanyard to the D Ring.",
        "It is not safe to attach a tool lanyard to the D Ring.",
    )
    for body in prohibited:
        assert anchor_d_ring_claims(body) == [], body


def test_trailing_avoidance_prohibition_fails_closed():
    assert (
        anchor_d_ring_claims(
            "Attaching a tool lanyard to the D Ring should be avoided."
        )
        == []
    )


def test_review_denied_and_external_d_ring_relations_fail_closed():
    prohibited = (
        "This anchor does not include a D Ring for lanyard attachment.",
        "This anchor doesn't include a D Ring for lanyard attachment.",
        "This anchor requires a D Ring for lanyard attachment.",
        "This anchor requires an accessory that includes a D Ring for lanyard attachment.",
        "You can't attach a tool lanyard to the D Ring.",
    )
    for body in prohibited:
        assert anchor_d_ring_claims(body) == [], body


def test_affirmative_provision_relations_remain_valid():
    positive = (
        "This anchor includes a D Ring for lanyard attachment.",
        "This anchor features a D Ring for secure lanyard attachment.",
        "This anchor requires no drilling and includes a D Ring for lanyard attachment.",
    )
    for body in positive:
        claims = anchor_d_ring_claims(body)
        assert {claim.property_key: claim.value for claim in claims} == {
            "interface.role": "anchor_attachment_tether_side",
            "interface.type": "ring",
            "interface.attribute.ring_form": "d_ring",
        }, body


def test_indefinite_external_d_ring_is_not_direct_use_evidence():
    assert anchor_d_ring_claims("Attach a tool lanyard to a D Ring.") == []
    assert anchor_d_ring_claims("Attach a tool lanyard to the D Ring.")
