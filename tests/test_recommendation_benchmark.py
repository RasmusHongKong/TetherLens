import json
from pathlib import Path

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    EligibilityPath,
    FeaturePredicate,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import resolve_product_constraints
from tetherlens_ingest.declared_compatibility import (
    connection_contexts_from_compatibility_declarations,
    resolve_connector_interface_compatibility_declarations,
)
from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ConstraintOperator,
)
from tetherlens_ingest.recommendation_run import RecommendationRunResult, run_recommendation
from tetherlens_ingest.resolution import (
    resolve_connection_interfaces,
    resolve_tool_interface_features,
)


GOLDEN_PATH = (
    Path(__file__).resolve().parents[1] / "benchmarks" / "recommendation_e2e_golden.json"
)
DECLARATION_URL = "https://go.neverletgo.com/hubfs/Product/Datasheet/101456.pdf"
ANCHOR_URL = "https://neverletgo.com/products/wristband/"
TOOL_URL = "https://example.test/benchmark-tool"
TOOL_ATTACHMENT_URL = "https://example.test/benchmark-tool-attachment"
PROHIBITED_GOLDEN_IDENTITY_KEYS = {"id", "ids", "ref", "refs", "sku", "skus"}
PROHIBITED_GOLDEN_IDENTITY_SUFFIXES = (
    "_id",
    "_ids",
    "_ref",
    "_refs",
    "_sku",
    "_skus",
)


def _accepted_claim(
    *,
    subject_type: ClaimSubjectType,
    subject_ref: str,
    property_key: str,
    value,
    source_url: str,
    claim_type: ClaimType | None = None,
    constraint_operator: ConstraintOperator | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=subject_type,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        source_url=source_url,
        extractor="benchmark.accepted_fixture",
        claim_type=claim_type,
        constraint_operator=constraint_operator,
    )


def _resolved_d_ring_anchor() -> ConnectionInterface:
    claims = [
        _accepted_claim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="benchmark_anchor_d_ring",
            property_key="interface.role",
            value="anchor_attachment_tether_side",
            source_url=ANCHOR_URL,
        ),
        _accepted_claim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="benchmark_anchor_d_ring",
            property_key="interface.type",
            value="ring",
            source_url=ANCHOR_URL,
        ),
        _accepted_claim(
            subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
            subject_ref="benchmark_anchor_d_ring",
            property_key="interface.attribute.ring_form",
            value="d_ring",
            source_url=ANCHOR_URL,
        ),
    ]
    interfaces = resolve_connection_interfaces(claims)
    assert len(interfaces) == 1
    return interfaces[0]


def _accepted_quick_clip_declaration():
    values = (
        ("connection_compatibility.connector_spec_ref", "quick_clip"),
        ("connection_compatibility.source_interface_type", "clip"),
        ("connection_compatibility.target_interface_type", "ring"),
        ("connection_compatibility.target_role", "anchor_attachment_tether_side"),
        ("connection_compatibility.target_attribute.ring_form", "d_ring"),
        ("connection_compatibility.issuer_manufacturer", "NLG"),
        ("connection_compatibility.scope", "Quick Clip to D-ring anchor point"),
    )
    claims = [
        _accepted_claim(
            subject_type=ClaimSubjectType.CONNECTION_COMPATIBILITY,
            subject_ref="quick_clip_to_d_ring_anchor",
            property_key=property_key,
            value=value,
            source_url=DECLARATION_URL,
        )
        for property_key, value in values
    ]
    declarations = resolve_connector_interface_compatibility_declarations(claims)
    assert len(declarations) == 1
    return declarations[0]


def _tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="benchmark:tool",
        object_mass_kg=2.0,
        direct_interfaces=[
            ConnectionInterface(
                interface_id="benchmark:tool:ring",
                role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                interface_type="ring",
            )
        ],
    )


def _resolved_surface_tool() -> ResolvedToolCandidate:
    claims: list[CandidateClaim] = []
    for subject_ref, surface_profile in (
        ("benchmark_tool_surface_flat", "flat"),
        ("benchmark_tool_surface_curved", "curved"),
    ):
        claims.extend(
            [
                _accepted_claim(
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref=subject_ref,
                    property_key="feature.kind",
                    value="surface",
                    source_url=TOOL_URL,
                ),
                _accepted_claim(
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref=subject_ref,
                    property_key="feature.attribute.surface_profile",
                    value=surface_profile,
                    source_url=TOOL_URL,
                ),
                _accepted_claim(
                    subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                    subject_ref=subject_ref,
                    property_key="feature.attribute.surface_condition.clean",
                    value=True,
                    source_url=TOOL_URL,
                ),
            ]
        )

    features = resolve_tool_interface_features(claims)
    assert len(features) == 2
    return ResolvedToolCandidate(
        tool_ref="benchmark:surface-tool",
        object_mass_kg=2.0,
        features=features,
    )


