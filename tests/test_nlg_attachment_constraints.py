from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.models import (
    ClaimType,
    ConstraintOperator,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


def artifact(body: str, *, url: str = "https://example.test/product", source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=source_type,
        content_type="text/html" if source_type == SourceType.MANUFACTURER_WEBPAGE else "application/pdf",
        body=body,
    )


def identity(sku: str = "101691") -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        sku=sku,
        url="https://example.test/product",
    )


def claim_map(body: str, *, sku: str = "101691", source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE):
    claims = NLGAdapter().extract(identity(sku), [artifact(body, source_type=source_type)])
    return {(claim.property_key, str(claim.value)): claim for claim in claims}


def test_angle_grinder_bracket_requires_declared_tool_class_and_handle_geometry():
    body = (
        "The Angle Grinder Bracket is designed for standard angle grinders. "
        "Easy installation to the angle grinder's handle."
    )
    claims = claim_map(body)

    category = claims[("applicable_tool_category_code", "angle_grinder")]
    assert category.claim_type == ClaimType.DECLARED_CONSTRAINT
    assert category.constraint_operator == ConstraintOperator.REQUIRES

    feature = claims[("required_tool_feature_type", "handle")]
    assert feature.claim_type == ClaimType.DECLARED_CONSTRAINT
    assert feature.constraint_operator == ConstraintOperator.REQUIRES


def test_handle_geometry_does_not_create_angle_grinder_scope_by_itself():
    claims = claim_map("The bracket attaches to the tool by the side handle.")
    assert ("required_tool_feature_type", "handle") in claims
    assert not any(key[0] == "applicable_tool_category_code" for key in claims)


def test_bare_angle_grinder_product_title_does_not_create_declared_scope():
    claims = claim_map("Related products: Angle Grinder Bracket")
    assert not any(key[0] == "applicable_tool_category_code" for key in claims)


def test_negated_angle_grinder_applicability_is_not_emitted():
    claims = claim_map("This attachment is not suitable for angle grinders.")
    assert not any(key[0] == "applicable_tool_category_code" for key in claims)


def test_negated_curved_surface_capability_is_not_emitted():
    claims = claim_map("This attachment is not for curved surfaces.", sku="101481")
    assert not any(key[0] == "supported_surface_profile" for key in claims)


def test_negated_flat_surface_instruction_is_not_emitted_as_requirement():
    claims = claim_map(
        "Do not attach the D Ring to a flat surface.",
        sku="101481",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    assert not any(key[0] == "installation_surface_profile" for key in claims)


def test_adhesive_instructions_emit_atomic_installation_constraints():
    body = """
    Attach the D Ring to a flat surface on the tool. The surface must be clean and grease-free.
    Do not attach the tether point to a battery compartment door as it can come off the tool.
    Allow 24 hours for the adhesive to fully bond before use. Test the tether point before use.
    """
    claims = claim_map(body, sku="101481", source_type=SourceType.MANUFACTURER_DOCUMENT)

    expected = {
        ("installation_surface_profile", "flat", ConstraintOperator.REQUIRES),
        ("required_surface_condition", "clean", ConstraintOperator.REQUIRES),
        ("required_surface_condition", "grease_free", ConstraintOperator.REQUIRES),
        ("prohibited_tool_part_type", "removable_cover_or_door", ConstraintOperator.PROHIBITS),
        ("minimum_bond_time_h", "24.0", ConstraintOperator.GTE),
        ("pre_use_attachment_test_required", "True", ConstraintOperator.REQUIRES),
    }
    actual = {
        (claim.property_key, str(claim.value), claim.constraint_operator)
        for claim in claims.values()
        if claim.claim_type == ClaimType.DECLARED_CONSTRAINT
    }
    assert expected <= actual


def test_neutral_removable_part_mention_does_not_create_prohibition():
    claims = claim_map(
        "The tool has a removable battery cover for servicing.",
        sku="101481",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    assert not any(key[0] == "prohibited_tool_part_type" for key in claims)


def test_explicit_removable_part_prohibition_is_preserved():
    claims = claim_map(
        "Do not attach the tether point to a removable battery cover.",
        sku="101481",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    prohibited = claims[("prohibited_tool_part_type", "removable_cover_or_door")]
    assert prohibited.claim_type == ClaimType.DECLARED_CONSTRAINT
    assert prohibited.constraint_operator == ConstraintOperator.PROHIBITS


def test_curved_surface_capability_remains_distinct_from_flat_installation_requirement():
    primary = artifact("Creates a tether point even on curved surfaces.")
    instructions = artifact(
        "Attach the D Ring to a flat surface on the tool.",
        url="https://go.neverletgo.com/hubfs/Product/Instructions/101481.pdf",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    claims = NLGAdapter().extract(identity("101481"), [primary, instructions])

    curved = next(c for c in claims if c.property_key == "supported_surface_profile")
    assert curved.value == "curved"
    assert curved.claim_type == ClaimType.DIRECT
    assert curved.constraint_operator is None

    flat = next(c for c in claims if c.property_key == "installation_surface_profile")
    assert flat.value == "flat"
    assert flat.claim_type == ClaimType.DECLARED_CONSTRAINT
    assert flat.constraint_operator == ConstraintOperator.REQUIRES


def test_nlg_discovers_product_instruction_document_from_page_link_without_duplicate_fallback():
    body = """
    <html><body>
      <a href="https://go.neverletgo.com/hubfs/Product/Instructions/101481.pdf?cache=1">Product Instructions</a>
    </body></html>
    """
    requests = NLGAdapter().related_sources(identity("101481"), artifact(body))

    instruction_requests = [request for request in requests if request.metadata.get("role") == "product_instructions"]
    assert len(instruction_requests) == 1
    assert instruction_requests[0].source_type == SourceType.MANUFACTURER_DOCUMENT
    assert instruction_requests[0].metadata.get("relationship_basis") == "page_link"
    assert instruction_requests[0].url.endswith("/Product/Instructions/101481.pdf?cache=1")


def test_nlg_adds_generic_sku_instruction_path_fallback():
    requests = NLGAdapter().related_sources(identity("101481"), artifact("<html></html>"))
    assert any(
        request.url == "https://go.neverletgo.com/hubfs/Product/Instructions/101481.pdf"
        and request.metadata.get("relationship_basis") == "manufacturer_sku_path"
        for request in requests
    )
