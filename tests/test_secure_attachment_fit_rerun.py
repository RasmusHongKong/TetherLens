from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ProductConstraintRuntimeState,
    ResolvedToolCandidate,
    TetherOption,
    ToolAttachmentAssemblyOption,
)
from tetherlens_ingest.compatibility import (
    AttachmentEligibility,
    CaptiveState,
    EligibilityPath,
    FeatureKind,
    FeaturePredicate,
    ToolInterfaceFeature,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.constraints import (
    ProductConstraintDisposition,
    ProductConstraintStatus,
    ResolvedProductConstraint,
)
from tetherlens_ingest.models import ClaimSubjectType, ConstraintOperator
from tetherlens_ingest.recommendation_run import run_recommendation


def _endpoint(
    endpoint_id: str,
    *,
    side: TetherSide,
    connector_spec_ref: str,
) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=endpoint_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref=connector_spec_ref,
    )


def test_failed_secure_fit_runtime_state_blocks_candidate_on_rerun() -> None:
    constraint = ResolvedProductConstraint(
        constraint_id="attachment:1:product:self:secure_attachment_fit_required:1",
        source_product_ref="attachment:1",
        subject_type=ClaimSubjectType.PRODUCT,
        subject_ref="self",
        constraint_key="secure_attachment_fit_required",
        operator=ConstraintOperator.REQUIRES,
        value=True,
        disposition=ProductConstraintDisposition.PRE_USE_OBLIGATION,
    )
    tool = ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=0.25,
        features=[
            ToolInterfaceFeature(
                feature_id="feature:handle",
                feature_kind=FeatureKind.HANDLE,
                captive_state=CaptiveState.NON_CAPTIVE,
            )
        ],
    )
    attachment = ToolAttachmentAssemblyOption(
        assembly_ref="assembly:1",
        components=[
            CandidateComponentOption(
                component_ref="component:attachment",
                source_product_ref="attachment:1",
                rated_capacity_kg=0.5,
                product_constraints=[constraint],
            )
        ],
        eligibility=AttachmentEligibility(
            paths=[
                EligibilityPath(
                    binding_name="handle",
                    requirements=[
                        FeaturePredicate(
                            property_key="feature_kind",
                            value=FeatureKind.HANDLE.value,
                        )
                    ],
                )
            ]
        ),
        provided_interfaces=[
            ConnectionInterface(
                interface_id="attachment:ring",
                role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
                interface_type="ring",
            )
        ],
    )
    tether = TetherOption(
        tether_ref="tether:1",
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref="tether:1",
            rated_capacity_kg=1.0,
        ),
        endpoints=[
            _endpoint(
                "tether:tool-end",
                side=TetherSide.TOOL_SIDE,
                connector_spec_ref="connector:tool",
            ),
            _endpoint(
                "tether:anchor-end",
                side=TetherSide.ANCHOR_SIDE,
                connector_spec_ref="connector:anchor",
            ),
        ],
        connector_specs={
            "connector:tool": ConnectorSpec(
                connector_spec_id="connector:tool",
                opening_action_count=2,
            ),
            "connector:anchor": ConnectorSpec(
                connector_spec_id="connector:anchor",
                opening_action_count=2,
            ),
        },
        max_length_mm=1200.0,
    )
    anchor = AnchorPathOption(
        anchor_path_ref="anchor:1",
        target_interfaces=[
            ConnectionInterface(
                interface_id="anchor:ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )

    run = run_recommendation(
        tool,
        [tether],
        [anchor],
        tool_attachment_assemblies=[attachment],
        product_runtime_state=[
            ProductConstraintRuntimeState(
                component_ref="component:attachment",
                installation_feature_id="feature:handle",
                secure_attachment_fit_confirmed=False,
            )
        ],
    )

    assert len(run.generated_candidates) == 1
    constraint_evaluation = next(
        item
        for item in run.generated_candidates[0].configuration.product_constraint_evaluations
        if item.constraint_key == "secure_attachment_fit_required"
    )
    assert constraint_evaluation.status == ProductConstraintStatus.FAILED
    assert run.evaluations[0].recommendation_state is None
    assert run.selection.ranked_viable_candidates == []
    assert [item.candidate_id for item in run.selection.blocked_candidates] == [
        run.generated_candidates[0].configuration.candidate_id
    ]
