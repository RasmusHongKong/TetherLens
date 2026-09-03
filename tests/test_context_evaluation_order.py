from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
)
from tetherlens_ingest.candidate_selection import (
    CandidateRankingContext,
    rank_and_select_candidates,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import (
    ProductConstraintDisposition,
    ResolvedProductConstraint,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ConstraintOperator,
)
from tetherlens_ingest.recommendation_run import run_recommendation


EXPOSURE = "salt_spray"


def _tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        direct_interfaces=[
            ConnectionInterface(
                interface_id="tool:ring",
                role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                interface_type="ring",
            )
        ],
    )


def _anchor_path() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path-1",
        components=[
            CandidateComponentOption(
                component_ref="component:anchor-1",
                source_product_ref="product:anchor-1",
                rated_capacity_kg=5.0,
            )
        ],
        target_interfaces=[
            ConnectionInterface(
                interface_id="container:ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )


def _tether(label: str, *, prohibited: bool) -> TetherOption:
    tether_ref = f"product:tether-{label}"
    tool_spec_ref = f"{tether_ref}:connector:tool"
    anchor_spec_ref = f"{tether_ref}:connector:anchor"
    constraints = []
    if prohibited:
        constraints = [
            ResolvedProductConstraint(
                constraint_id=f"{tether_ref}:product:self:prohibited_exposure:1",
                source_product_ref=tether_ref,
                subject_type=ClaimSubjectType.PRODUCT,
                subject_ref="self",
                constraint_key="prohibited_exposure",
                operator=ConstraintOperator.PROHIBITS,
                value=EXPOSURE,
                disposition=ProductConstraintDisposition.CONTEXTUAL,
                source_urls=["https://example.test/manufacturer/tether"],
            )
        ]
    return TetherOption(
        tether_ref=tether_ref,
        component=CandidateComponentOption(
            component_ref=f"component:tether-{label}",
            source_product_ref=tether_ref,
            rated_capacity_kg=5.0,
            product_constraints=constraints,
        ),
        endpoints=[
            ConnectionInterface(
                interface_id=f"endpoint:{label}:tool",
                role=ConnectionInterfaceRole.TETHER_CONNECTION,
                interface_type="carabiner",
                tether_side=TetherSide.TOOL_SIDE,
                connector_spec_ref=tool_spec_ref,
            ),
            ConnectionInterface(
                interface_id=f"endpoint:{label}:anchor",
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
        min_length_mm=400.0,
        max_length_mm=1200.0,
    )


def test_context_evaluations_are_canonical_when_input_order_changes():
    run = run_recommendation(
        _tool(),
        [
            _tether("z-unknown", prohibited=False),
            _tether("a-prohibited", prohibited=True),
        ],
        [_anchor_path()],
    )
    context = CandidateRankingContext(environmental_exposures=[EXPOSURE])

    forward = rank_and_select_candidates(
        run.generated_candidates,
        run.evaluations,
        ranking_context=context,
    )
    reversed_input = rank_and_select_candidates(
        list(reversed(run.generated_candidates)),
        list(reversed(run.evaluations)),
        ranking_context=context,
    )

    assert forward.context_evaluations == reversed_input.context_evaluations
    ids = [evaluation.candidate_id for evaluation in forward.context_evaluations]
    assert ids == sorted(ids)
