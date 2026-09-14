import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter, FallTechAdapter, MilwaukeeAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.normalize import mass_to_kg
from tetherlens_ingest.runner import IngestionRunner


class SingleArtifactFetcher:
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


def test_falltech_anchor_capacity_requires_tool_weight_capacity_label():
    identity = ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Waist Belt Cinch Anchor Attachment",
        sku="5424A10",
        url="https://www.falltech.com/product/5424a10/",
    )
    claims = FallTechAdapter().extract(
        identity,
        [
            _artifact(
                identity.url,
                "<h1>Waist Belt Cinch Anchor Attachment</h1>"
                "<p>SKU: 5424A10</p>"
                "<p>Worker capacity: 310 lb max.</p>"
                "<p>Its simple choke-on installation provides a secure setup.</p>"
                "<p>Fits most full body harness belts.</p>"
                "<p>Steel D-ring provides secure connection point for tool tether.</p>"
                "<p>Filter - Tool Weight Capacity: 5 lb max.</p>",
            )
        ],
    )

    capacities = [
        claim for claim in claims if claim.property_key == "rated_capacity_kg"
    ]
    assert len(capacities) == 1
    assert capacities[0].value == pytest.approx(mass_to_kg(5, "lb"))
    assert "5 lb" in (capacities[0].raw_value or "")
    assert "310" not in (capacities[0].raw_value or "")


def test_partial_milwaukee_anchor_does_not_run_tool_mass_readiness_checks():
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="50lbs Anchor Strap",
        sku="48-22-8855",
        url=(
            "https://www.milwaukeetool.com/products/details/"
            "50lbs-anchor-strap/48-22-8855"
        ),
    )
    artifact = _artifact(
        identity.url,
        "<h1>50lbs Anchor Strap 48-22-8855</h1>"
        "<p>The anchor strap features an oversized D-Ring that holds 5 carabiners.</p>"
        "<p>The attachment secures to supported structures.</p>"
        "<p>The lanyard has a maximum working capacity of 50 pounds.</p>",
    )

    result = IngestionRunner(SingleArtifactFetcher(artifact)).ingest(
        identity,
        MilwaukeeAdapter(),
    )

    assert any(
        claim.property_key == "interface.role"
        and claim.value == "anchor_attachment_tether_side"
        for claim in result.claims
    )
    assert not any(
        claim.property_key == "anchor_installation.method"
        for claim in result.claims
    )
    assert result.readiness_assessed is False
    assert result.issues == []


def test_evidence_free_milwaukee_anchor_does_not_run_tool_mass_readiness_checks():
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="50lbs Anchor Strap",
        sku="48-22-8855",
        url=(
            "https://www.milwaukeetool.com/products/details/"
            "50lbs-anchor-strap/48-22-8855"
        ),
    )
    artifact = _artifact(
        identity.url,
        "<h1>50lbs Anchor Strap 48-22-8855</h1>"
        "<p>Manufacturer copy changed and no currently recognized anchor wording remains.</p>",
    )

    result = IngestionRunner(SingleArtifactFetcher(artifact)).ingest(
        identity,
        MilwaukeeAdapter(),
    )

    assert result.claims == []
    assert result.readiness_assessed is False
    assert result.issues == []


def test_milwaukee_anchor_capacity_accepts_kgs_unit():
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="50lbs Anchor Strap",
        sku="48-22-8855",
        url=(
            "https://www.milwaukeetool.com/products/details/"
            "50lbs-anchor-strap/48-22-8855"
        ),
    )
    claims = MilwaukeeAdapter().extract(
        identity,
        [
            _artifact(
                identity.url,
                "<h1>50lbs Anchor Strap 48-22-8855</h1>"
                "<p>22 kgs weight rating.</p>",
            )
        ],
    )

    capacities = [
        claim for claim in claims if claim.property_key == "rated_capacity_kg"
    ]
    assert len(capacities) == 1
    assert capacities[0].value == pytest.approx(22.0)


def test_ergodyne_anchor_capacity_accepts_kgs_unit():
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3171 Anchor Strap Belt Loop Attachment",
        model="3171",
        sku="19171",
        url=(
            "https://www.ergodyne.com/"
            "squids-3171-anchor-strap-belt-loop-attachment-tool-tethering-5-lbs-2.3-kg"
        ),
    )
    claims = ErgodyneAdapter().extract(
        identity,
        [
            _artifact(
                identity.url,
                "<h1>Squids 3171 Anchor Strap Belt Loop Attachment</h1>"
                "<p>Item #: 19171</p>"
                "<p>2.3 kgs maximum working capacity.</p>",
            )
        ],
    )

    capacities = [
        claim for claim in claims if claim.property_key == "rated_capacity_kg"
    ]
    assert len(capacities) == 1
    assert capacities[0].value == pytest.approx(2.3)