def _surface_attachment_assembly() -> ToolAttachmentAssemblyOption:
    source_product_ref = "benchmark:attachment-product"
    constraint_claims = [
        _accepted_claim(
            subject_type=ClaimSubjectType.PRODUCT,
            subject_ref="self",
            property_key="installation_surface_profile",
            value="flat",
            source_url=TOOL_ATTACHMENT_URL,
            claim_type=ClaimType.DECLARED_CONSTRAINT,
            constraint_operator=ConstraintOperator.REQUIRES,
        ),
        _accepted_claim(
            subject_type=ClaimSubjectType.PRODUCT,
            subject_ref="self",
            property_key="required_surface_condition",
            value="clean",
            source_url=TOOL_ATTACHMENT_URL,
            claim_type=ClaimType.DECLARED_CONSTRAINT,
            constraint_operator=ConstraintOperator.REQUIRES,
        ),
    ]
    constraints = resolve_product_constraints(
        constraint_claims,
        source_product_ref=source_product_ref,
    )
    assert len(constraints) == 2

    provided_interfaces = resolve_connection_interfaces(
        [
            _accepted_claim(
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref="benchmark_attachment_tether_ring",
                property_key="interface.role",
                value="tool_attachment_tether_side",
                source_url=TOOL_ATTACHMENT_URL,
            ),
            _accepted_claim(
                subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
                subject_ref="benchmark_attachment_tether_ring",
                property_key="interface.type",
                value="ring",
                source_url=TOOL_ATTACHMENT_URL,
            ),
        ]
    )
    assert len(provided_interfaces) == 1

    return ToolAttachmentAssemblyOption(
        assembly_ref="benchmark:surface-attachment-assembly",
        components=[
            CandidateComponentOption(
                component_ref="benchmark:surface-attachment-component",
                source_product_ref=source_product_ref,
                rated_capacity_kg=5.0,
                product_constraints=constraints,
            )
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="surface",
                    requirements=[
                        FeaturePredicate(
                            property_key="feature_kind",
                            value="surface",
                        )
                    ],
                )
            ]
        ),
        provided_interfaces=provided_interfaces,
    )


def _anchor_path(target: ConnectionInterface) -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="benchmark:anchor-path",
        components=[
            CandidateComponentOption(
                component_ref="benchmark:anchor-component",
                source_product_ref="benchmark:anchor-product",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[target],
    )


def _carabiner_tether(label: str, *, capacity_kg: float) -> TetherOption:
    tether_ref = f"benchmark:tether:{label}"
    tool_spec_ref = f"benchmark:connector:{label}:tool"
    anchor_spec_ref = f"benchmark:connector:{label}:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"benchmark:component:{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=capacity_kg,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id=f"benchmark:endpoint:{label}:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id=f"benchmark:endpoint:{label}:anchor",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec_ref,
            ),
        ],
        connector_specs={
            tool_spec_ref: ConnectorSpec(
                connector_spec_id=tool_spec_ref,
                opening_action_count=2,
            ),
            anchor_spec_ref: ConnectorSpec(
                connector_spec_id=anchor_spec_ref,
                opening_action_count=2,
            ),
        },
    )


def _declared_anchor_tether() -> TetherOption:
    tether_ref = "benchmark:tether:manufacturer-declared"
    tool_spec_ref = "benchmark:connector:declared:tool"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref="benchmark:component:manufacturer-declared",
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="benchmark:endpoint:declared:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id="benchmark:endpoint:declared:anchor",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="clip",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref="quick_clip",
            ),
        ],
        connector_specs={
            tool_spec_ref: ConnectorSpec(
                connector_spec_id=tool_spec_ref,
                opening_action_count=2,
            ),
            "quick_clip": ConnectorSpec(
                connector_spec_id="quick_clip",
                attributes={"opening_mechanism": "trigger_operated"},
            ),
        },
    )


def _unresolved_tool_connection_tether() -> TetherOption:
    tether_ref = "benchmark:tether:unresolved-tool-connection"
    tool_spec_ref = "benchmark:connector:plain-clip"
    anchor_spec_ref = "benchmark:connector:unresolved:anchor"
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref="benchmark:component:unresolved-tool-connection",
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="benchmark:endpoint:unresolved:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="clip",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id="benchmark:endpoint:unresolved:anchor",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec_ref,
            ),
        ],
        connector_specs={
            tool_spec_ref: ConnectorSpec(connector_spec_id=tool_spec_ref),
            anchor_spec_ref: ConnectorSpec(
                connector_spec_id=anchor_spec_ref,
                opening_action_count=2,
            ),
        },
    )


