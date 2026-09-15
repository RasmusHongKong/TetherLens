from __future__ import annotations

import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter, FallTechAdapter, GRIPPSAdapter, KleinAdapter
from tetherlens_ingest.anchor_claim_resolution import resolve_anchor_attachment_installation_rule
from tetherlens_ingest.anchor_installation import (
    AnchorInstallationMethod,
    PrimaryAnchorFeature,
    PrimaryAnchorFeatureKind,
    ResolvedPrimaryAnchor,
    evaluate_anchor_installation_eligibility,
    resolve_anchor_installation_bindings,
)
from tetherlens_ingest.compatibility import EligibilityStatus
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.runner import IngestionRunner


FALLTECH_WRIST_INSTRUCTIONS_URL = (
    "https://cdn11.bigcommerce.com/s-1wxw1202sk/content/product_documents/"
    "instruction_manuals/MTOL05_Rev_B_013125_EN.pdf"
)
ERGODYNE_BUCKET_INSTRUCTIONS_URL = (
    "https://www.ergodyne.com/sites/default/files/2022-11/"
    "squids-3178-locking-bucket-hook-instructions.pdf"
)


class MappingFetcher:
    def __init__(self, artifacts: dict[str, SourceArtifact]):
        self.artifacts = artifacts
        self.calls: list[tuple[str, SourceType]] = []

    def get(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    ) -> SourceArtifact:
        self.calls.append((url, source_type))
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
        content_type=(
            "application/pdf"
            if source_type == SourceType.MANUFACTURER_DOCUMENT
            else "text/html"
        ),
        body=body,
    )


def _installation_rule(result, identity: ProductIdentity):
    rule = resolve_anchor_attachment_installation_rule(
        result.claims,
        source_product_ref=f"{identity.manufacturer}:{identity.sku}",
    )
    assert rule is not None
    return rule


def _assert_no_numeric_installation_fit(claims) -> None:
    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in claims
    )


