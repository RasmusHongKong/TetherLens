from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentBasis,
    EndpointAssignmentSemantics,
    resolve_tether_endpoint_assignment_declarations,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.runner import IngestionRunner


PAGE_URL = "https://neverletgo.com/products/go-bungee-tool-lanyard-twin/"
DATASHEET_URL = (
    "https://go.neverletgo.com/hubfs/Product/Datasheet/101519.pdf"
    "?2026-01-30T12%3A24%3A11.892Z="
)


class FakeFetcher:
    def __init__(self, *, page_html: str, datasheet_text: str):
        self.page_html = page_html
        self.datasheet_text = datasheet_text
        self.calls: list[tuple[str, SourceType]] = []

    def get(self, url, source_type=SourceType.MANUFACTURER_WEBPAGE):
        self.calls.append((url, source_type))
        if url == PAGE_URL:
            return SourceArtifact(
                url=url,
                source_type=source_type,
                content_type="text/html",
                body=self.page_html,
            )
        if url == DATASHEET_URL:
            return SourceArtifact(
                url=url,
                source_type=source_type,
                content_type="application/pdf",
                body=self.datasheet_text,
            )
        raise AssertionError(url)


def _identity(
    name: str = "GO Bungee Tool Lanyard, Twin Carabiner",
    sku: str = "101519",
    url: str = PAGE_URL,
) -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name=name,
        sku=sku,
        url=url,
    )


def _primary(body: str, *, url: str = PAGE_URL) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _assignment_claims(claims):
    return [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT
    ]


def test_nlg_source_graph_fetches_first_party_datasheet_only_for_dual_carabiner_assignment_gap():
    page_html = f"""
    <h1>GO Bungee Tool Lanyard, Twin Carabiner</h1>
    <p>
      It comes with dual sturdy double-action carabiners so that it can attach easily
      to all common hand tools.
    </p>
    <div class="downloads">
      <a href="{DATASHEET_URL}">Datasheet</a>
      <a href="https://go.neverletgo.com/hubfs/Product/Instructions/101519.pdf">Product Instructions</a>
    </div>
    """
    datasheet_text = """
    NLG GO Bungee Tool Lanyard, Twin Carabiner
    The dual double-action carabiners allow for easy yet secure attachment to your tool
    and anchor point, whilst the low resistance makes it comfortable for all-day use.
    """
    fetcher = FakeFetcher(page_html=page_html, datasheet_text=datasheet_text)

    result = IngestionRunner(fetcher).ingest(_identity(), NLGAdapter())

    assert fetcher.calls == [
        (PAGE_URL, SourceType.MANUFACTURER_WEBPAGE),
        (DATASHEET_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert len(result.artifacts) == 2
    assert result.artifacts[1].metadata == {
        "role": "product_datasheet",
        "relationship_basis": "first_party_product_download",
    }

    assignment_claims = _assignment_claims(result.claims)
    assert len(assignment_claims) == 6
    assert {claim.source_url for claim in assignment_claims} == {DATASHEET_URL}
    assert {claim.evidence_method for claim in assignment_claims} == {
        "derived_endpoint_equivalence"
    }

    declaration = resolve_tether_endpoint_assignment_declarations(
        assignment_claims,
        tether_ref="product:NLG:101519",
    )[0]
    assert declaration.endpoint_refs == ["connection_point_1", "connection_point_2"]
    assert declaration.semantics == EndpointAssignmentSemantics.REVERSIBLE_TOOL_ANCHOR_PAIR
    assert declaration.basis == EndpointAssignmentBasis.DERIVED_ENDPOINT_EQUIVALENCE
    assert declaration.issuer_manufacturer == "NLG"
    assert declaration.source_urls == [DATASHEET_URL]


def test_nlg_primary_page_alone_does_not_derive_twin_carabiner_reversibility():
    page_html = f"""
    <h1>GO Bungee Tool Lanyard, Twin Carabiner</h1>
    <p>
      It comes with dual sturdy double-action carabiners so that it can attach easily
      to all common hand tools.
    </p>
    <a href="{DATASHEET_URL}">Datasheet</a>
    """

    claims = NLGAdapter().extract(_identity(), [_primary(page_html)])

    assert _assignment_claims(claims) == []


def test_nlg_does_not_derive_carabiner_equivalence_from_multiplicity_and_pair_use_alone():
    body = """
    <h1>Example Twin Carabiner Tool Lanyard</h1>
    <p>Dual carabiners allow secure attachment to your tool and anchor point.</p>
    """

    claims = NLGAdapter().extract(
        _identity(name="Example Twin Carabiner Tool Lanyard", sku="example"),
        [_primary(body)],
    )

    assert _assignment_claims(claims) == []


def test_nlg_does_not_derive_carabiner_equivalence_when_first_party_copy_assigns_ends():
    body = """
    <h1>Example Twin Carabiner Tool Lanyard</h1>
    <p>
      Dual double-action carabiners allow secure attachment to your tool and anchor point.
      The tool-end carabiner is used on the tool and the anchor-end carabiner is used on
      the anchor.
    </p>
    """

    claims = NLGAdapter().extract(
        _identity(name="Example Twin Carabiner Tool Lanyard", sku="example"),
        [_primary(body)],
    )

    assert _assignment_claims(claims) == []


def test_nlg_directional_rotobiner_product_does_not_request_datasheet_or_gain_reversibility():
    url = "https://neverletgo.com/products/heavy-duty-retractable-lanyard-double-carabiner/"
    body = """
    <h1>Heavy Duty Retractable Lanyard, Double Carabiner</h1>
    <p>
      Integral carabiner for belt or anchor and 360° Rotobiner for tool attachment.
    </p>
    <a href="https://go.neverletgo.com/hubfs/Product/Datasheet/101756.pdf">Datasheet</a>
    """
    identity = _identity(
        name="Heavy Duty Retractable Lanyard, Double Carabiner",
        sku="101756",
        url=url,
    )
    artifact = _primary(body, url=url)
    adapter = NLGAdapter()

    assert adapter.related_sources(identity, artifact) == []
    assert _assignment_claims(adapter.extract(identity, [artifact])) == []


def test_nlg_datasheet_discovery_rejects_external_datasheet_links():
    body = """
    <h1>Example Twin Carabiner Tool Lanyard</h1>
    <p>Dual sturdy double-action carabiners for common hand tools.</p>
    <a href="https://example.test/untrusted.pdf">Datasheet</a>
    """
    identity = _identity(name="Example Twin Carabiner Tool Lanyard", sku="example")

    assert NLGAdapter().related_sources(identity, _primary(body)) == []
