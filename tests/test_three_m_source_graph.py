from tetherlens_ingest.adapters import ThreeMAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


PRODUCT_URL = "https://www.3m.com/3M/en_LB/p/d/v100323604/"
MANUAL_URL = (
    "https://multimedia.3m.com/mws/media/1300988O/"
    "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
)


class _FakeFetcher:
    def __init__(self, *, primary_body: str | None = None) -> None:
        self.requests: list[tuple[str, SourceType]] = []
        self.primary_body = primary_body or (
            "3M DBI-SALA Quick Spin Medium Size 1500028. "
            "3M Product Number 1500028. "
            "Quick Spin, 0.5 kg (1 lb.) capacity. "
            "Tangle-resistant spin top simply slides onto the handle of a tool."
        )

    def get(self, url: str, source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE):
        self.requests.append((url, source_type))
        if url == PRODUCT_URL:
            return SourceArtifact(
                url=url,
                source_type=source_type,
                content_type="text/html",
                body=self.primary_body,
            )
        if url == MANUAL_URL:
            return SourceArtifact(
                url=url,
                source_type=source_type,
                content_type="application/pdf",
                body=(
                    "Do not use if a snug fit on the tool cannot be secured. "
                    "Never attach tool lanyards or attachment points to a tapered surface. "
                    "A non-metallic attachment point is needed."
                ),
            )
        raise AssertionError(f"unexpected fetch: {url}")


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url=PRODUCT_URL,
    )


def test_quick_spin_ingestion_joins_first_party_manual_before_constraint_resolution() -> None:
    fetcher = _FakeFetcher()

    result = IngestionRunner(fetcher).ingest(_identity(), ThreeMAdapter())

    assert fetcher.requests == [
        (PRODUCT_URL, SourceType.MANUFACTURER_WEBPAGE),
        (MANUAL_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert [artifact.url for artifact in result.artifacts] == [PRODUCT_URL, MANUAL_URL]
    assert result.acquisition_observations == []

    claim_values = {(claim.property_key, claim.value) for claim in result.claims}
    assert ("attachment_selection_class", "handle_attachment") in claim_values
    assert ("attachment_method_code", "mechanical_capture") in claim_values
    assert ("rated_capacity_kg", 0.5) in claim_values
    assert ("secure_attachment_fit_required", True) in claim_values
    assert ("prohibited_surface_profile", "tapered") in claim_values


def test_quick_spin_does_not_join_manual_when_resolved_page_is_fallback_or_different_product() -> None:
    fetcher = _FakeFetcher(
        primary_body=(
            "3M Tool Fall Protection. Popular products include Quick Spin Medium Size 1500028. "
            "3M Product Number 1500030."
        )
    )

    result = IngestionRunner(fetcher).ingest(_identity(), ThreeMAdapter())

    assert fetcher.requests == [(PRODUCT_URL, SourceType.MANUFACTURER_WEBPAGE)]
    assert [artifact.url for artifact in result.artifacts] == [PRODUCT_URL]
    assert result.claims == []
