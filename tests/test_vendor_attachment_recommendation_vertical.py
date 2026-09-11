from tetherlens_ingest.adapters import GRIPPSAdapter, ThreeMAdapter
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from tetherlens_ingest.compatibility import CaptiveState, FeatureKind, ToolInterfaceFeature
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import resolve_product_constraints
from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact, SourceType
from tetherlens_ingest.recommendation_run import run_recommendation
from tetherlens_ingest.resolution import (
    resolve_attachment_eligibility,
    resolve_connection_interfaces,
)


def _artifact(body: str, *, url: str, source_type=SourceType.MANUFACTURER_WEBPAGE):
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


def _assembly(product_ref: str, claims) -> ToolAttachmentAssemblyOption:
    eligibility = resolve_attachment_eligibility(claims)
    assert eligibility is not None
    provided_interfaces = resolve_connection_interfaces(claims)
    assert provided_interfaces
    capacity = next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )
    constraints = resolve_product_constraints(claims, source_product_ref=product_ref)
    return ToolAttachmentAssemblyOption(
        assembly_ref=f"{product_ref}:assembly",
        components=[
            CandidateComponentOption(
                component_ref=f"{product_ref}:component",
                source_product_ref=product_ref,
                rated_capacity_kg=capacity,
                product_constraints=constraints,
            )
        ],
        eligibility=eligibility,
        provided_interfaces=provided_interfaces,
    )


def _generic_tether() -> TetherOption:
    tool_spec = "generic:tether:tool-carabiner"
    anchor_spec = "generic:tether:anchor-carabiner"
    return TetherOption(
        tether_ref="generic:tether",
        component=CandidateComponentOption(
            component_ref="generic:tether:component",
            source_product_ref="generic:tether",
            rated_capacity_kg=5.0,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id="generic:tether:tool-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec,
            ),
            ConnectionInterface(
                interface_id="generic:tether:anchor-end",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref=anchor_spec,
            ),
        ],
        connector_specs={
            tool_spec: ConnectorSpec(connector_spec_id=tool_spec, opening_action_count=2),
            anchor_spec: ConnectorSpec(connector_spec_id=anchor_spec, opening_action_count=2),
        },
    )


def _generic_anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="generic:anchor-path",
        components=[
            CandidateComponentOption(
                component_ref="generic:anchor:component",
                source_product_ref="generic:anchor",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[
            ConnectionInterface(
                interface_id="generic:anchor:d-ring",
                role=ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
                interface_type="ring",
                attributes={"ring_form": "d_ring"},
            )
        ],
    )


def _run(tool: ResolvedToolCandidate, assembly: ToolAttachmentAssemblyOption):
    return run_recommendation(
        tool,
        [_generic_tether()],
        [_generic_anchor_path()],
        tool_attachment_assemblies=[assembly],
    )


def test_snaplock_vendor_claims_generate_only_handle_bound_attachment_candidates() -> None:
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
                "standardized connection point for tethering compatible tools. Its self-closing "
                "design allows fast installation to a tool's handle or neck. Max Load: 6.8 kg. "
                "Available in four sizes (S, M, L, XL).",
                url=identity.url,
            )
        ],
    )
    tool = ResolvedToolCandidate(
        tool_ref="tool:snaplock-proof",
        object_mass_kg=0.4,
        features=[
            ToolInterfaceFeature(
                feature_id="handle:non-captive",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="handle:captive",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.CAPTIVE,
            ),
            ToolInterfaceFeature(
                feature_id="section:neck",
                feature_kind=FeatureKind.EXTERNAL_SECTION,
                captive_state=CaptiveState.NON_CAPTIVE,
            ),
        ],
    )

    result = _run(tool, _assembly("GRIPPS:H01150", claims))

    assert len(result.generated_candidates) == 2
    assert {
        candidate.selection.installation_feature_id
        for candidate in result.generated_candidates
    } == {"handle:non-captive", "handle:captive"}
    assert all(
        candidate.configuration.attachment_eligibility.matches[0].feature_id
        == candidate.selection.installation_feature_id
        for candidate in result.generated_candidates
    )
    assert all(
        candidate.selection.installation_feature_id != "section:neck"
        for candidate in result.generated_candidates
    )


