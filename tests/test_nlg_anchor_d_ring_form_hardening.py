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
    prohibited = (
        "Attaching a tool lanyard to the D Ring should be avoided.",
        "Attach a tool lanyard to the D Ring; this must be prohibited.",
    )
    for body in prohibited:
        assert anchor_d_ring_claims(body) == [], body
