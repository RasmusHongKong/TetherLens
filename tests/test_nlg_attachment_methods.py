from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType


def artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url="https://example.test/product",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        url="https://example.test/product",
    )


def method_value(body: str) -> str | None:
    claims = NLGAdapter().extract(identity(), [artifact(body)])
    claim = next((c for c in claims if c.property_key == "attachment_method_code"), None)
    return str(claim.value) if claim else None


def test_nlg_normalizes_adhesive_attachment():
    assert method_value("The D ring uses 3M adhesive technology to bond to the tool surface.") == "adhesive"


def test_nlg_does_not_treat_adhesive_free_tape_as_adhesive_attachment():
    assert method_value("This self-fusing tether tape is adhesive-free and wraps around the tool.") == "wrap"


def test_nlg_normalizes_handle_bracket_as_mechanical_capture():
    assert method_value("The rigid bracket attaches to the tool by the side handle.") == "mechanical_capture"


def test_nlg_normalizes_explicit_cinch_attachment():
    assert method_value("The loop is cinched around a captive handle or captive hole.") == "cinch"


def test_nlg_cinch_takes_precedence_over_secondary_tape_wrap():
    body = "The attachment cinches around the captive handle. Tether Tape is then wrapped around the free arm to secure it."
    assert method_value(body) == "cinch"


def test_nlg_normalizes_through_feature_with_explicit_closure():
    body = "Pass the loop through the captive hole, then tighten the threaded closure to secure the attachment."
    assert method_value(body) == "through_feature"


def test_nlg_normalizes_wrap_attachment():
    assert method_value("Wrap the tethering tape around the tool and attachment point.") == "wrap"


def test_nlg_does_not_emit_attachment_method_for_non_tool_attachment():
    ident = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        url="https://example.test/product",
    )
    claims = NLGAdapter().extract(ident, [artifact("The product uses adhesive technology.")])
    assert not any(c.property_key == "attachment_method_code" for c in claims)