def test_quick_spin_vendor_constraints_remain_feature_bound_through_hard_evaluation() -> None:
    product_url = "https://www.3m.com/3M/en_LB/p/d/v100323604/"
    manual_url = (
        "https://multimedia.3m.com/mws/media/1300988O/"
        "ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf"
    )
    identity = ProductIdentity(
        manufacturer="3M",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="DBI-SALA Quick Spin Medium Size",
        sku="1500028",
        url=product_url,
    )
    claims = ThreeMAdapter().extract(
        identity,
        [
            _artifact(
                "Tangle-resistant spin top simply slides onto the handle of a tool in seconds. "
                "Quick Spin, 0.5 kg (1 lb.) capacity, 2 cm (0.80 in) diameter.",
                url=product_url,
            ),
            _artifact(
                "Do not use if a snug fit on the tool cannot be secured. "
                "Never attach tool lanyards or attachment points to a tapered surface. "
                "Ensure that the Quick Spin is firmly in place before use. "
                "A non-metallic attachment point is needed.",
                url=manual_url,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
            ),
        ],
    )
    tool = ResolvedToolCandidate(
        tool_ref="tool:quick-spin-proof",
        object_mass_kg=0.4,
        features=[
            ToolInterfaceFeature(
                feature_id="handle:cylindrical",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
                attributes={"surface_profile": "cylindrical"},
            ),
            ToolInterfaceFeature(
                feature_id="handle:tapered",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
                attributes={"surface_profile": "tapered"},
            ),
        ],
    )

    result = _run(tool, _assembly("3M:1500028", claims))

    assert len(result.generated_candidates) == 2
    by_feature = {
        candidate.selection.installation_feature_id: candidate
        for candidate in result.generated_candidates
    }
    cylindrical = by_feature["handle:cylindrical"]
    tapered = by_feature["handle:tapered"]

    cylindrical_constraints = {
        evaluation.constraint_key: evaluation
        for evaluation in cylindrical.configuration.product_constraint_evaluations
    }
    tapered_constraints = {
        evaluation.constraint_key: evaluation
        for evaluation in tapered.configuration.product_constraint_evaluations
    }

    assert cylindrical_constraints["prohibited_surface_profile"].status.value == "passed"
    assert tapered_constraints["prohibited_surface_profile"].status.value == "failed"
    assert cylindrical_constraints["secure_attachment_fit_required"].status.value == "requires_action"
    assert tapered_constraints["secure_attachment_fit_required"].status.value == "requires_action"
    assert all(
        evaluation.installation_feature_id == "handle:cylindrical"
        for evaluation in cylindrical_constraints.values()
    )
    assert all(
        evaluation.installation_feature_id == "handle:tapered"
        for evaluation in tapered_constraints.values()
    )

    evaluations_by_id = {evaluation.candidate_id: evaluation for evaluation in result.evaluations}
    cylindrical_eval = evaluations_by_id[cylindrical.configuration.candidate_id]
    tapered_eval = evaluations_by_id[tapered.configuration.candidate_id]

    cylindrical_product_checks = [
        check
        for check in cylindrical_eval.checks
        if check.check_type.value == "product_constraint"
    ]
    tapered_product_checks = [
        check
        for check in tapered_eval.checks
        if check.check_type.value == "product_constraint"
    ]
    assert {check.status.value for check in cylindrical_product_checks} == {
        "passed",
        "requires_action",
    }
    assert "failed" in {check.status.value for check in tapered_product_checks}

    # First-party text establishes an attachment point but not its normalized physical
    # interface form. The run therefore correctly refuses to invent full recommendation
    # readiness: the cylindrical path still has an unresolved connection check.
    assert any(
        check.check_type.value == "connection_compatibility"
        and check.status.value == "unresolved"
        for check in cylindrical_eval.checks
    )
    assert result.selection.selected is None
