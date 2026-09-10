from __future__ import annotations

from tetherlens_ingest.adapters import TyFlotAdapter
from tetherlens_ingest.models import (
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


PRODUCT_URL = "https://guardianfall.com/product/cold-shrink-series/COLDSH41X35"
GUIDE_INDEX_URL = "https://guardianfall.com/media/catalog/dropped-object-prevention-product-guide"
TRUSTED_GUIDE_URL = "https://guardianfall.com/assets/current-dop-guide"
EXTERNAL_GUIDE_URL = "https://example.test/copied-dop-guide.pdf"


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Ty-Flot",
        product_type=ProductType.TOOL_ATTACHMENT,
        name='Cold Shrink Attachment, 4.1 in by 3.5 in',
        sku="COLDSH41X35",
        url=PRODUCT_URL,
    )


def _guide_body() -> str:
    return (
        'Cold Shrink Part Numbers Description Fits Diameter Rating Qty '
        'COLDSH41X35 Cold Shrink Attachment, 4.1" X 3.5" '
        '1.65" to 3.50" up to 10 lb 5'
    )


def test_tyflot_guide_discovery_ignores_external_links() -> None:
    artifact = SourceArtifact(
        url=GUIDE_INDEX_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=(
            f'<a href="{EXTERNAL_GUIDE_URL}">Download PDF Version</a>'
            f'<a href="{TRUSTED_GUIDE_URL}">Download PDF Version</a>'
        ),
        metadata={"role": "dop_product_guide_index"},
    )

    requests = TyFlotAdapter().related_sources(_identity(), artifact)

    assert [request.url for request in requests] == [TRUSTED_GUIDE_URL]


def test_tyflot_rejects_guide_that_redirects_to_external_host() -> None:
    artifact = SourceArtifact(
        url=EXTERNAL_GUIDE_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=_guide_body(),
        metadata={"role": "dop_product_guide"},
    )

    claims = TyFlotAdapter().extract(_identity(), [artifact])

    assert claims == []


def test_tyflot_rejects_primary_artifact_that_redirects_off_manufacturer_host() -> None:
    artifact = SourceArtifact(
        url="https://example.test/copied-product-page",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=(
            "<h1>Cold Shrink Series</h1>"
            "<p>The durable shrink tubing will collapse onto the tool, fixing it in place.</p>"
            "<p>Max Tool Weight: 10 lb</p>"
        ),
    )

    adapter = TyFlotAdapter()

    assert adapter.related_sources(_identity(), artifact) == []
    assert adapter.extract(_identity(), [artifact]) == []
