import pytest

from tetherlens_ingest.adapters import GRIPPSAdapter, ThreeMAdapter
from tetherlens_ingest.compatibility import (
    CaptiveState,
    EligibilityStatus,
    FeatureKind,
    ToolInterfaceFeature,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.constraints import (
    ProductConstraintContext,
    ProductConstraintDisposition,
    ProductConstraintStatus,
    evaluate_product_constraints,
    resolve_product_constraints,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
)


def _artifact(body: str, *, url: str, source_type=SourceType.MANUFACTURER_WEBPAGE):
    return SourceArtifact(
        url=url,
        source_type=source_type,
        content_type="application/pdf" if source_type == SourceType.MANUFACTURER_DOCUMENT else "text/html",
        body=body,
    )


def test_gripps_snaplock_vertical_uses_handle_subset_without_neck_or_size_inference():
    identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="SnapLock",
        sku="H01150",
        url="https://gripps.com/products/snaplock",
    )
    claims = GRIPPSAdapter().extract(
        identity,
        [
            _artifact(
                "The GRIPPS SnapLock is a self-closing tool connector that provides a secure, "
                "standardised connection point for tethering compatible tools. Its self-closing "
                "design allows fast installation to a tool's handle or neck. Max Load: 6.8 kg | "
                "15 lb. Available in four sizes (S, M, L, XL).",
                url=identity.url,
            )
        ],
    )

    by_key = {}
    for claim in claims:
        by_key.setdefault(claim.property_key, []).append(claim)

    assert by_key["attachment_selection_class"][0].value == "handle_attachment"
    assert by_key["attachment_method_code"][0].value == "mechanical_capture"
    assert by_key["rated_capacity_kg"][0].value == pytest.approx(6.8)
    assert not any(
        claim.value == "external_section_attachment"
        for claim in by_key["attachment_selection_class"]
    )
    assert not any(
        claim.property_key.startswith(("feature.dimension.", "interface.dimension."))
        for claim in claims
    )

    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    result = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="non_captive_handle",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="captive_handle",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="tool_neck",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
        ],
    )
    assert result.status == EligibilityStatus.ELIGIBLE
    assert [match.feature_id for match in result.matches] == [
        "non_captive_handle",
        "captive_handle",
    ]

    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    assert interfaces[0].interface_id == "snaplock_tether_connection"
    assert interfaces[0].interface_type == "unknown"


def test_three_m_quick_spin_vertical_separates_fit_obligation_from_taper_prohibition():
    identity = ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url="https://www.3m.com/3M/en_LB/p/d/v100323604/",
    )
    product = _artifact(
        "<html><body>"
        "<h1>3M DBI-SALA Quick Spin Medium Size 1500028</h1>"
        "<div>3M Product Number 1500028</div>"
        "<p>Tangle-resistant spin top simply slides onto the handle of a tool in seconds.</p>"
        "<p>Quick spin, 0.5 kg (1 lb.) capacity, 2 cm (0.80 in) diameter.</p>"
        "</body></html>",
        url=identity.url,
    )
    manual = _artifact(
        "Python Safety Quick Spins simply slides onto the handle of a tool in seconds. "
        "On tools under 1lb (0.5kg) where the Quick Spin will fit tightly on a handle. "
        "Do not use if a snug fit on the tool cannot be secured. "
        "Never attach tool lanyards or attachment points to a tapered surface. "
        "Identify a Quick Spin Adapter that will properly fit the handle of the tool. "
        "Some force should be necessary to create a snug fit. Ensure that the Quick Spin "
        "is firmly in place before use. A non-metallic attachment point is needed.",
        url=(
            "https://multimedia.3m.com/mws/media/1300988O/"
            "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
        ),
        source_type=SourceType.MANUFACTURER_DOCUMENT,
    )

    adapter = ThreeMAdapter()
    claims = adapter.extract(identity, [product, manual])

    assert any(
        claim.property_key == "attachment_selection_class"
        and claim.value == "handle_attachment"
        for claim in claims
    )
    assert any(
        claim.property_key == "attachment_method_code"
        and claim.value == "mechanical_capture"
        for claim in claims
    )
    capacity = next(claim for claim in claims if claim.property_key == "rated_capacity_kg")
    assert capacity.value == pytest.approx(0.5)
    assert not any(
        claim.property_key.startswith(("feature.dimension.", "interface.dimension."))
        for claim in claims
    )

    constraints = resolve_product_constraints(
        claims,
        source_product_ref="3M:1500028",
    )
    by_key = {constraint.constraint_key: constraint for constraint in constraints}
    assert by_key["secure_attachment_fit_required"].disposition == (
        ProductConstraintDisposition.PRE_USE_OBLIGATION
    )
    assert by_key["prohibited_surface_profile"].disposition == ProductConstraintDisposition.HARD
    assert by_key["prohibited_surface_profile"].value == "tapered"

    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    eligible = evaluate_attachment_eligibility(
        eligibility,
        [
            ToolInterfaceFeature(
                feature_id="handle:cylindrical",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
                attributes={"surface_profile": "cylindrical"},
            )
        ],
    )
    assert eligible.status == EligibilityStatus.ELIGIBLE

    cylindrical = ToolInterfaceFeature(
        feature_id="handle:cylindrical",
        feature_kind=FeatureKind.HANDLE,
        attributes={"surface_profile": "cylindrical"},
    )
    evaluations = {
        item.constraint_key: item
        for item in evaluate_product_constraints(
            constraints,
            ProductConstraintContext(installation_feature=cylindrical),
        )
    }
    assert evaluations["prohibited_surface_profile"].status == ProductConstraintStatus.PASSED
    assert evaluations["prohibited_surface_profile"].installation_feature_id == (
        "handle:cylindrical"
    )
    assert evaluations["secure_attachment_fit_required"].status == (
        ProductConstraintStatus.REQUIRES_ACTION
    )

    tapered = ToolInterfaceFeature(
        feature_id="handle:tapered",
        feature_kind=FeatureKind.HANDLE,
        attributes={"surface_profile": "tapered"},
    )
    tapered_eval = {
        item.constraint_key: item
        for item in evaluate_product_constraints(
            constraints,
            ProductConstraintContext(installation_feature=tapered),
        )
    }
    assert tapered_eval["prohibited_surface_profile"].status == ProductConstraintStatus.FAILED
    assert tapered_eval["prohibited_surface_profile"].installation_feature_id == "handle:tapered"

    unknown = ToolInterfaceFeature(
        feature_id="handle:unknown_profile",
        feature_kind=FeatureKind.HANDLE,
    )
    unknown_eval = {
        item.constraint_key: item
        for item in evaluate_product_constraints(
            constraints,
            ProductConstraintContext(installation_feature=unknown),
        )
    }
    assert unknown_eval["prohibited_surface_profile"].status == ProductConstraintStatus.UNRESOLVED


def test_three_m_quick_spin_requests_first_party_family_manual_without_nominal_fit_semantics():
    identity = ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url="https://www.3m.com/3M/en_LB/p/d/v100323604/",
    )
    primary = _artifact(
        "<html><body>"
        "<h1>3M DBI-SALA Quick Spin Medium Size 1500028</h1>"
        "<div>3M Product Number 1500028</div>"
        "</body></html>",
        url=identity.url,
    )

    requests = ThreeMAdapter().related_sources(identity, primary)

    assert len(requests) == 1
    assert requests[0].source_type == SourceType.MANUFACTURER_DOCUMENT
    assert requests[0].url.startswith("https://multimedia.3m.com/")
    assert ThreeMAdapter().accepts_request_provenance(identity, requests[0])
