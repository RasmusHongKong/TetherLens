from tetherlens_ingest.adapters import MilwaukeeAdapter
from tetherlens_ingest.compatibility import CaptiveState, FeatureKind, FeatureRole
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import resolve_tool_interface_features


PRODUCT_URL = (
    "https://www.milwaukeetool.com/products/details/"
    "14l-aluminum-pipe-wrench-with-powerlength-handle/48-22-7215"
)


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.TOOL,
        name='14L Aluminum Pipe Wrench with POWERLENGTH Handle',
        sku="48-22-7215",
        url=PRODUCT_URL,
    )


def _artifact(body: str, *, url: str = PRODUCT_URL) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_explicit_tether_ready_lanyard_hole_resolves_as_one_captive_tool_feature() -> None:
    claims = MilwaukeeAdapter().extract(
        _identity(),
        [
            _artifact(
                """
                <h1>48-22-7215 14L Aluminum Pipe Wrench with POWERLENGTH Handle</h1>
                <div>Tether-ready lanyard hole</div>
                """
            )
        ],
    )

    features = resolve_tool_interface_features(claims)

    assert len(features) == 1
    feature = features[0]
    assert feature.feature_id == "tether_ready_opening"
    assert feature.feature_kind == FeatureKind.THROUGH_OPENING
    assert feature.feature_role == FeatureRole.TETHER_INTERFACE
    assert feature.captive_state == CaptiveState.CAPTIVE


def test_tether_ready_handle_loop_uses_the_same_manufacturer_neutral_feature_shape() -> None:
    claims = MilwaukeeAdapter().extract(
        _identity(),
        [
            _artifact(
                """
                <h1>48-22-7215 14L Aluminum Pipe Wrench with POWERLENGTH Handle</h1>
                <p>Tether-Ready Handle Loop</p>
                """
            )
        ],
    )

    features = resolve_tool_interface_features(claims)

    assert [(feature.feature_kind, feature.captive_state) for feature in features] == [
        (FeatureKind.THROUGH_OPENING, CaptiveState.CAPTIVE)
    ]


def test_generic_handle_wording_does_not_invent_a_tether_feature() -> None:
    claims = MilwaukeeAdapter().extract(
        _identity(),
        [
            _artifact(
                """
                <h1>48-22-7215 14L Aluminum Pipe Wrench with POWERLENGTH Handle</h1>
                <p>Ergonomic handle design that helps prevent fatigue and slip.</p>
                """
            )
        ],
    )

    assert resolve_tool_interface_features(claims) == []


def test_tether_ready_feature_requires_verified_exact_sku_primary_page() -> None:
    claims = MilwaukeeAdapter().extract(
        _identity(),
        [
            _artifact(
                "<h1>Other product 48-22-7214</h1><p>Tether-ready lanyard hole</p>"
            )
        ],
    )

    assert resolve_tool_interface_features(claims) == []
