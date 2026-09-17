import pytest

from tetherlens_ingest.adapters import ThreeMAdapter
from tetherlens_ingest.attachment_method import resolve_tool_attachment_installation_method
from tetherlens_ingest.compatibility import (
    CaptiveState,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
)
from tetherlens_ingest.runner import IngestionRunner


PRODUCT_URL = "https://www.3m.com/3M/en_US/p/d/v100323824/"
MANUAL_URL = (
    "https://multimedia.3m.com/mws/media/1300990O/"
    "ifu-5903828-python-d-ring-cord-a3-a3-size-instructions-manual.pdf"
)


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA D-Ring Attachment with Cord",
        sku="1500009",
        url=PRODUCT_URL,
    )


def _primary() -> SourceArtifact:
    return SourceArtifact(
        url=PRODUCT_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=(
            "<html><body>"
            "<h1>3M DBI-SALA D-Ring Attachment with Cord 1500009, 10 EA/PACK</h1>"
            "<div>3M Product Number 1500009</div>"
            "<p>Provides workers an attachment point to secure tools and accessories.</p>"
            "</body></html>"
        ),
    )


def _manual() -> SourceArtifact:
    return SourceArtifact(
        url=MANUAL_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            "Installation and Use Instructions for Python Safety D-Ring Cord Attachment. "
            "Simply pass the loop end of a D-Ring Cord through a pre-drilled hole or closed "
            "handle to create an instant attachment point. On tools weighing up to 5 lbs "
            "(2.3 kg). Python Safety attachment points require the use of an appropriate "
            "Python Safety Lanyard, Tether or Retractor for safe connection. "
            "D-Ring Cord Attachment Installation, Closed Handle Tools. "
            "Pass the cord end of the D-Ring Cord through the handle of the tool. "
            "Pass the Ring side of the D-Ring Cord through the loop of the Cord. "
            "Pull tightly to cinch and create a secure connection. "
            "D-Ring Cord Attachment Installation, Tools with Pre-Drilled Holes. "
            "Pass the cord end of the D-Ring Cord through the pre-drilled hole in the tool. "
            "Pass the Ring side of the D-Ring Cord through the loop of the Cord. "
            "Pull tightly to cinch and create a secure connection. "
            "1500009 Load Rating 5lbs (2.3kg)."
        ),
    )


class _FakeFetcher:
    def __init__(
        self,
        *,
        primary: SourceArtifact | None = None,
        manual: SourceArtifact | None = None,
    ) -> None:
        self.primary = primary or _primary()
        self.manual = manual or _manual()
        self.requests: list[tuple[str, SourceType]] = []

    def get(self, url: str, source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE):
        self.requests.append((url, source_type))
        if url == PRODUCT_URL:
            return self.primary
        if url == MANUAL_URL:
            return self.manual
        raise AssertionError(f"unexpected fetch: {url}")


def test_d_ring_cord_ingestion_uses_existing_generic_tool_attachment_semantics() -> None:
    fetcher = _FakeFetcher()

    result = IngestionRunner(fetcher).ingest(_identity(), ThreeMAdapter())

    assert fetcher.requests == [
        (PRODUCT_URL, SourceType.MANUFACTURER_WEBPAGE),
        (MANUAL_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert result.acquisition_observations == []

    by_key = {}
    for claim in result.claims:
        by_key.setdefault(claim.property_key, []).append(claim)

    assert by_key["attachment_selection_class"][0].value == "captive_feature_attachment"
    assert by_key["attachment_method_code"][0].value == "cinch"
    assert by_key["rated_capacity_kg"][0].value == pytest.approx(2.3)
    assert by_key["rated_capacity_kg"][0].unit == "kg"

    eligibility = resolve_attachment_eligibility(result.claims)
    assert eligibility is not None
    assert [path.binding_name for path in eligibility.paths] == ["handle", "opening"]

    eligible = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="closed-handle",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="pre-drilled-hole",
                feature_kind=FeatureKind.THROUGH_OPENING,
                captive_state=CaptiveState.CAPTIVE,
            ),
        ],
    )
    assert eligible.status == EligibilityStatus.ELIGIBLE
    assert {
        (match.binding_name, match.feature_id)
        for match in eligible.matches
    } == {
        ("handle", "closed-handle"),
        ("opening", "pre-drilled-hole"),
    }

    method = resolve_tool_attachment_installation_method(
        result.claims,
        source_product_ref="3M:1500009",
    )
    assert method is not None
    assert method.attachment_method_code == "cinch"
    assert method.source_urls == [MANUAL_URL]

    interfaces = resolve_connection_interfaces(result.claims)
    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface.interface_id == "d_ring_tether_connection"
    assert interface.interface_type == "ring"
    assert interface.attributes == {"ring_form": "d_ring"}

    # The first-party family warning remains source evidence; it must not be promoted
    # here into a mixed-manufacturer hard exclusion or SKU-pair compatibility rule.
    assert set(by_key) == {
        "attachment_selection_class",
        "attachment_method_code",
        "rated_capacity_kg",
        "interface.role",
        "interface.type",
        "interface.attribute.ring_form",
    }
    assert not any(
        claim.property_key.startswith(("feature.dimension.", "interface.dimension."))
        for claim in result.claims
    )


def test_d_ring_cord_does_not_join_manual_from_unverified_aggregate_page() -> None:
    aggregate = SourceArtifact(
        url=PRODUCT_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=(
            "<html><body>"
            "<h1>3M Fall Protection for Tools</h1>"
            "<article><h2>D-Ring Attachment with Cord 1500009</h2>"
            "<div>3M Product Number 1500009</div></article>"
            "<article><h2>Quick Spin Medium 1500028</h2>"
            "<div>3M Product Number 1500028</div></article>"
            "</body></html>"
        ),
    )
    fetcher = _FakeFetcher(primary=aggregate)

    result = IngestionRunner(fetcher).ingest(_identity(), ThreeMAdapter())

    assert fetcher.requests == [(PRODUCT_URL, SourceType.MANUFACTURER_WEBPAGE)]
    assert result.claims == []


def test_d_ring_cord_rejects_manual_without_local_product_identity() -> None:
    manual = _manual().model_copy(
        update={"body": _manual().body.replace("1500009", "1500010")}
    )
    fetcher = _FakeFetcher(manual=manual)

    result = IngestionRunner(fetcher).ingest(_identity(), ThreeMAdapter())

    assert result.claims == []
