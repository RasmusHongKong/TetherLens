from tetherlens_ingest.adapters.hilti_tool_attachment import HiltiAdapter
from tetherlens_ingest.declared_compatibility import (
    resolve_connector_interface_compatibility_declarations,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.tool_attachment_installation import (
    resolve_tool_attachment_installation_bindings,
)


TOOL_URL = "https://example.test/hilti-sf4-22"
MANUAL_A = "https://example.test/hilti-sf4-22-a.pdf"
MANUAL_B = "https://example.test/hilti-sf4-22-b.pdf"


def _tool_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL,
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        url=TOOL_URL,
    )


def _primary() -> SourceArtifact:
    return SourceArtifact(
        url=TOOL_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>",
    )


def _manual(body: str, url: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=body,
        metadata={"role": "operating_instruction"},
    )


def _complete_section(strap: str, tether: str) -> str:
    return (
        "SF 4-22 (02). Fall arrest. "
        "As drop arrester for this product, use only a combination of the Hilti "
        f"retaining strap #{strap} and the Hilti tool tether #{tether}. "
        "Secure the retaining strap to the installation openings for accessories. "
        "Secure one carabiner of the tool tether to the retaining strap and secure the "
        "second carabiner to a load-bearing structure."
    )


def _extract(*manuals: SourceArtifact):
    return HiltiAdapter().extract(_tool_identity(), [_primary(), *manuals])


def test_different_manual_pairings_resolve_as_independent_evidence_records():
    claims = _extract(
        _manual(_complete_section("2293133", "2261970"), MANUAL_A),
        _manual(_complete_section("2293134", "2261971"), MANUAL_B),
    )

    installation_refs = {
        claim.subject_ref
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH
    }
    declaration_refs = {
        claim.subject_ref
        for claim in claims
        if claim.subject_type == ClaimSubjectType.CONNECTION_COMPATIBILITY
    }
    assert installation_refs == {
        "retaining_strap_accessory_openings:2293133",
        "retaining_strap_accessory_openings:2293134",
    }
    assert declaration_refs == {
        "tool_tether_to_retaining_strap:2261970:2293133",
        "tool_tether_to_retaining_strap:2261971:2293134",
    }

    bindings = resolve_tool_attachment_installation_bindings(
        claims,
        tool_ref="Hilti:2253847",
        attachment_product_refs={
            "2293133": "Hilti:2293133",
            "2293134": "Hilti:2293134",
        },
    )
    assert {binding.source_product_ref for binding in bindings} == {
        "Hilti:2293133",
        "Hilti:2293134",
    }

    declarations = resolve_connector_interface_compatibility_declarations(
        claims,
        product_refs_by_identifier={
            "2261970": "Hilti:2261970",
            "2293133": "Hilti:2293133",
            "2261971": "Hilti:2261971",
            "2293134": "Hilti:2293134",
        },
    )
    assert {
        (declaration.source_product_ref, declaration.target_product_ref)
        for declaration in declarations
    } == {
        ("Hilti:2261970", "Hilti:2293133"),
        ("Hilti:2261971", "Hilti:2293134"),
    }


def test_same_pairing_from_two_manuals_merges_source_provenance():
    claims = _extract(
        _manual(_complete_section("2293133", "2261970"), MANUAL_B),
        _manual(_complete_section("2293133", "2261970"), MANUAL_A),
    )

    bindings = resolve_tool_attachment_installation_bindings(
        claims,
        tool_ref="Hilti:2253847",
        attachment_product_refs={"2293133": "Hilti:2293133"},
    )
    assert len(bindings) == 1
    assert bindings[0].source_urls == [MANUAL_A, MANUAL_B]

    declarations = resolve_connector_interface_compatibility_declarations(
        claims,
        product_refs_by_identifier={
            "2261970": "Hilti:2261970",
            "2293133": "Hilti:2293133",
        },
    )
    assert len(declarations) == 1
    assert declarations[0].source_urls == [MANUAL_A, MANUAL_B]


def test_incomplete_first_matching_model_section_does_not_hide_later_complete_section():
    body = (
        "SF 4-22 (02). Fall arrest. Contents entry without installation instructions. "
        + _complete_section("2293133", "2261970")
    )
    claims = _extract(_manual(body, MANUAL_A))

    required_attachments = {
        str(claim.value)
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.property_key == "tool.required_tool_attachment"
    }
    installation_refs = {
        claim.subject_ref
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH
    }
    assert required_attachments == {"2293133"}
    assert installation_refs == {"retaining_strap_accessory_openings:2293133"}


def test_two_complete_matching_sections_in_one_manual_both_survive():
    body = (
        _complete_section("2293133", "2261970")
        + " "
        + _complete_section("2293134", "2261971")
    )
    claims = _extract(_manual(body, MANUAL_A))

    installation_refs = {
        claim.subject_ref
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH
    }
    assert installation_refs == {
        "retaining_strap_accessory_openings:2293133",
        "retaining_strap_accessory_openings:2293134",
    }