def test_falltech_5331a1_runner_proves_wrist_fasten_around_without_numeric_fit() -> None:
    identity = ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Wrist Attachment Anchor",
        sku="5331A1",
        url="https://www.falltech.com/product/5331a1/",
    )
    primary = _artifact(
        identity.url,
        "<h1>5331A1 Wrist Attachment Anchor; adjustable UniFit size with Speed-clip and D-ring</h1>"
        "<p>Product Type: Adjustable Wristband Anchor</p>"
        "<p>SKU: 5331A1</p>"
        "<p>D-ring Plated Steel</p>"
        "<p>Filter - Tool Weight Capacity: 5 lb max.</p>",
    )
    instructions = _artifact(
        FALLTECH_WRIST_INSTRUCTIONS_URL,
        "5331A1 / 5331A5 Wrist Attachment Point 5 lb UniFit D-ring + Speed-clip\n"
        "4.2.1 Wristband System: To install, loosen the velcro strap and slide the wristband over the hand. "
        "The wristband is correctly adjusted when one finger can be inserted between the wristband and forearm. "
        "To tighten, pull on the strap and attach the velcro.",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    fetcher = MappingFetcher(
        {
            identity.url: primary,
            FALLTECH_WRIST_INSTRUCTIONS_URL: instructions,
        }
    )

    result = IngestionRunner(fetcher).ingest(identity, FallTechAdapter())
    rule = _installation_rule(result, identity)

    assert fetcher.calls == [
        (identity.url, SourceType.MANUFACTURER_WEBPAGE),
        (FALLTECH_WRIST_INSTRUCTIONS_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert rule.installation_method == AnchorInstallationMethod.FASTEN_AROUND
    assert [path.binding_name for path in rule.paths] == ["wrist"]
    predicates = {predicate.property_key: predicate.value for predicate in rule.paths[0].requirements}
    assert predicates == {"feature_kind": "wrist"}
    _assert_no_numeric_installation_fit(result.claims)

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker",
        features=[
            PrimaryAnchorFeature(
                feature_id="left-wrist",
                feature_kind=PrimaryAnchorFeatureKind.WRIST,
            ),
            PrimaryAnchorFeature(
                feature_id="harness-belt",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert [binding.installation_feature_id for binding in bindings] == ["left-wrist"]
    assert bindings[0].source_urls == [FALLTECH_WRIST_INSTRUCTIONS_URL]


def test_gripps_h01086_runner_proves_same_wrist_family_without_all_sizes_geometry() -> None:
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Adjustable Wrist Anchor",
        sku="H01086",
        url="https://www.au.gripps.com/products/adjustable-wrist-anchor",
    )
    primary = _artifact(
        identity.url,
        "<h1>Adjustable Wrist Anchor - 2.5kg / 5.5lb</h1>"
        "<p>SKU H01086</p>"
        "<p>A versatile wristband, designed to fit all sizes, incorporates a built-in, load-rated tether anchor.</p>"
        "<p>Can be attached to hand rails or your wrist.</p>"
        "<p>Industrial-grade Velcro adjusts diameter to suit any wrist or rail size.</p>"
        "<p>Max Load: 2.5kg / 5.5lb</p>",
    )
    fetcher = MappingFetcher({identity.url: primary})

    result = IngestionRunner(fetcher).ingest(identity, GRIPPSAdapter())
    rule = _installation_rule(result, identity)

    assert fetcher.calls == [(identity.url, SourceType.MANUFACTURER_WEBPAGE)]
    assert rule.installation_method == AnchorInstallationMethod.FASTEN_AROUND
    assert [path.binding_name for path in rule.paths] == ["wrist"]
    predicates = {predicate.property_key: predicate.value for predicate in rule.paths[0].requirements}
    assert predicates == {"feature_kind": "wrist"}
    _assert_no_numeric_installation_fit(result.claims)


def test_ergodyne_3178_runner_uses_bucket_lip_nominal_class_not_numeric_envelope() -> None:
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3178 Locking Aerial Bucket Hook Tethering Point",
        model="3178",
        sku="19178",
        url="https://www.ergodyne.com/squids-3178-locking-aerial-bucket-hook-tethering-point",
    )
    primary = _artifact(
        identity.url,
        "<h1>Squids 3178 Locking Aerial Bucket Hook Tethering Point</h1>"
        "<p>Item #: 19178</p>"
        "<p>Simply clip to the bucket lip. Self-locking exterior hook with enclosed tethering point.</p>",
    )
    instructions = _artifact(
        ERGODYNE_BUCKET_INSTRUCTIONS_URL,
        "PRIMARY ANCHOR: lip of the aerial bucket\n"
        "ANCHOR ATTACHMENT (HOOK ITEM): 19178\n"
        "LIP CAVITY OF HOOK (BUCKET LIP SIZE) 2IN // 5CM\n"
        "STATIC LOAD RATING 40LB // 18.1KG DYNAMIC TETHER POINT 7LB // 3.2KG\n"
        "Pry the hook over the lip at approximately 45 degrees until it snaps into place.\n"
        "19179\n"
        "LIP CAVITY OF HOOK (BUCKET LIP SIZE) 3IN // 7.6CM",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )
    fetcher = MappingFetcher(
        {
            identity.url: primary,
            ERGODYNE_BUCKET_INSTRUCTIONS_URL: instructions,
        }
    )

    result = IngestionRunner(fetcher).ingest(identity, ErgodyneAdapter())
    rule = _installation_rule(result, identity)

    assert fetcher.calls == [
        (identity.url, SourceType.MANUFACTURER_WEBPAGE),
        (ERGODYNE_BUCKET_INSTRUCTIONS_URL, SourceType.MANUFACTURER_DOCUMENT),
    ]
    assert rule.installation_method == AnchorInstallationMethod.HOOK_ON
    assert [path.binding_name for path in rule.paths] == ["bucket_lip"]
    predicates = {predicate.property_key: predicate.value for predicate in rule.paths[0].requirements}
    assert predicates == {
        "feature_kind": "bucket_lip",
        "attribute:nominal_lip_size": "2_in",
    }
    _assert_no_numeric_installation_fit(result.claims)

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="aerial-bucket",
        features=[
            PrimaryAnchorFeature(
                feature_id="two-inch-lip",
                feature_kind=PrimaryAnchorFeatureKind.BUCKET_LIP,
                attributes={"nominal_lip_size": "2_in"},
            ),
            PrimaryAnchorFeature(
                feature_id="three-inch-lip",
                feature_kind=PrimaryAnchorFeatureKind.BUCKET_LIP,
                attributes={"nominal_lip_size": "3_in"},
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert [binding.installation_feature_id for binding in bindings] == ["two-inch-lip"]
    assert bindings[0].source_urls == [ERGODYNE_BUCKET_INSTRUCTIONS_URL]


def test_klein_5144lg3_runner_proves_same_bucket_lip_hook_family() -> None:
    identity = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="3-Inch Gated Bucket Hook",
        sku="5144LG3",
        url="https://www.kleintools.com/catalog/hooks-slings/3-inch-gated-bucket-hook",
    )
    primary = _artifact(
        identity.url,
        "<h1>3-Inch Gated Bucket Hook</h1>"
        "<p>Setup is simple by easily attaching the hook to a 3-Inch (7.6 cm) lip aerial bucket.</p>"
        "<p>Quickly attaches to standard 3-Inch (7.6 cm) lip aerial buckets.</p>"
        "<p>Includes a tether rated attachment point for tool tethering.</p>",
    )
    fetcher = MappingFetcher({identity.url: primary})

    result = IngestionRunner(fetcher).ingest(identity, KleinAdapter())
    rule = _installation_rule(result, identity)

    assert fetcher.calls == [(identity.url, SourceType.MANUFACTURER_WEBPAGE)]
    assert rule.installation_method == AnchorInstallationMethod.HOOK_ON
    assert [path.binding_name for path in rule.paths] == ["bucket_lip"]
    predicates = {predicate.property_key: predicate.value for predicate in rule.paths[0].requirements}
    assert predicates == {
        "feature_kind": "bucket_lip",
        "attribute:nominal_lip_size": "3_in",
    }
    _assert_no_numeric_installation_fit(result.claims)


def test_bucket_lip_predicates_never_stitch_across_concrete_features() -> None:
    identity = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="3-Inch Gated Bucket Hook",
        sku="5144LG3",
        url="https://www.kleintools.com/catalog/hooks-slings/3-inch-gated-bucket-hook",
    )
    claims = KleinAdapter().extract(
        identity,
        [
            _artifact(
                identity.url,
                "<p>Setup is simple by easily attaching the hook to a 3-Inch (7.6 cm) lip aerial bucket.</p>",
            )
        ],
    )
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="Klein Tools:5144LG3",
    )
    assert rule is not None

    split = ResolvedPrimaryAnchor(
        primary_anchor_ref="split-evidence",
        features=[
            PrimaryAnchorFeature(
                feature_id="lip-with-unknown-size",
                feature_kind=PrimaryAnchorFeatureKind.BUCKET_LIP,
            ),
            PrimaryAnchorFeature(
                feature_id="rail-with-right-size-label",
                feature_kind=PrimaryAnchorFeatureKind.RAIL,
                attributes={"nominal_lip_size": "3_in"},
            ),
        ],
    )

    evaluation = evaluate_anchor_installation_eligibility(rule, split)

    assert evaluation.status == EligibilityStatus.UNRESOLVED
    assert evaluation.matches == []


def test_bucket_lip_wrong_known_nominal_class_is_ineligible() -> None:
    identity = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="3-Inch Gated Bucket Hook",
        sku="5144LG3",
        url="https://www.kleintools.com/catalog/hooks-slings/3-inch-gated-bucket-hook",
    )
    claims = KleinAdapter().extract(
        identity,
        [
            _artifact(
                identity.url,
                "<p>Setup is simple by easily attaching the hook to a 3-Inch (7.6 cm) lip aerial bucket.</p>",
            )
        ],
    )
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="Klein Tools:5144LG3",
    )
    assert rule is not None

    wrong_size = ResolvedPrimaryAnchor(
        primary_anchor_ref="aerial-bucket",
        features=[
            PrimaryAnchorFeature(
                feature_id="two-inch-lip",
                feature_kind=PrimaryAnchorFeatureKind.BUCKET_LIP,
                attributes={"nominal_lip_size": "2_in"},
            )
        ],
    )

    evaluation = evaluate_anchor_installation_eligibility(rule, wrong_size)

    assert evaluation.status == EligibilityStatus.INELIGIBLE
    assert evaluation.matches == []
