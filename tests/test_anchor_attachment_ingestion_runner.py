from __future__ import annotations

import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter, FallTechAdapter, MilwaukeeAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.anchor_installation import AnchorInstallationMethod
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


ERGODYNE_INSTRUCTIONS_URL = (
    "https://www.ergodyne.com/sites/default/files/2022-11/"
    "squids-3171-3172-3174-3176-3177-anchor-straps-instructions.pdf"
)


class MappingFetcher:
    def __init__(self, artifacts: dict[str, SourceArtifact]):
        self.artifacts = artifacts
        self.calls: list[tuple[str, SourceType]] = []

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        self.calls.append((url, source_type))
        artifact = self.artifacts[url]
        return artifact.model_copy(deep=True, update={"source_type": source_type})


def _artifact(
    url: str,
    body: str,
    *,
    source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=source_type,
        content_type=(
            "application/pdf"
            if source_type == SourceType.MANUFACTURER_DOCUMENT
            else "text/html"
        ),
        body=body,
    )


@pytest.mark.parametrize(
    ("identity", "adapter", "body", "expected_method", "expected_paths"),
    [
        (
            ProductIdentity(
                manufacturer="Milwaukee",
                product_type=ProductType.ANCHOR_ATTACHMENT,
                name="50lbs Anchor Strap",
                sku="48-22-8855",
                url=(
                    "https://www.milwaukeetool.com/products/details/"
                    "50lbs-anchor-strap/48-22-8855"
                ),
            ),
            MilwaukeeAdapter(),
            "<h1>50lbs Anchor Strap 48-22-8855</h1>"
            "<p>The anchor strap features an oversized D-Ring that holds 5 carabiners.</p>"
            "<p>The anchor strap's loop securely wraps around beams and rails for maximum productivity.</p>"
            "<p>The lanyard has a maximum working capacity of 50 pounds.</p>",
            AnchorInstallationMethod.WRAP,
            ["beam", "rail"],
        ),
        (
            ProductIdentity(
                manufacturer="FallTech",
                product_type=ProductType.ANCHOR_ATTACHMENT,
                name="Waist Belt Cinch Anchor Attachment",
                sku="5424A10",
                url="https://www.falltech.com/product/5424a10/",
            ),
            FallTechAdapter(),
            "<h1>Waist Belt Cinch Anchor Attachment</h1>"
            "<p>SKU: 5424A10</p>"
            "<p>Its simple choke-on installation provides a secure setup.</p>"
            "<p>Fits most full body harness belts and other small diameter anchorage locations.</p>"
            "<p>Steel D-ring provides secure connection point for tool tether.</p>"
            "<p>Filter - Tool Weight Capacity: 5 lb max.</p>",
            AnchorInstallationMethod.CINCH,
            ["belt"],
        ),
    ],
)
def test_single_page_anchor_products_cross_normal_ingestion_runner(
    identity,
    adapter,
    body,
    expected_method,
    expected_paths,
):
    fetcher = MappingFetcher({identity.url: _artifact(identity.url, body)})

    result = IngestionRunner(fetcher).ingest(identity, adapter)
    rule = resolve_anchor_attachment_installation_rule(
        result.claims,
        source_product_ref=f"{identity.manufacturer}:{identity.sku}",
    )

    assert fetcher.calls == [(identity.url, SourceType.MANUFACTURER_WEBPAGE)]
    assert rule is not None
    assert rule.installation_method == expected_method
    assert [path.binding_name for path in rule.paths] == expected_paths
    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in result.claims
    )


def test_ergodyne_3171_crosses_runner_first_party_document_join_and_generic_resolution():
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
    primary = _artifact(
        identity.url,
        "<h1>Squids 3171 Anchor Strap Belt Loop Attachment for Tool Tethering</h1>"
        "<p>Item #: 19171</p>"
        "<p>Durable steel D-ring for attaching tool lanyards.</p>"
        "<p>Third party certified to a 5lbs / 2.3kg maximum working capacity.</p>",
    )
    instructions = _artifact(
        ERGODYNE_INSTRUCTIONS_URL,
        "SELECTING AN ANCHOR ATTACHMENT\n"
        "3171 Belt loop Fall Protection Belts, Tool Belts 5lbs / 2.26kg 48in / 122cm "
        "3in / 7.6cm x 0.5in / 1.3cm\n"
        "3172 Hook & loop Fall Protection Belts, Tool Belts, Harness Webbing 5lbs / 2.26kg "
        "48in / 122cm 3in / 7.6cm x 0.5in / 1.3cm\n"
        "3171 BELT LOOP ANCHOR INSTRUCTIONS\n"
        "The fully enclosed Belt Loop Anchor Attachment must be threaded onto an open-ended "
        "Primary Anchor like a belt. The Primary Anchor must then be secured in a manner that "
        "does not allow the anchor to slide off.\n"
        "1. Undo the belt that is acting as the Primary Anchor\n"
        "2. Thread the belt through the loop of the Anchor Attachment\n"
        "3. Refasten and secure the belt\n"
        "4. Attach a tool lanyard to the d-ring\n"
        "3172 HOOK & LOOP ANCHOR INSTRUCTIONS\n"
        "Primary Anchor should not be taller than 99in and not thicker than 88in.",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    fetcher = MappingFetcher(
        {
            identity.url: primary,
            ERGODYNE_INSTRUCTIONS_URL: instructions,
        }
    )

    result = IngestionRunner(fetcher).ingest(identity, ErgodyneAdapter())
    rule = resolve_anchor_attachment_installation_rule(
        result.claims,
        source_product_ref="Ergodyne:19171",
    )

    assert fetcher.calls == [
        (identity.url, SourceType.MANUFACTURER_WEBPAGE),
        (ERGODYNE_INSTRUCTIONS_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert len(result.artifacts) == 2
    assert result.artifacts[1].metadata["role"] == "anchor_attachment_instructions"
    assert not result.acquisition_observations
    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.THREAD_OVER
    assert [path.binding_name for path in rule.paths] == ["belt"]

    predicates = {
        predicate.property_key: predicate.value
        for predicate in rule.paths[0].requirements
    }
    assert predicates["attribute:open_for_threading"] is True
    assert predicates["attribute:can_be_resecured"] is True
    assert predicates["dimension:section_height"] == pytest.approx(76.2)
    assert predicates["dimension:section_thickness"] == pytest.approx(12.7)
