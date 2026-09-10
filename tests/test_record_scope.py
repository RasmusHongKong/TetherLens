from __future__ import annotations

import re

from tetherlens_ingest.adapters import TyFlotAdapter
from tetherlens_ingest.adapters.common import bounded_record_for_identifier
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


GUIDE_URL = "https://guardianfall.com/assets/current-dop-guide"


def test_bounded_record_for_identifier_stops_before_next_record_marker() -> None:
    text = "SKU1 alpha 10 SKU2 beta 20"

    record = bounded_record_for_identifier(text, "SKU1", re.compile(r"\bSKU\d+\b", re.I))

    assert record == "SKU1 alpha 10 "
    assert bounded_record_for_identifier(text, "SKU3", r"\bSKU\d+\b") is None


def test_tyflot_guide_does_not_borrow_fields_from_next_sku_row() -> None:
    identity = ProductIdentity(
        manufacturer="Ty-Flot",
        product_type=ProductType.TOOL_ATTACHMENT,
        name='Cold Shrink Attachment, 4.1 in by 3.5 in',
        sku="COLDSH41X35",
        url="https://guardianfall.com/product/cold-shrink-series/COLDSH41X35",
    )
    guide = SourceArtifact(
        url=GUIDE_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            'Cold Shrink Part Numbers Description Fits Diameter Rating Qty '
            'COLDSH41X35 Cold Shrink Attachment, 4.1" X 3.5" '
            'COLDSH21X275 Cold Shrink Attachment, 2.1" X 2.75" '
            '1.00" to 1.65" up to 5 lb 5'
        ),
        metadata={"role": "dop_product_guide"},
    )

    claims = TyFlotAdapter().extract(identity, [guide])

    assert claims == []
