from tetherlens_ingest.adapters import ThreeMAdapter
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


PRODUCT_URL = "https://www.3m.com/3M/en_LB/p/d/v100323604/"
MANUAL_URL = (
    "https://multimedia.3m.com/mws/media/1300988O/"
    "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
)


class _FakeFetcher:
    def __init__(self) -> None:
        self.requests: list[tuple[str, SourceType]] = []

    def get(self, url: str, source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE):
        self.requests.append((url, source_type))
        if url == PRODUCT_URL:
            return SourceArtifact(
                url=url,
                source_type=source_type,
                content_type="text/html",
                body=(
                    "Quick Spin, 0.5 kg (1 lb.) capacity. "
                    "Tangle-resistant spin top simply slides onto the handle of a tool."
                ),
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


def test_quick_spin_ingestion_joins_first_party_manual_before_constraint_resolution() -> None:
    identity = ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url=PRODUCT_URL,
    )
    fetcher = _FakeFetcher()

    result = IngestionRunner(fetcher).ingest(identity, ThreeMAdapter())

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
