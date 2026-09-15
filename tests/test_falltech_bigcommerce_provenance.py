from __future__ import annotations

from tetherlens_ingest.adapters import FallTechAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType


FALLTECH_DOCUMENT_NAMESPACE = (
    "https://cdn11.bigcommerce.com/s-1wxw1202sk/content/product_documents/"
)


def _falltech_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Wrist Attachment Anchor",
        sku="5331A1",
        url="https://www.falltech.com/product/5331a1/",
    )


def test_falltech_bigcommerce_trust_accepts_store_scoped_product_documents() -> None:
    adapter = FallTechAdapter()
    identity = _falltech_identity()

    assert adapter.is_first_party_url(
        identity,
        FALLTECH_DOCUMENT_NAMESPACE + "instruction_manuals/ANOTHER_FALLTECH_MANUAL.pdf",
    )
    assert adapter.is_first_party_url(
        identity,
        FALLTECH_DOCUMENT_NAMESPACE + "declarations/FALLTECH_DECLARATION.pdf",
    )


def test_falltech_bigcommerce_trust_rejects_shared_cdn_outside_falltech_document_namespace() -> None:
    adapter = FallTechAdapter()
    identity = _falltech_identity()

    assert not adapter.is_first_party_url(
        identity,
        "https://cdn11.bigcommerce.com/s-anotherstore/content/product_documents/manual.pdf",
    )
    assert not adapter.is_first_party_url(
        identity,
        "https://cdn11.bigcommerce.com/s-1wxw1202sk/stencil/assets/manual.pdf",
    )
    assert not adapter.is_first_party_url(
        identity,
        "https://cdn11.bigcommerce.com.example/s-1wxw1202sk/content/product_documents/manual.pdf",
    )


def test_falltech_bigcommerce_trust_requires_falltech_identity() -> None:
    adapter = FallTechAdapter()
    other_identity = ProductIdentity(
        manufacturer="Other Manufacturer",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Other Anchor",
        sku="OTHER-1",
        url="https://www.example.com/product/other-1/",
    )

    assert not adapter.is_first_party_url(
        other_identity,
        FALLTECH_DOCUMENT_NAMESPACE + "instruction_manuals/manual.pdf",
    )
