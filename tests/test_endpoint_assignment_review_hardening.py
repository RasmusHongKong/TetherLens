import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    GeneratedCandidate,
    ResolvedToolCandidate,
    TetherOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentSemantics,
    TetherEndpointAssignmentDeclaration,
)
from tetherlens_ingest.recommendation import CandidateConfiguration


TETHER_REF = "product:tether-review-hardening"


def _endpoint(endpoint_id: str, side: TetherSide) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=endpoint_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref="shared_connector",
    )


def _declaration(*, tether_ref: str = TETHER_REF) -> TetherEndpointAssignmentDeclaration:
    return TetherEndpointAssignmentDeclaration(
        declaration_id="assignment:reversible-pair",
        tether_ref=tether_ref,
        endpoint_refs=["end_a", "end_b"],
        semantics=EndpointAssignmentSemantics.REVERSIBLE_TOOL_ANCHOR_PAIR,
        issuer_manufacturer="Example Manufacturer",
        scope="Either tether end may serve tool or anchor side",
        source_urls=["https://manufacturer.test/reversible-tether"],
    )


def _tether(
    *,
    sides: tuple[TetherSide, TetherSide],
    include_declaration: bool = True,
) -> TetherOption:
    return TetherOption(
        tether_ref=TETHER_REF,
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref=TETHER_REF,
            rated_capacity_kg=5.0,
        ),
        endpoints=[_endpoint("end_a", sides[0]), _endpoint("end_b", sides[1])],
        connector_specs={
            "shared_connector": ConnectorSpec(
                connector_spec_id="shared_connector",
                opening_action_count=2,
            )
        },
        endpoint_assignment_declarations=[_declaration()] if include_declaration else [],
        max_length_mm=1200.0,
    )


def _tool() -> ResolvedToolCandidate:
    return ResolvedToolCandidate(
        tool_ref="tool:1",
        object_mass_kg=2.0,
        direct_interfaces=[
            ConnectionInterface(
                interface_id="tool_ring",
                role=ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
                interface_type="ring",
            )
        ],
    )


def _anchor() -> AnchorPathOption:
    return AnchorPathOption(
        anchor_path_ref="anchor:path",
        target_interfaces=[
            ConnectionInterface(
                interface_id="anchor_ring",
                role=ConnectionInterfaceRole.CONTAINER_CONNECTION,
                interface_type="ring",
            )
        ],
    )


def _relation_candidate() -> GeneratedCandidate:
    generated = generate_candidate_configurations(
        _tool(),
        [_tether(sides=(TetherSide.UNKNOWN, TetherSide.UNKNOWN))],
        [_anchor()],
    )
    assert len(generated) == 2
    return generated[0]


def test_configuration_rejects_endpoint_assignment_declaration_owned_by_another_tether():
    candidate = _relation_candidate()
    payload = candidate.configuration.model_dump(mode="json")
    payload["endpoint_assignment_declarations"][0]["tether_ref"] = "product:other-tether"

    with pytest.raises(ValueError, match="belong to the selected tether"):
        CandidateConfiguration.model_validate(payload)


def test_rehydrated_generated_candidate_rejects_missing_assignment_proof():
    candidate = _relation_candidate()
    payload = candidate.model_dump(mode="json")
    payload["selection"]["endpoint_assignment_proofs"] = []

    with pytest.raises(ValueError, match="assignment proofs do not match configuration"):
        GeneratedCandidate.model_validate(payload)


def test_rehydrated_generated_candidate_rejects_forged_assignment_provenance():
    candidate = _relation_candidate()
    payload = candidate.model_dump(mode="json")
    payload["selection"]["endpoint_assignment_proofs"][0]["issuer_manufacturer"] = "Other Manufacturer"

    with pytest.raises(ValueError, match="assignment proofs do not match configuration"):
        GeneratedCandidate.model_validate(payload)


def test_fixed_role_candidate_rejects_bogus_assignment_proof():
    generated = generate_candidate_configurations(
        _tool(),
        [_tether(sides=(TetherSide.TOOL_SIDE, TetherSide.ANCHOR_SIDE))],
        [_anchor()],
    )
    assert len(generated) == 1
    assert generated[0].configuration.endpoint_assignment_declarations == []
    assert generated[0].selection.endpoint_assignment_proofs == []

    relation_proof = _relation_candidate().selection.endpoint_assignment_proofs[0]
    payload = generated[0].model_dump(mode="json")
    payload["selection"]["endpoint_assignment_proofs"] = [
        relation_proof.model_dump(mode="json")
    ]

    with pytest.raises(ValueError, match="assignment proofs do not match configuration"):
        GeneratedCandidate.model_validate(payload)
