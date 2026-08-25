import pytest

from tetherlens_ingest.adapters import KleinAdapter, NLGAdapter
from tetherlens_ingest.compatibility import (
    CaptiveState,
    EligibilityStatus,
    FeatureKind,
    FeatureRole,
    evaluate_attachment_eligibility,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.resolution import (
    ClaimResolutionError,
    resolve_attachment_eligibility,
    resolve_tool_interface_features,
)


def artifact(body: str, *, url: str = "https://example.test/product") -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def test_klein_6826ins_to_nlg_101363_vertical_slice_uses_resolved_feature_semantics():
    klein_identity = ProductIdentity(
        manufacturer="Klein Tools",
        product_type=ProductType.TOOL,
        name="Insulated Screwdriver",
        sku="6826INS",
        url="https://example.test/klein/6826ins",
    )
    klein_claims = KleinAdapter().extract(
        klein_identity,
        [artifact("The tether hole in the handle provides added safety when working at height.")],
    )

    features = resolve_tool_interface_features(klein_claims)
    assert len(features) == 1
    assert features[0].feature_id == "tether_hole"
    assert features[0].feature_kind == FeatureKind.THROUGH_OPENING
    assert features[0].feature_role == FeatureRole.TETHER_INTERFACE
    assert features[0].captive_state == CaptiveState.CAPTIVE
    assert features[0].location_description == "handle"

    nlg_identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="360 D Ring Loop Tool Tether",
        sku="101363",
        url="https://example.test/nlg/101363",
    )
    nlg_claims = NLGAdapter().extract(
        nlg_identity,
        [
            artifact(
                "Create a tether point on any tool with a captive hole or handle and "
                "cinch it around the tool itself. Max Load: 3 kg."
            )
        ],
    )

    selection = next(
        claim for claim in nlg_claims if claim.property_key == "attachment_selection_class"
    )
    assert selection.value == "captive_feature_attachment"

    eligibility = resolve_attachment_eligibility(nlg_claims)
    assert eligibility is not None
    result = evaluate_attachment_eligibility(eligibility, features)

    assert result.status == EligibilityStatus.ELIGIBLE
    assert [(match.binding_name, match.feature_id) for match in result.matches] == [
        ("opening", "tether_hole")
    ]


def test_nlg_captive_feature_rule_reuses_same_eligibility_for_unrelated_tool_identity():
    nlg_claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            sku="101363",
            url="https://example.test/nlg/101363",
        ),
        [artifact("Connect to a captive handle or captive opening using the cinch loop.")],
    )
    eligibility = resolve_attachment_eligibility(nlg_claims)
    assert eligibility is not None

    unrelated_tool_claims = [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="rear_opening",
            property_key="feature.kind",
            value="through_opening",
            source_url="https://example.test/other-tool",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="rear_opening",
            property_key="feature.captive_state",
            value="captive",
            source_url="https://example.test/other-tool",
            extractor="test",
        ),
    ]
    features = resolve_tool_interface_features(unrelated_tool_claims)

    result = evaluate_attachment_eligibility(eligibility, features)
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.matches[0].feature_id == "rear_opening"


def test_feature_resolution_keeps_subject_refs_separate():
    claims = [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="handle",
            property_key="feature.kind",
            value="handle",
            source_url="https://example.test/tool",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="handle",
            property_key="feature.captive_state",
            value="non_captive",
            source_url="https://example.test/tool",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="opening",
            property_key="feature.kind",
            value="through_opening",
            source_url="https://example.test/tool",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="opening",
            property_key="feature.captive_state",
            value="captive",
            source_url="https://example.test/tool",
            extractor="test",
        ),
    ]

    features = resolve_tool_interface_features(claims)
    assert [(feature.feature_id, feature.feature_kind, feature.captive_state) for feature in features] == [
        ("handle", FeatureKind.HANDLE, CaptiveState.NON_CAPTIVE),
        ("opening", FeatureKind.THROUGH_OPENING, CaptiveState.CAPTIVE),
    ]


def test_conflicting_accepted_feature_claims_fail_resolution():
    claims = [
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="opening",
            property_key="feature.kind",
            value="through_opening",
            source_url="https://example.test/a",
            extractor="test",
        ),
        CandidateClaim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="opening",
            property_key="feature.kind",
            value="handle",
            source_url="https://example.test/b",
            extractor="test",
        ),
    ]

    with pytest.raises(ClaimResolutionError):
        resolve_tool_interface_features(claims)


def test_nlg_does_not_invent_captive_selection_from_unqualified_handle_or_hole_copy():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            url="https://example.test/nlg/generic",
        ),
        [artifact("Attach the loop to a handle or hole on the tool.")],
    )

    assert not any(
        claim.property_key == "attachment_selection_class" for claim in claims
    )


def test_nlg_does_not_join_captive_connector_copy_to_feature_alternatives_in_later_sentence():
    claims = NLGAdapter().extract(
        ProductIdentity(
            manufacturer="NLG",
            product_type=ProductType.TOOL_ATTACHMENT,
            url="https://example.test/nlg/generic",
        ),
        [artifact("Attach the captive loop to the D-ring. The tool chart lists a handle or hole.")],
    )

    assert not any(
        claim.property_key == "attachment_selection_class" for claim in claims
    )


def test_klein_does_not_borrow_handle_location_from_adjacent_copy():
    claims = KleinAdapter().extract(
        ProductIdentity(
            manufacturer="Klein Tools",
            product_type=ProductType.TOOL,
            url="https://example.test/klein/generic",
        ),
        [artifact("Comfortable handle with insulated grip\nIntegrated tether hole at the shaft end")],
    )

    features = resolve_tool_interface_features(claims)
    assert len(features) == 1
    assert features[0].feature_kind == FeatureKind.THROUGH_OPENING
    assert features[0].location_description is None
