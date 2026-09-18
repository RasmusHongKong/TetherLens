from tetherlens_ingest.adapters import GRIPPSAdapter
from tetherlens_ingest.anchor_claim_resolution import (
    resolve_anchor_attachment_installation_rule,
)
from tetherlens_ingest.anchor_installation import (
    PrimaryAnchorFeature,
    PrimaryAnchorFeatureKind,
    ResolvedPrimaryAnchor,
    bound_anchor_installation_evaluation,
    resolve_anchor_installation_bindings,
)
from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
)
from tetherlens_ingest.connection import (
    CompatibilityBasis,
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
)
from tetherlens_ingest.declared_compatibility import (
    connection_contexts_from_compatibility_declarations,
    resolve_connector_interface_compatibility_declarations,
)
from tetherlens_ingest.endpoint_assignment import (
    resolve_tether_endpoint_assignment_declarations,
)
from tetherlens_ingest.models import (
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.recommendation import RecommendationState
from tetherlens_ingest.recommendation_run import run_recommendation
from tetherlens_ingest.resolution import (
    resolve_connection_interfaces,
    resolve_connector_specs,
)


TETHER_REF = "GRIPPS:H01067"
ANCHOR_REF = "GRIPPS:H01085-M"


def _artifact(url: str, body: str) -> SourceArtifact:
    return SourceArtifact(
        url=url,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _capacity(claims) -> float:
    return next(
        float(claim.value)
        for claim in claims
        if claim.property_key == "rated_capacity_kg"
    )


def test_h01067_h01085_m_flows_through_ordinary_tether_and_anchor_path() -> None:
    tether_identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.TETHER,
        name="Webbing Wrist Tether Single-Action",
        sku="H01067",
        url="https://gripps.com/products/webbing-single-action-wrist-tether",
    )
    tether_claims = GRIPPSAdapter().extract(
        tether_identity,
        [
            _artifact(
                tether_identity.url,
                """
                <h1>Webbing Wrist Tether Single-Action - 2.5kg / 5.5lb</h1>
                <p>SKU H01067</p>
                <p>This tether facilitates secure attachment of hand tools to GRIPPS
                gloves or wrist anchors.</p>
                <p>Two swivel-head single-action carabiners.</p>
                <p>Max Load: 2.5 kg | 5.5 lb</p>
                """,
            )
        ],
    )
    tether = TetherOption(
        tether_ref=TETHER_REF,
        component=CandidateComponentOption(
            component_ref=f"{TETHER_REF}:component",
            source_product_ref=TETHER_REF,
            rated_capacity_kg=_capacity(tether_claims),
        ),
        endpoints=resolve_connection_interfaces(tether_claims),
        connector_specs=resolve_connector_specs(tether_claims),
        endpoint_assignment_declarations=resolve_tether_endpoint_assignment_declarations(
            tether_claims,
            tether_ref=TETHER_REF,
        ),
    )

    anchor_identity = ProductIdentity(
        manufacturer="GRIPPS",
        product_type=ProductType.ANCHOR_ATTACHMENT,
        name="Slip-On Wrist Anchor",
        sku="H01085-M",
        url="https://gripps.com/products/slip-on-wrist-anchor",
    )
    anchor_claims = GRIPPSAdapter().extract(
        anchor_identity,
        [
            _artifact(
                anchor_identity.url,
                """
                <h1>Slip-On Wrist Anchor - 2.5kg / 5.5lb</h1>
                <p>SKU: H01085-M</p>
                <p>The GRIPPS Slip-On Wrist Anchor is a wrist-mounted tether anchor.</p>
                <p>Just slip it on, secure your tool, and start your task.</p>
                <p>Suitable for use with our H01060, H01062 and H01067 wrist tethers.</p>
                <p>Built-in load-rated tether anchor point.</p>
                <p>Max Load: 2.5 kg | 5.5 lb</p>
                """,
            )
        ],
    )
    anchor_rule = resolve_anchor_attachment_installation_rule(
        anchor_claims,
        source_product_ref=ANCHOR_REF,
    )
    assert anchor_rule is not None
    primary_anchor = ResolvedPrimaryAnchor(
        primary_anchor_ref="worker:wrist",
        features=[
            PrimaryAnchorFeature(
                feature_id="worker:wrist",
                feature_kind=PrimaryAnchorFeatureKind.WRIST,
            )
        ],
    )
    bindings = resolve_anchor_installation_bindings(anchor_rule, primary_anchor)
    assert len(bindings) == 1
    binding = bindings[0]
    anchor_path = AnchorPathOption(
        anchor_path_ref=f"{ANCHOR_REF}:wrist-path",
        components=[
            CandidateComponentOption(
                component_ref=f"{ANCHOR_REF}:component",
                source_product_ref=ANCHOR_REF,
                rated_capacity_kg=_capacity(anchor_claims),
            )
        ],
        target_interfaces=resolve_connection_interfaces(anchor_claims),
        installation_binding=binding,
        installation_eligibility=bound_anchor_installation_evaluation(binding),
    )

    declarations = resolve_connector_interface_compatibility_declarations(
        anchor_claims,
        product_refs_by_identifier={
            "H01067": TETHER_REF,
            "H01085-M": ANCHOR_REF,
        },
    )
    assert len(declarations) == 1
    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref=tether.tether_ref,
        endpoints=tether.endpoints,
        target_owner_ref=anchor_path.anchor_path_ref,
        target_interfaces=anchor_path.target_interfaces,
        declarations=declarations,
        tether_product_ref=TETHER_REF,
        target_product_refs={ANCHOR_REF},
    )

    result = run_recommendation(
        ResolvedToolCandidate(
            tool_ref="tool:wrist-path-proof",
            object_mass_kg=1.0,
            direct_interfaces=[
                ConnectionInterface(
                    interface_id="tool:ring",
                    role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                    interface_type="ring",
                )
            ],
        ),
        [tether],
        [anchor_path],
        connection_contexts=contexts,
    )

    # H01067's accepted reversible endpoint semantics create one candidate per valid
    # orientation. The exact product-scoped GRIPPS statement closes only the anchor-side
    # sparse-geometry gap; it does not manufacture a generic wrist-anchor interface class.
    assert len(result.generated_candidates) == 2
    assert all(
        candidate.configuration.anchor_side_connection.status == ConnectionStatus.COMPATIBLE
        and candidate.configuration.anchor_side_connection.basis
        == CompatibilityBasis.MANUFACTURER_DECLARED
        for candidate in result.generated_candidates
    )
    assert all(
        candidate.configuration.tool_side_connection.status
        == ConnectionStatus.REQUIRES_VERIFICATION
        for candidate in result.generated_candidates
    )
    assert all(
        candidate.selection.anchor_installation_binding is not None
        and candidate.selection.anchor_installation_binding.source_product_ref == ANCHOR_REF
        and candidate.selection.anchor_installation_binding.installation_feature_id
        == "worker:wrist"
        for candidate in result.generated_candidates
    )
    assert all(
        {component.source_product_ref for component in candidate.selection.components}
        == {TETHER_REF, ANCHOR_REF}
        for candidate in result.generated_candidates
    )
    assert all(
        evaluation.recommendation_state
        == RecommendationState.RECOMMENDED_WITH_CONSTRAINTS
        for evaluation in result.evaluations
    )
    assert result.selection.selected is not None
