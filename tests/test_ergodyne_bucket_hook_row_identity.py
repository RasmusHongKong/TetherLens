from __future__ import annotations

import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


PRODUCT_URL = "https://www.ergodyne.com/squids-3178-locking-aerial-bucket-hook-tethering-point"
INSTRUCTIONS_URL = (
    "https://www.ergodyne.com/sites/default/files/2022-11/"
    "squids-3178-locking-bucket-hook-instructions.pdf"
)


class MappingFetcher:
    def __init__(self, artifacts: dict[str, SourceArtifact]):
        self.artifacts = artifacts

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        artifact = self.artifacts[url]
        return artifact.model_copy(deep=True, update={"source_type": source_type})


def _artifact(
    url: str,
    body: str,
    *,
    source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=source_type,
        content_type="application/pdf" if source_type == SourceType.MANUFACTURER_DOCUMENT else "text/html",
        body=body,
    )


def _primary() -> SourceArtifact:
    return _artifact(
        PRODUCT_URL,
        "<h1>Squids 3178 Locking Aerial Bucket Hook Tethering Point</h1>"
        "<p>Item #: 19178</p>"
        "<p>Item #: 19278</p>"
        "<p>Item #: 19179</p>"
        "<p>Item #: 19279</p>"
        "<p>Self-locking exterior hook with enclosed tethering point.</p>",
    )


def _instructions() -> SourceArtifact:
    return _artifact(
        INSTRUCTIONS_URL,
        "PRIMARY ANCHOR: lip of the aerial bucket\n"
        "ANCHOR ATTACHMENT (HOOK ITEM): 19178\n"
        "LIP CAVITY OF HOOK (BUCKET LIP SIZE) 2IN // 5CM\n"
        "STATIC CAPACITY FOR INTERIOR & EXTERIOR HOOKS 40LBS // 18KG\n"
        "DYNAMIC TETHER POINT CAPACITY 7LBS // 3.2KG\n"
        "MAXIMUM TETHER LENGTH 48IN // 122CM\n"
        "ANCHOR ATTACHMENT (HOOK ITEM): 19179\n"
        "LIP CAVITY OF HOOK (BUCKET LIP SIZE) 3IN // 7.6CM\n"
        "STATIC CAPACITY FOR INTERIOR & EXTERIOR HOOKS 40LBS // 18KG\n"
        "DYNAMIC TETHER POINT CAPACITY 7LBS // 3.2KG\n"
        "MAXIMUM TETHER LENGTH 48IN // 122CM\n"
        "Pry the hook over the lip of the bucket until it snaps into place on the bucket.",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )


def _ingest(sku: str):
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3178 Locking Aerial Bucket Hook Tethering Point",
        model="3178",
        sku=sku,
        url=PRODUCT_URL,
    )
    fetcher = MappingFetcher({PRODUCT_URL: _primary(), INSTRUCTIONS_URL: _instructions()})
    result = IngestionRunner(fetcher).ingest(identity, ErgodyneAdapter())
    rule = resolve_anchor_attachment_installation_rule(
        result.claims,
        source_product_ref=f"Ergodyne:{sku}",
    )
    return result, rule


@pytest.mark.parametrize(
    ("sku", "expected_nominal_size"),
    [("19178", "2_in"), ("19179", "3_in")],
)
def test_bucket_hook_selection_grid_uses_requested_item_row(
    sku: str,
    expected_nominal_size: str,
) -> None:
    result, rule = _ingest(sku)

    assert rule is not None
    assert [path.binding_name for path in rule.paths] == ["bucket_lip"]
    predicates = {
        predicate.property_key: predicate.value
        for predicate in rule.paths[0].requirements
    }
    assert predicates == {
        "feature_kind": "bucket_lip",
        "attribute:nominal_lip_size": expected_nominal_size,
    }
    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in result.claims
    )


@pytest.mark.parametrize("sku", ["19278", "19279"])
def test_bucket_hook_pack_sku_does_not_inherit_single_hook_instruction_row(sku: str) -> None:
    _, rule = _ingest(sku)

    assert rule is None
