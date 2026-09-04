import pytest

from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.connection import (
    CinchLoopClosedInterfaceVerification,
    CompatibilityBasis,
    ConnectionEvaluation,
    ConnectionStatus,
    GatedConnectorClosedInterfaceVerification,
    RuntimeVerificationStatus,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


def _artifact(body: str) -> SourceArtifact:
    return SourceArtifact(
        url="https://neverletgo.example/bungee-tool-lanyard",
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body=body,
    )


def _identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TETHER,
        name="Bungee Tool Lanyard",
        sku="101372",
        url="https://neverletgo.example/bungee-tool-lanyard",
    )


def _has_cinch_mechanism(body: str) -> bool:
    claims = NLGAdapter().extract(_identity(), [_artifact(body)])
    return any(
        claim.subject_type == ClaimSubjectType.CONNECTOR_SPEC
        and claim.property_key == "connector.attribute.engagement_method"
        and claim.value == "cinch"
        for claim in claims
    )


def _evaluation(*, family: str, observations):
    return ConnectionEvaluation(
        status=ConnectionStatus.REQUIRES_VERIFICATION,
        basis=CompatibilityBasis.RUNTIME_VERIFICATION,
        endpoint_id="endpoint:1",
        target_interface_id="target:1",
        reason="test runtime verification",
        verification_status=RuntimeVerificationStatus.PENDING,
        verification_family=family,
        verification_observations=observations,
    )


def test_negated_cinching_loop_assertion_does_not_emit_positive_mechanism():
    body = (
        "<p>The climbing cord loop is not a cinching loop and allows attachment to an "
        "anchor point.</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>"
    )

    assert not _has_cinch_mechanism(body)


def test_contracted_negation_also_does_not_emit_positive_mechanism():
    body = (
        "<p>The climbing cord loop isn't a cinching loop and allows attachment to an "
        "anchor point.</p>"
        "<p>The Rotobiner allows attachment to a tool or anchor.</p>"
    )

    assert not _has_cinch_mechanism(body)


def test_cinch_observations_round_trip_using_persisted_family():
    original = _evaluation(
        family="cinch_loop_to_closed_interface.v1",
        observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=True,
            cinch_drawn_tight=True,
        ),
    )

    restored = ConnectionEvaluation.model_validate(original.model_dump())

    assert isinstance(restored.verification_observations, CinchLoopClosedInterfaceVerification)
    assert restored.verification_observations.target_fully_captured is True
    assert restored.verification_observations.cinch_drawn_tight is True


def test_partial_cinch_observations_round_trip_without_becoming_gated_observations():
    original = _evaluation(
        family="cinch_loop_to_closed_interface.v1",
        observations=CinchLoopClosedInterfaceVerification(
            target_fully_captured=True,
        ),
    )

    restored = ConnectionEvaluation.model_validate(original.model_dump())

    assert isinstance(restored.verification_observations, CinchLoopClosedInterfaceVerification)
    assert restored.verification_observations.target_fully_captured is True
    assert restored.verification_observations.cinch_drawn_tight is None


def test_gated_observations_round_trip_using_persisted_family():
    original = _evaluation(
        family="gated_connector_to_closed_interface.v1",
        observations=GatedConnectorClosedInterfaceVerification(
            target_fully_captured=True,
            gate_closed_completely=True,
        ),
    )

    restored = ConnectionEvaluation.model_validate(original.model_dump())

    assert isinstance(
        restored.verification_observations,
        GatedConnectorClosedInterfaceVerification,
    )
    assert restored.verification_observations.target_fully_captured is True
    assert restored.verification_observations.gate_closed_completely is True


def test_serialized_observations_with_fields_from_other_family_fail_closed():
    payload = _evaluation(
        family="cinch_loop_to_closed_interface.v1",
        observations=CinchLoopClosedInterfaceVerification(target_fully_captured=True),
    ).model_dump()
    payload["verification_observations"] = {
        "target_fully_captured": True,
        "gate_closed_completely": True,
    }

    with pytest.raises(ValueError, match="fields outside their family"):
        ConnectionEvaluation.model_validate(payload)