def _manufacturer_declared_ranked_selection_run() -> RecommendationRunResult:
    target = _resolved_d_ring_anchor()
    declared_tether = _declared_anchor_tether()
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref=declared_tether.tether_ref,
        endpoints=declared_tether.endpoints,
        target_owner_ref="benchmark:anchor-path",
        target_interfaces=[target],
        declarations=[_accepted_quick_clip_declaration()],
    )
    return run_recommendation(
        _tool(),
        [declared_tether, _carabiner_tether("runtime-control", capacity_kg=5.0)],
        [_anchor_path(target)],
        connection_contexts=contexts,
    )


def _complete_hard_exhaustion_run() -> RecommendationRunResult:
    target = _resolved_d_ring_anchor()
    return run_recommendation(
        _tool(),
        [
            _carabiner_tether("under-capacity", capacity_kg=1.0),
            _unresolved_tool_connection_tether(),
        ],
        [_anchor_path(target)],
    )


def _tool_attachment_feature_bound_selection_run() -> tuple[
    RecommendationRunResult,
    ResolvedToolCandidate,
]:
    tool = _resolved_surface_tool()
    target = _resolved_d_ring_anchor()
    result = run_recommendation(
        tool,
        [_carabiner_tether("tool-attachment", capacity_kg=5.0)],
        [_anchor_path(target)],
        tool_attachment_assemblies=[_surface_attachment_assembly()],
    )
    return result, tool


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def _mapping_keys(value) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(_mapping_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for nested in value:
            keys.update(_mapping_keys(nested))
        return keys
    return set()


def _assert_complete_provenance(result: RecommendationRunResult) -> None:
    generated_ids = {
        candidate.configuration.candidate_id for candidate in result.generated_candidates
    }
    evaluation_ids = {evaluation.candidate_id for evaluation in result.evaluations}
    partitioned = [
        *result.selection.ranked_viable_candidates,
        *result.selection.contextually_infeasible_candidates,
        *result.selection.blocked_candidates,
    ]
    partition_ids = {candidate.candidate_id for candidate in partitioned}

    assert len(generated_ids) == len(result.generated_candidates)
    assert len(evaluation_ids) == len(result.evaluations)
    assert generated_ids == evaluation_ids == partition_ids
    for candidate in partitioned:
        assert candidate.generated_candidate in result.generated_candidates
        assert candidate.evaluation in result.evaluations


def _selection_summary(result: RecommendationRunResult) -> dict:
    summary = {
        "generated_count": len(result.generated_candidates),
        "evaluation_count": len(result.evaluations),
        "selection_state": result.selection.state.value,
        "ranked_viable_count": len(result.selection.ranked_viable_candidates),
        "blocked_count": len(result.selection.blocked_candidates),
    }
    if result.selection.selected is None:
        return summary

    selected = result.selection.selected
    anchor_connection = selected.generated_candidate.configuration.anchor_side_connection
    summary.update(
        {
            "selected_recommendation_state": selected.evaluation.recommendation_state.value,
            "selected_pending_verification_count": len(
                selected.evaluation.pending_verification_connection_ids
            ),
            "selected_anchor_status": anchor_connection.status.value,
            "selected_anchor_basis": anchor_connection.basis.value,
            "selected_anchor_issuer_manufacturer": (
                anchor_connection.manufacturer_assessments[0].issuer_manufacturer
                if anchor_connection.manufacturer_assessments
                else None
            ),
        }
    )
    if len(result.selection.ranked_viable_candidates) > 1:
        summary["runner_up_pending_verification_count"] = len(
            result.selection.ranked_viable_candidates[
                1
            ].evaluation.pending_verification_connection_ids
        )
    return summary


def _tool_attachment_summary(
    result: RecommendationRunResult,
    tool: ResolvedToolCandidate,
) -> dict:
    selected = result.selection.selected
    assert selected is not None

    generated = selected.generated_candidate
    selection = generated.selection
    configuration = generated.configuration
    selected_feature_id = selection.installation_feature_id
    assert selected_feature_id is not None

    feature_by_id = {feature.feature_id: feature for feature in tool.features}
    selected_feature = feature_by_id[selected_feature_id]
    product_constraints = configuration.product_constraint_evaluations

    return {
        "generated_count": len(result.generated_candidates),
        "evaluation_count": len(result.evaluations),
        "selection_state": result.selection.state.value,
        "ranked_viable_count": len(result.selection.ranked_viable_candidates),
        "blocked_count": len(result.selection.blocked_candidates),
        "selected_recommendation_state": selected.evaluation.recommendation_state.value,
        "selected_pending_verification_count": len(
            selected.evaluation.pending_verification_connection_ids
        ),
        "selected_attachment_mode": configuration.attachment_mode.value,
        "selected_binding_names": sorted(
            proof.binding_name for proof in selection.eligibility_proofs
        ),
        "selected_surface_profile": selected_feature.attributes["surface_profile"],
        "selected_constraint_statuses": {
            evaluation.constraint_key: evaluation.status.value
            for evaluation in product_constraints
        },
        "selected_all_constraints_bound_to_selected_feature": all(
            evaluation.installation_feature_id == selected_feature_id
            for evaluation in product_constraints
        ),
        "selected_tool_target_role": configuration.tool_side_connection.target_role.value,
        "selected_component_roles": [
            component.role.value for component in selection.components
        ],
    }


def test_recommendation_golden_is_semantic_answer_key_not_product_configuration():
    keys = _mapping_keys(_load_golden())
    prohibited = {
        key
        for key in keys
        if key in PROHIBITED_GOLDEN_IDENTITY_KEYS
        or key.endswith(PROHIBITED_GOLDEN_IDENTITY_SUFFIXES)
    }
    assert prohibited == set()


def test_manufacturer_declared_path_ranks_end_to_end_from_accepted_evidence():
    expected = _load_golden()["scenarios"]["manufacturer_declared_ranked_selection"]
    result = _manufacturer_declared_ranked_selection_run()

    _assert_complete_provenance(result)
    actual = _selection_summary(result)
    assert actual == expected

    selected = result.selection.selected
    assert selected is not None
    assert selected == result.selection.ranked_viable_candidates[0]
    assert selected.generated_candidate.selection.tether_ref == "benchmark:tether:manufacturer-declared"


def test_complete_evaluated_set_can_conclude_no_suitable_recommendation():
    expected = _load_golden()["scenarios"]["complete_hard_exhaustion"]
    result = _complete_hard_exhaustion_run()

    _assert_complete_provenance(result)
    expected_summary = {
        key: value
        for key, value in expected.items()
        if key != "blocked_candidate_semantics"
    }
    assert _selection_summary(result) == expected_summary

    blocked_by_tether_ref = {
        candidate.generated_candidate.selection.tether_ref: candidate
        for candidate in result.selection.blocked_candidates
    }
    scenario_bindings = {
        "under_capacity": "benchmark:tether:under-capacity",
        "unresolved_tool_connection": "benchmark:tether:unresolved-tool-connection",
    }
    assert set(blocked_by_tether_ref) == set(scenario_bindings.values())

    for scenario_role, tether_ref in scenario_bindings.items():
        candidate = blocked_by_tether_ref[tether_ref]
        blocking_semantics = {
            (check.check_type.value, check.status.value)
            for check in candidate.evaluation.checks
            if check.status.value in {"failed", "unresolved"}
        }
        required = expected["blocked_candidate_semantics"][scenario_role]
        assert blocking_semantics == {(required["check_type"], required["status"])}

    assert len(result.generated_candidates) == len(result.evaluations) == 2
    assert all(evaluation.recommendation_state is None for evaluation in result.evaluations)


def test_tool_attachment_path_preserves_feature_bound_constraints_through_selection():
    expected = _load_golden()["scenarios"]["tool_attachment_feature_bound_selection"]
    result, tool = _tool_attachment_feature_bound_selection_run()

    _assert_complete_provenance(result)
    expected_summary = {
        key: value
        for key, value in expected.items()
        if key != "blocked_candidate_semantics"
    }
    assert _tool_attachment_summary(result, tool) == expected_summary

    selected = result.selection.selected
    assert selected is not None
    assert selected == result.selection.ranked_viable_candidates[0]

    feature_by_id = {feature.feature_id: feature for feature in tool.features}
    blocked = result.selection.blocked_candidates
    assert len(blocked) == 1
    blocked_candidate = blocked[0]
    blocked_selection = blocked_candidate.generated_candidate.selection
    blocked_feature_id = blocked_selection.installation_feature_id
    assert blocked_feature_id is not None

    required = expected["blocked_candidate_semantics"]["installation_surface_mismatch"]
    blocked_feature = feature_by_id[blocked_feature_id]
    assert blocked_feature.attributes["surface_profile"] == required["surface_profile"]

    blocking_semantics = {
        (check.check_type.value, check.status.value)
        for check in blocked_candidate.evaluation.checks
        if check.status.value in {"failed", "unresolved"}
    }
    assert blocking_semantics == {(required["check_type"], required["status"])}

    failed_constraints = [
        evaluation
        for evaluation in blocked_candidate.generated_candidate.configuration.product_constraint_evaluations
        if evaluation.status.value == "failed"
    ]
    assert len(failed_constraints) == 1
    failed_constraint = failed_constraints[0]
    assert failed_constraint.constraint_key == required["constraint_key"]
    assert (
        failed_constraint.installation_feature_id == blocked_selection.installation_feature_id
    ) is required["constraint_bound_to_selected_feature"]
