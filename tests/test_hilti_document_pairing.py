from tetherlens_ingest.adapters.hilti_tool_attachment import HiltiAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def _tool_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        product_type=ProductType.TOOL,
        url="https://www.hilti.com/c/CLS_POWER_TOOLS_7125/CLS_DRILL_DRIVERS_SCREW_DRIVERS__7125/r13275669",
        manufacturer_ids={"technical_family": "r13275669"},
    )


def _artifact(
    body: str,
    *,
    role: str | None = None,
    source_type=SourceType.MANUFACTURER_WEBPAGE,
    url=None,
    metadata_extra: dict | None = None,
):
    metadata = {"role": role} if role else {}
    metadata.update(metadata_extra or {})
    return SourceArtifact(
        url=url or _tool_identity().url,
        source_type=source_type,
        content_type="application/pdf" if source_type == SourceType.MANUFACTURER_DOCUMENT else "text/html",
        body=body,
        metadata=metadata,
    )


def test_hilti_tool_uses_model_driven_technical_library_query():
    primary = _artifact("<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>")
    requests = HiltiAdapter().related_sources(_tool_identity(), primary)
    document_indexes = [request for request in requests if request.metadata.get("role") == "document_index"]
    assert len(document_indexes) == 1
    assert document_indexes[0].url == "https://www.hilti.com/technical-library?search=true&text=SF+4-22"
    assert document_indexes[0].metadata["document_query"] == "SF 4-22"


def test_hilti_technical_library_discovers_matching_operating_instruction():
    index = _artifact(
        """
        <article><h3>Operating Instruction SF 4-22 (02), SF 4H-22 (02)</h3>
        <div>Operating Instruction</div>
        <a href="https://productdata.hilti.com/APQ_HC_RAW/PUB_1234567_000.pdf">Download</a></article>
        """,
        role="document_index",
        url="https://www.hilti.com/technical-library?search=true&text=SF+4-22",
    )
    requests = HiltiAdapter().related_sources(_tool_identity(), index)
    manuals = [request for request in requests if request.metadata.get("role") == "operating_instruction"]
    assert len(manuals) == 1
    assert manuals[0].source_type == SourceType.MANUFACTURER_DOCUMENT
    assert manuals[0].url.endswith("PUB_1234567_000.pdf")
    assert manuals[0].metadata["relationship_basis"] == "technical_library_result"


def test_hilti_pdf_annotation_document_id_discovers_us_online_operating_instruction():
    manual = _artifact(
        "SF 4-22 (02), SF 4H-22 (02) Original operating instructions",
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        url="https://productdata.hilti.com/APQ_HC_RAW/PUB_5664433_000.pdf",
        metadata_extra={
            "document_links": ["https://qr.hilti.com/manual?id=2272252&id=2272254"],
        },
    )
    requests = HiltiAdapter().related_sources(_tool_identity(), manual)
    assert len(requests) == 1
    online = requests[0]
    assert online.url == "https://www.hilti.com/content/hilti/W1/US/en/op-man.html/2272254/en"
    assert online.metadata["role"] == "online_operating_instruction"
    assert online.metadata["document_id"] == "2272254"
    assert online.metadata["relationship_basis"] == "embedded_document_id"


def test_hilti_pdf_text_document_id_remains_a_supported_fallback():
    manual = _artifact(
        """
        SF 4-22 (02), SF 4H-22 (02)
        More information: https://qr.hilti.com/manual?id=2272252&id=2272254
        """,
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    assert HiltiAdapter().related_sources(_tool_identity(), manual)[0].metadata["document_id"] == "2272254"


def test_hilti_pdf_document_join_requires_manual_to_match_tool_model():
    manual = _artifact(
        "SID 6-22 (01)",
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        metadata_extra={
            "document_links": ["https://qr.hilti.com/manual?id=2272252&id=2272254"],
        },
    )
    assert HiltiAdapter().related_sources(_tool_identity(), manual) == []


def test_hilti_operating_instruction_extracts_required_drop_arrest_pairing_without_polluting_tool_identity():
    primary = _artifact("<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div><div>Tool body weight: 2.9 lb</div>")
    manual = _artifact(
        """
        SF 4-22 (02), SF 4H-22 (02)
        Original operating instructions
        As drop arrester for this product, use only a combination of the Hilti retaining strap #2293133
        and the Hilti tool tether #2261970.
        """,
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        url="https://productdata.hilti.com/APQ_HC_RAW/PUB_1234567_000.pdf",
    )
    claims = HiltiAdapter().extract(_tool_identity(), [primary, manual])
    by_key = {claim.property_key: claim for claim in claims}
    assert by_key["manufacturer_item_code"].value == "2253847"
    assert by_key["tool.required_tool_attachment"].value == "2293133"
    assert by_key["tool.required_tether"].value == "2261970"
    assert by_key["tool.required_tool_attachment"].evidence_method == "manufacturer_pairing"
    assert by_key["tool.required_tool_attachment"].source_url == manual.url
    assert not any(claim.property_key == "manufacturer_item_code" and claim.value == "2293133" for claim in claims)


def test_hilti_online_operating_instruction_can_supply_exact_pairing():
    primary = _artifact("<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>")
    online_manual = _artifact(
        """
        <main>
        <h1>Operating Instruction SF 4-22 (02), SF 4H-22 (02)</h1>
        <p>As drop arrester for this product, use only a combination of the Hilti retaining strap #2293133
        and the Hilti tool tether #2261970.</p>
        </main>
        """,
        role="online_operating_instruction",
        url="https://www.hilti.com/content/hilti/W1/US/en/op-man.html/2272254/en",
    )
    claims = HiltiAdapter().extract(_tool_identity(), [primary, online_manual])
    by_key = {claim.property_key: claim for claim in claims}
    assert by_key["tool.required_tool_attachment"].value == "2293133"
    assert by_key["tool.required_tether"].value == "2261970"
    assert by_key["tool.required_tool_attachment"].source_url == online_manual.url


def test_hilti_operating_instruction_keeps_partial_pairing_when_strap_sku_is_absent():
    primary = _artifact("<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>")
    manual = _artifact(
        """
        Front matter that can be arbitrarily long. SF 4-22 (02), SF 4H-22 (02).
        As drop arrester for this product, use only a combination of the Hilti retaining strap
        and the Hilti tool tether #2261970.
        """,
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    claims = HiltiAdapter().extract(_tool_identity(), [primary, manual])
    by_key = {claim.property_key: claim for claim in claims}
    assert "tool.required_tool_attachment" not in by_key
    assert by_key["tool.required_tether"].value == "2261970"


def test_hilti_pairing_requires_manual_to_match_tool_model():
    primary = _artifact("<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>")
    wrong_manual = _artifact(
        """
        SID 6-22 (01)
        As drop arrester for this product, use only a combination of the Hilti retaining strap #2293133
        and the Hilti tool tether #2261970.
        """,
        role="operating_instruction",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        url="https://productdata.hilti.com/APQ_HC_RAW/PUB_wrong.pdf",
    )
    claims = HiltiAdapter().extract(_tool_identity(), [primary, wrong_manual])
    assert not any(claim.property_key.startswith("tool.required_") for claim in claims)
