import pytest

from tetherlens_ingest.candidate_generation import (
    AnchorPathOption,
    CandidateComponentOption,
    ResolvedToolCandidate,
    TetherOption,
    generate_candidate_configurations,
)
from tetherlens_ingest.connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionStatus,
    ConnectorSpec,
    TetherSide,
)
from tetherlens_ingest.endpoint_assignment import (
    EndpointAssignmentSemantics,
    TetherEndpointAssignmentDeclaration,
    resolve_tether_endpoint_assignment_declarations,
)
from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType
from tetherlens_ingest.recommendation import evaluate_candidate_configuration


TETHER_REF = "product:tether-reversible"
SOURCE_URL = "https://manufacturer.test/reversible-tether"
SUPPORTING_URL = "https://manufacturer.test/reversible-tether-instructions"


def assignment_claims(
    *,
    declaration_id: str = "assignment:reversible-pair",
    members: tuple[str, ...] = ("end_a", "end_b"),
) -> list[CandidateClaim]:
    values = [
        *[("endpoint_assignment.member_ref", member) for member in members],
        ("endpoint_assignment.semantics", "reversible_tool_anchor_pair"),
        ("endpoint_assignment.issuer_manufacturer", "Example Manufacturer"),
        ("endpoint_assignment.scope", "Either tether end may serve tool or anchor side"),
    ]
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT,
            subject_ref=declaration_id,
            property_key=key,
            value=value,
            source_url=SOURCE_URL,
            supporting_source_urls=[SUPPORTING_URL] if key == "endpoint_assignment.semantics" else [],
            extractor="test",
        )
        for key, value in values
    ]


def declaration(
    *,
    declaration_id: str = "assignment:reversible-pair",
    tether_ref: str = TETHER_REF,
) -> TetherEndpointAssignmentDeclaration:
    return resolve_tether_endpoint_assignment_declarations(
        assignment_claims(declaration_id=declaration_id),
        tether_ref=tether_ref,
    )[0]


def endpoint(endpoint_id: str, side: TetherSide) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=endpoint_id,
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        tether_side=side,
        connector_spec_ref="shared_connector",
    )


def tether(
    *,
    sides: tuple[TetherSide, TetherSide] = (TetherSide.UNKNOWN, TetherSide.UNKNOWN),
    declarations: list[TetherEndpointAssignmentDeclaration] | None = None,
) -> TetherOption:
    return TetherOption(
        tether_ref=TETHER_REF,
        component=CandidateComponentOption(
            component_ref="component:tether",
            source_product_ref=TETHER_REF,
            rated_capacity_kg=5.0,
        ),
        endpoints=[endpoint("end_a", sides[0]), endpoint("end_b", sides[1])],
        connector_specs={
            "shared_connector": ConnectorSpec(
                connector_spec_id="shared_connector",
                opening_action_count=2,
            )
        },
        endpoint_assignment_declarations=list(declarations or []),
        max_length_mm=1200.0,
    )


def tool() -> ResolvedToolCandidate:
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


def anchor() -> AnchorPathOption:
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


def test_resolver_retains_relation_members_owner_and_source_provenance():
    resolved = resolve_tether_endpoint_assignment_declarations(
        assignment_claims(),
        tether_ref=TETHER_REF,
    )

    assert len(resolved) == 1
    out = resolved[0]
    assert out.declaration_id == "assignment:reversible-pair"
    assert out.tether_ref == TETHER_REF
    assert out.endpoint_refs == ["end_a", "end_b"]
    assert out.semantics == EndpointAssignmentSemantics.REVERSIBLE_TOOL_ANCHOR_PAIR
    assert out.issuer_manufacturer == "Example Manufacturer"
    assert out.scope == "Either tether end may serve tool or anchor side"
    assert out.source_urls == sorted([SOURCE_URL, SUPPORTING_URL])


def test_resolver_requires_exactly_two_distinct_members():
    with pytest.raises(ValueError, match="exactly two distinct endpoint members"):
        resolve_tether_endpoint_assignment_declarations(
            assignment_claims(members=("end_a", "end_a")),
            tether_ref=TETHER_REF,
        )

    with pytest.raises(ValueError, match="exactly two distinct endpoint members"):
        resolve_tether_endpoint_assignment_declarations(
            assignment_claims(members=("end_a", "end_b", "end_c")),
            tether_ref=TETHER_REF,
        )


