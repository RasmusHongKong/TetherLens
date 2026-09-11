from tetherlens_ingest.adapters import ThreeMAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url="https://www.3m.com/3M/en_LB/p/d/v100323604/",
    )


def _artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url=(
            "https://multimedia.3m.com/mws/media/1300988O/"
            "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
        ),
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=body,
    )


def test_taper_prohibition_alone_does_not_invent_a_provided_attachment_interface() -> None:
    claims = ThreeMAdapter().extract(
        _identity(),
        [_artifact("Never attach tool lanyards or attachment points to a tapered surface.")],
    )

    assert any(
        claim.property_key == "prohibited_surface_profile" and claim.value == "tapered"
        for claim in claims
    )
    assert not any(claim.property_key == "interface.role" for claim in claims)


def test_affirmative_non_metallic_attachment_point_can_supply_interface_role_without_form() -> None:
    claims = ThreeMAdapter().extract(
        _identity(),
        [_artifact("A non-metallic attachment point is needed.")],
    )

    role_claims = [claim for claim in claims if claim.property_key == "interface.role"]
    assert len(role_claims) == 1
    assert role_claims[0].value == "tool_attachment_tether_side"
    assert not any(claim.property_key == "interface.type" for claim in claims)
