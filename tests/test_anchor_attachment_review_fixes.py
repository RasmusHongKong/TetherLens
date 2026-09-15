from __future__ import annotations

from tetherlens_ingest.adapters import GRIPPSAdapter, KleinAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.anchor_installation import (
    AnchorInstallationMethod,
    PrimaryAnchorFeature,
    PrimaryAnchorFeatureKind,
    ResolvedPrimaryAnchor,
    resolve_anchor_installation_bindings,
)
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


class RedirectingFetcher:
    def __init__(self, requested_url: str, artifact: SourceArtifact):
        self.requested_url = requested_url
        self.artifact = artifact

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        assert url == self.requested_url
        return self.artifact.model_copy(deep=True, update={"source_type": source_type})


def _artifact(url: str, body: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_gripps_h01086_preserves_wrist_and_hand_rail_installation_paths() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Adjustable Wrist Anchor",
        sku="H01086",
        url="https://www.au.gripps.com/products/adjustable-wrist-anchor",
    )
    artifact = _artifact(
        identity.url,
        "<h1>Adjustable Wrist Anchor - 2.5kg / 5.5lb</h1>"
        "<p>SKU H01086</p>"
        "<p>A versatile wristband incorporates a built-in, load-rated tether anchor.</p>"
        "<p>Can be attached to hand rails or your wrist.</p>"
        "<p>Industrial-grade Velcro adjusts diameter to suit any wrist or rail size.</p>"
        "<p>Max Load: 2.5kg / 5.5lb</p>",
    )

    claims = GRIPPSAdapter().extract(identity, [artifact])
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="GRIPPS:H01086",
    )

    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.FASTEN_AROUND
    assert {path.binding_name for path in rule.paths} == {"wrist", "rail"}

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker-or-structure",
        features=[
            PrimaryAnchorFeature(
                feature_id="left-wrist",
                feature_kind=PrimaryAnchorFeatureKind.WRIST,
            ),
            PrimaryAnchorFeature(
                feature_id="hand-rail",
                feature_kind=PrimaryAnchorFeatureKind.RAIL,
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert {binding.installation_feature_id for binding in bindings} == {"left-wrist", "hand-rail"}


def test_gripps_anchor_rejects_same_host_redirect_to_different_product() -> None:
    requested = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Different Anchor",
        sku="H99999",
        url="https://www.au.gripps.com/products/different-anchor",
    )
    redirected = _artifact(
        "https://www.au.gripps.com/products/adjustable-wrist-anchor",
        "<h1>Adjustable Wrist Anchor - 2.5kg / 5.5lb</h1>"
        "<p>SKU H01086</p>"
        "<p>Can be attached to hand rails or your wrist.</p>"
        "<p>Industrial-grade Velcro adjusts diameter to suit any wrist or rail size.</p>"
        "<p>Max Load: 2.5kg / 5.5lb</p>",
    )

    result = IngestionRunner(RedirectingFetcher(requested.url, redirected)).ingest(
        requested,
        GRIPPSAdapter(),
    )

    assert result.claims == []


def test_klein_anchor_rejects_same_host_redirect_to_5144lg3() -> None:
    requested = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Different Bucket Accessory",
        sku="9999",
        url="https://www.kleintools.com/catalog/hooks-slings/different-bucket-accessory",
    )
    redirected = _artifact(
        "https://www.kleintools.com/catalog/hooks-slings/3-inch-gated-bucket-hook",
        "<h1>3-Inch Gated Bucket Hook</h1>"
        "<p>Setup is simple by easily attaching the hook to a 3-Inch (7.6 cm) lip aerial bucket.</p>"
        "<p>Includes a tether rated attachment point for tool tethering.</p>",
    )

    result = IngestionRunner(RedirectingFetcher(requested.url, redirected)).ingest(
        requested,
        KleinAdapter(),
    )

    assert result.claims == []