def test_identical_unknown_hardware_alone_does_not_create_endpoint_assignments():
    generated = generate_candidate_configurations(tool(), [tether()], [anchor()])
    assert generated == []


def test_reversible_declaration_generates_both_orientations_without_promoting_roles():
    generated = generate_candidate_configurations(
        tool(),
        [tether(declarations=[declaration()])],
        [anchor()],
    )

    assert len(generated) == 2
    assert {
        (candidate.selection.tool_endpoint_id, candidate.selection.anchor_endpoint_id)
        for candidate in generated
    } == {("end_a", "end_b"), ("end_b", "end_a")}
    assert len({candidate.configuration.candidate_id for candidate in generated}) == 2

    for candidate in generated:
        assert candidate.configuration.tool_side_connection.endpoint_tether_side == TetherSide.UNKNOWN
        assert candidate.configuration.anchor_side_connection.endpoint_tether_side == TetherSide.UNKNOWN
        assert len(candidate.selection.endpoint_assignment_proofs) == 1
        proof = candidate.selection.endpoint_assignment_proofs[0]
        assert proof.declaration_id == "assignment:reversible-pair"
        assert proof.source_urls == sorted([SOURCE_URL, SUPPORTING_URL])


def test_assignment_evidence_does_not_create_connection_compatibility():
    unknown_clip = tether(declarations=[declaration()]).model_copy(
        update={
            "endpoints": [
                ConnectionInterface(
                    interface_id="end_a",
                    role=ConnectionInterfaceRole.TETHER_CONNECTION,
                    interface_type="clip",
                    tether_side=TetherSide.UNKNOWN,
                ),
                ConnectionInterface(
                    interface_id="end_b",
                    role=ConnectionInterfaceRole.TETHER_CONNECTION,
                    interface_type="clip",
                    tether_side=TetherSide.UNKNOWN,
                ),
            ],
            "connector_specs": {},
        }
    )

    generated = generate_candidate_configurations(tool(), [unknown_clip], [anchor()])
    assert len(generated) == 2

    for candidate in generated:
        evaluation = evaluate_candidate_configuration(candidate.configuration)
        assert evaluation.recommendation_state is None
        assert all(
            connection.status == ConnectionStatus.UNRESOLVED
            for connection in evaluation.connections
        )


def test_reversible_declaration_does_not_override_explicit_fixed_roles():
    generated = generate_candidate_configurations(
        tool(),
        [
            tether(
                sides=(TetherSide.TOOL_SIDE, TetherSide.ANCHOR_SIDE),
                declarations=[declaration()],
            )
        ],
        [anchor()],
    )

    assert len(generated) == 1
    candidate = generated[0]
    assert candidate.selection.tool_endpoint_id == "end_a"
    assert candidate.selection.anchor_endpoint_id == "end_b"
    assert candidate.selection.endpoint_assignment_proofs == []


def test_reversible_declaration_does_not_fill_a_partially_known_pair():
    generated = generate_candidate_configurations(
        tool(),
        [
            tether(
                sides=(TetherSide.TOOL_SIDE, TetherSide.UNKNOWN),
                declarations=[declaration()],
            )
        ],
        [anchor()],
    )
    assert generated == []


def test_declaration_ownership_and_endpoint_membership_fail_closed():
    with pytest.raises(ValueError, match="owning tether identity"):
        tether(declarations=[declaration(tether_ref="product:other-tether")])

    outside = declaration().model_copy(update={"endpoint_refs": ["end_a", "missing_end"]})
    with pytest.raises(ValueError, match="outside its tether"):
        tether(declarations=[outside])


def test_multiple_declarations_are_proofs_not_duplicate_candidate_identity():
    first = declaration(declaration_id="assignment:first")
    second = declaration(declaration_id="assignment:second")

    one_proof = generate_candidate_configurations(
        tool(),
        [tether(declarations=[first])],
        [anchor()],
    )
    two_proofs = generate_candidate_configurations(
        tool(),
        [tether(declarations=[second, first])],
        [anchor()],
    )

    assert len(one_proof) == 2
    assert len(two_proofs) == 2
    assert {
        candidate.configuration.candidate_id for candidate in one_proof
    } == {
        candidate.configuration.candidate_id for candidate in two_proofs
    }
    assert all(
        [proof.declaration_id for proof in candidate.selection.endpoint_assignment_proofs]
        == ["assignment:first", "assignment:second"]
        for candidate in two_proofs
    )
