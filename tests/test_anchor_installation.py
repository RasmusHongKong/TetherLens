import pytest

from tetherlens_ingest.anchor_installation import (
    AnchorAttachmentInstallationRule,
    AnchorEligibilityPath,
    AnchorFeaturePredicate,
    AnchorInstallationEligibilityEvaluation,
    AnchorInstallationMethod,
    PrimaryAnchorFeature,
    PrimaryAnchorFeatureKind,
    ResolvedPrimaryAnchor,
    evaluate_anchor_installation_eligibility,
    resolve_anchor_installation_bindings,
)
from tetherlens_ingest.compatibility import ComparisonOperator, EligibilityStatus


def _kind(kind: PrimaryAnchorFeatureKind) -> AnchorFeaturePredicate:
    return AnchorFeaturePredicate(property_key="feature_kind", value=kind.value)


def test_anchor_eligibility_path_requires_at_least_one_predicate() -> None:
    with pytest.raises(ValueError, match="at least one requirement or prohibition"):
        AnchorEligibilityPath(binding_name="empty")


def test_anchor_eligibility_evaluation_requires_complete_provenance() -> None:
    with pytest.raises(ValueError):
        AnchorInstallationEligibilityEvaluation(
            status=EligibilityStatus.ELIGIBLE,
            matches=[],
        )


def test_milwaukee_shaped_wrap_rule_binds_beam_and_rail_only() -> None:
    rule = AnchorAttachmentInstallationRule(
        rule_id="wrap_beam_or_rail",
        source_product_ref="anchor-strap",
        installation_method=AnchorInstallationMethod.WRAP,
        paths=[
            AnchorEligibilityPath(binding_name="beam", requirements=[_kind(PrimaryAnchorFeatureKind.BEAM)]),
            AnchorEligibilityPath(binding_name="rail", requirements=[_kind(PrimaryAnchorFeatureKind.RAIL)]),
        ],
        source_urls=["https://manufacturer.example/anchor-strap"],
    )
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="work-area-anchor",
        features=[
            PrimaryAnchorFeature(feature_id="beam-a", feature_kind=PrimaryAnchorFeatureKind.BEAM),
            PrimaryAnchorFeature(feature_id="rail-b", feature_kind=PrimaryAnchorFeatureKind.RAIL),
            PrimaryAnchorFeature(feature_id="belt-c", feature_kind=PrimaryAnchorFeatureKind.BELT),
        ],
    )

    evaluation = evaluate_anchor_installation_eligibility(rule, anchor)
    bindings = resolve_anchor_installation_bindings(rule, anchor)

    assert evaluation.status == EligibilityStatus.ELIGIBLE
    assert {match.feature_id for match in evaluation.matches} == {"beam-a", "rail-b"}
    assert [binding.installation_feature_id for binding in bindings] == ["beam-a", "rail-b"]
    assert all(binding.primary_anchor_ref == "work-area-anchor" for binding in bindings)
    assert all(binding.installation_method == AnchorInstallationMethod.WRAP for binding in bindings)


def test_falltech_shaped_cinch_rule_does_not_invent_small_diameter_geometry() -> None:
    rule = AnchorAttachmentInstallationRule(
        rule_id="cinch_belt",
        source_product_ref="cinch-anchor",
        installation_method=AnchorInstallationMethod.CINCH,
        paths=[
            AnchorEligibilityPath(binding_name="belt", requirements=[_kind(PrimaryAnchorFeatureKind.BELT)])
        ],
        source_urls=["https://manufacturer.example/cinch-anchor"],
    )
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker-anchor",
        features=[
            PrimaryAnchorFeature(
                feature_id="belt",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
            ),
            PrimaryAnchorFeature(
                feature_id="rail-described-as-small",
                feature_kind=PrimaryAnchorFeatureKind.RAIL,
                dimensions_mm={"section_diameter": 15.0},
            ),
        ],
    )

    bindings = resolve_anchor_installation_bindings(rule, anchor)

    assert [binding.installation_feature_id for binding in bindings] == ["belt"]


def _ergodyne_shaped_rule() -> AnchorAttachmentInstallationRule:
    return AnchorAttachmentInstallationRule(
        rule_id="thread_open_refastenable_belt",
        source_product_ref="belt-loop-anchor",
        installation_method=AnchorInstallationMethod.THREAD_OVER,
        paths=[
            AnchorEligibilityPath(
                binding_name="threadable_belt",
                requirements=[
                    _kind(PrimaryAnchorFeatureKind.BELT),
                    AnchorFeaturePredicate(
                        property_key="attribute:open_for_threading",
                        value=True,
                    ),
                    AnchorFeaturePredicate(
                        property_key="attribute:can_be_resecured",
                        value=True,
                    ),
                    AnchorFeaturePredicate(
                        property_key="dimension:section_height",
                        operator=ComparisonOperator.LTE,
                        value=76.2,
                    ),
                    AnchorFeaturePredicate(
                        property_key="dimension:section_thickness",
                        operator=ComparisonOperator.LTE,
                        value=12.7,
                    ),
                ],
            )
        ],
        source_urls=["https://manufacturer.example/belt-loop-anchor-instructions"],
    )


def test_ergodyne_shaped_rule_requires_all_facts_on_same_feature() -> None:
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="harness",
        features=[
            PrimaryAnchorFeature(
                feature_id="open-but-oversize",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 100.0, "section_thickness": 10.0},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            ),
            PrimaryAnchorFeature(
                feature_id="size-ok-but-closed",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 70.0, "section_thickness": 10.0},
                attributes={"open_for_threading": False, "can_be_resecured": True},
            ),
        ],
    )

    evaluation = evaluate_anchor_installation_eligibility(_ergodyne_shaped_rule(), anchor)

    assert evaluation.status == EligibilityStatus.INELIGIBLE
    assert evaluation.matches == []


def test_ergodyne_shaped_rule_fails_closed_when_required_dimension_is_unknown() -> None:
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="harness",
        features=[
            PrimaryAnchorFeature(
                feature_id="belt",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 70.0},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            )
        ],
    )

    evaluation = evaluate_anchor_installation_eligibility(_ergodyne_shaped_rule(), anchor)

    assert evaluation.status == EligibilityStatus.UNRESOLVED
    assert evaluation.matches == []


def test_ergodyne_shaped_rule_binds_exact_eligible_feature_with_provenance() -> None:
    rule = _ergodyne_shaped_rule()
    anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="harness",
        features=[
            PrimaryAnchorFeature(
                feature_id="belt",
                feature_kind=PrimaryAnchorFeatureKind.BELT,
                dimensions_mm={"section_height": 76.2, "section_thickness": 12.7},
                attributes={"open_for_threading": True, "can_be_resecured": True},
            )
        ],
    )

    [binding] = resolve_anchor_installation_bindings(rule, anchor)

    assert binding.primary_anchor_ref == "harness"
    assert binding.installation_feature_id == "belt"
    assert binding.rule_id == rule.rule_id
    assert binding.source_product_ref == rule.source_product_ref
    assert binding.installation_method == AnchorInstallationMethod.THREAD_OVER
    assert [(proof.path_index, proof.binding_name) for proof in binding.eligibility_proofs] == [
        (0, "threadable_belt")
    ]
    assert binding.source_urls == rule.source_urls
