import pytest

from tetherlens_ingest.adapters import ErgodyneAdapter, FallTechAdapter, MilwaukeeAdapter
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
from tetherlens_ingest.connection import ConnectionInterfaceRole
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.resolution import resolve_connection_interfaces


def _artifact(
    body: str,
    *,
    url: str,
    source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE,
    metadata: dict | None = None,
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
        metadata=metadata or {},
    )


def _assert_d_ring(claims):
    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    assert interfaces[0].role == ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE
    assert interfaces[0].interface_type == "ring"
    assert interfaces[0].attributes["ring_form"] == "d_ring"


def test_milwaukee_anchor_strap_vertical_compiles_beam_and_rail_wrap_without_geometry():
    identity = ProductIdentity(
        manufacturer="Milwaukee",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="50lbs Anchor Strap",
        sku="48-22-8855",
        url=(
            "https://www.milwaukeetool.com/products/details/"
            "50lbs-anchor-strap/48-22-8855"
        ),
    )
    claims = MilwaukeeAdapter().extract(
        identity,
        [
            _artifact(
                "<h1>50lbs Anchor Strap 48-22-8855</h1>"
                "<p>The anchor strap features an oversized D-Ring that holds 5 carabiners.</p>"
                "<p>The anchor strap's loop securely wraps around beams and rails for maximum productivity.</p>"
                "<p>The lanyard has a maximum working capacity of 50 pounds.</p>",
                url=identity.url,
            )
        ],
    )

    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in claims
    )
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="Milwaukee:48-22-8855",
    )
    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.WRAP
    assert [path.binding_name for path in rule.paths] == ["beam", "rail"]

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="site-anchor",
        features=[
            PrimaryAnchorFeature(
                feature_id="beam-A",
                feature_kind=PrimaryAnchorFeatureKind.BEAM,
            ),
            PrimaryAnchorFeature(
                feature_id="rail-B",
                feature_kind=PrimaryAnchorFeatureKind.RAIL,
            ),
            PrimaryAnchorFeature(
                feature_id="belt-C",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert [binding.installation_feature_id for binding in bindings] == ["beam-A", "rail-B"]
    assert all(binding.source_product_ref == "Milwaukee:48-22-8855" for binding in bindings)
    _assert_d_ring(claims)


def test_falltech_cinch_vertical_compiles_only_explicit_belt_subset():
    identity = ProductIdentity(
        manufacturer="FallTech",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Waist Belt Cinch Anchor Attachment",
        sku="5424A10",
        url="https://www.falltech.com/product/5424a10/",
    )
    claims = FallTechAdapter().extract(
        identity,
        [
            _artifact(
                "<h1>Waist Belt Cinch Anchor Attachment</h1>"
                "<p>SKU: 5424A10</p>"
                "<p>Its simple choke-on installation provides a secure setup.</p>"
                "<p>Fits most full body harness belts and other small diameter anchorage locations.</p>"
                "<p>Steel D-ring provides secure connection point for tool tether.</p>"
                "<p>Filter - Tool Weight Capacity: 5 lb max.</p>",
                url=identity.url,
            )
        ],
    )

    assert not any(
        claim.property_key.startswith("anchor_installation.dimension.")
        for claim in claims
    )
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="FallTech:5424A10",
    )
    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.CINCH
    assert len(rule.paths) == 1
    assert rule.paths[0].binding_name == "belt"

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker",
        features=[
            PrimaryAnchorFeature(
                feature_id="belt",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
            ),
            PrimaryAnchorFeature(
                feature_id="rail",
                feature_kind=PrimaryAnchorFeatureKind.RAIL,
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert [binding.installation_feature_id for binding in bindings] == ["belt"]
    _assert_d_ring(claims)


def test_ergodyne_3171_vertical_uses_identity_scoped_instruction_topology_and_dimensions():
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3171 Anchor Strap Belt Loop Attachment",
        model="3171",
        sku="19171",
        url=(
            "https://www.ergodyne.com/"
            "squids-3171-anchor-strap-belt-loop-attachment-tool-tethering-5-lbs-2.3-kg"
        ),
    )
    primary = _artifact(
        "<html><body>"
        "<h1>Squids 3171 Anchor Strap Belt Loop Attachment for Tool Tethering</h1>"
        "<div>Item #: 19171</div>"
        "<p>Durable steel D-ring for attaching tool lanyards.</p>"
        "<p>Third party certified to a 5lbs / 2.3kg maximum working capacity.</p>"
        "</body></html>",
        url=identity.url,
    )
    manual_url = (
        "https://www.ergodyne.com/sites/default/files/2022-11/"
        "squids-3171-3172-3174-3176-3177-anchor-straps-instructions.pdf"
    )
    manual = _artifact(
        "SELECTING AN ANCHOR ATTACHMENT\n"
        "3171 Belt loop Fall Protection Belts, Tool Belts 5lbs / 2.26kg 48in / 122cm "
        "3in / 7.6cm x 0.5in / 1.3cm\n"
        "3172 Hook & loop Fall Protection Belts, Tool Belts, Harness Webbing 5lbs / 2.26kg "
        "48in / 122cm 3in / 7.6cm x 0.5in / 1.3cm\n"
        "3171 BELT LOOP ANCHOR INSTRUCTIONS\n"
        "The fully enclosed Belt Loop Anchor Attachment must be threaded onto an open-ended "
        "Primary Anchor like a belt. The Primary Anchor must then be secured in a manner that "
        "does not allow the anchor to slide off.\n"
        "1. Undo the belt that is acting as the Primary Anchor\n"
        "2. Thread the belt through the loop of the Anchor Attachment\n"
        "3. Refasten and secure the belt\n"
        "4. Attach a tool lanyard to the d-ring\n"
        "3172 HOOK & LOOP ANCHOR INSTRUCTIONS\n"
        "Primary Anchor should not be taller than 99in and not thicker than 88in.",
        url=manual_url,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        metadata={"role": "anchor_attachment_instructions"},
    )

    adapter = ErgodyneAdapter()
    claims = adapter.extract(identity, [primary, manual])
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="Ergodyne:19171",
    )
    assert rule is not None
    assert rule.installation_method == AnchorInstallationMethod.THREAD_OVER
    assert len(rule.paths) == 1
    path = rule.paths[0]
    assert path.binding_name == "belt"

    predicates = {predicate.property_key: predicate for predicate in path.requirements}
    assert predicates["feature_kind"].value == "belt"
    assert predicates["attribute:open_for_threading"].value is True
    assert predicates["attribute:can_be_resecured"].value is True
    assert predicates["dimension:section_height"].value == pytest.approx(76.2)
    assert predicates["dimension:section_thickness"].value == pytest.approx(12.7)

    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker-belt",
        features=[
            PrimaryAnchorFeature(
                feature_id="eligible",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 70.0, "section_thickness": 10.0},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            ),
            PrimaryAnchorFeature(
                feature_id="oversize",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 80.0, "section_thickness": 10.0},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            ),
        ],
    )
    bindings = resolve_anchor_installation_bindings(rule, anchor)
    assert [binding.installation_feature_id for binding in bindings] == ["eligible"]
    _assert_d_ring(claims)


def test_ergodyne_3171_same_feature_predicates_do_not_stitch_across_belts():
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3171 Anchor Strap Belt Loop Attachment",
        model="3171",
        sku="19171",
        url=(
            "https://www.ergodyne.com/"
            "squids-3171-anchor-strap-belt-loop-attachment-tool-tethering-5-lbs-2.3-kg"
        ),
    )
    primary = _artifact(
        "<h1>Squids 3171 Anchor Strap Belt Loop Attachment</h1><p>Item #: 19171</p>",
        url=identity.url,
    )
    manual_url = (
        "https://www.ergodyne.com/sites/default/files/2022-11/"
        "squids-3171-3172-3174-3176-3177-anchor-straps-instructions.pdf"
    )
    manual = _artifact(
        "3171 Belt loop Fall Protection Belts, Tool Belts 5lbs / 2.26kg 48in / 122cm "
        "3in / 7.6cm x 0.5in / 1.3cm\n"
        "3172 Hook & loop next row\n"
        "3171 BELT LOOP ANCHOR INSTRUCTIONS\n"
        "The fully enclosed Belt Loop Anchor Attachment must be threaded onto an open-ended "
        "Primary Anchor like a belt.\n"
        "Undo the belt that is acting as the Primary Anchor.\n"
        "Refasten and secure the belt.\n"
        "3172 HOOK & LOOP ANCHOR INSTRUCTIONS",
        url=manual_url,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        metadata={"role": "anchor_attachment_instructions"},
    )
    claims = ErgodyneAdapter().extract(identity, [primary, manual])
    rule = resolve_anchor_attachment_installation_rule(
        claims,
        source_product_ref="Ergodyne:19171",
    )
    assert rule is not None

    split_facts = ResolvedPrimaryAnchor(
        primary_anchor_ref="split",
        features=[
            PrimaryAnchorFeature(
                feature_id="topology-only",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 90.0, "section_thickness": 20.0},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            ),
            PrimaryAnchorFeature(
                feature_id="dimensions-only",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 70.0, "section_thickness": 10.0},
                attributes={"open_for_threading": False, "can_be_resecured": False},
            ),
        ],
    )
    evaluation = evaluate_anchor_installation_eligibility(rule, split_facts)
    assert evaluation.status == EligibilityStatus.INELIGIBLE
    assert evaluation.matches == []


def test_ergodyne_source_graph_requires_verified_3171_primary():
    identity = ProductIdentity(
        manufacturer="Ergodyne",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Squids 3171 Anchor Strap Belt Loop Attachment",
        model="3171",
        sku="19171",
        url=(
            "https://www.ergodyne.com/"
            "squids-3171-anchor-strap-belt-loop-attachment-tool-tethering-5-lbs-2.3-kg"
        ),
    )
    primary = _artifact(
        "<h1>Squids 3171 Anchor Strap Belt Loop Attachment</h1><p>Item #: 19171</p>",
        url=identity.url,
    )
    requests = ErgodyneAdapter().related_sources(identity, primary)
    assert len(requests) == 1
    assert requests[0].source_type == SourceType.MANUFACTURER_DOCUMENT
    assert requests[0].url.startswith("https://www.ergodyne.com/")
    assert requests[0].metadata["role"] == "anchor_attachment_instructions"

    wrong_product = _artifact(
        "<h1>Squids 3172 Anchor Strap Hook & Loop Closure</h1><p>Item #: 19172</p>",
        url=identity.url,
    )
    assert ErgodyneAdapter().related_sources(identity, wrong_product) == []
