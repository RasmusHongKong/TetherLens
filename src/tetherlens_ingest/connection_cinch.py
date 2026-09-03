from __future__ import annotations

from pydantic import BaseModel, StrictBool


class CinchLoopClosedInterfaceVerification(BaseModel):
    """Observed checks for ``cinch_loop_to_closed_interface.v1``.

    The two observations mirror the manufacturer-described cinch mechanism: the loop
    must fully capture the intended closed/captive target and the cinch must be pulled
    tight. Nullable fields allow incremental evidence without accepting a generic
    caller-supplied pass/fail assertion.
    """

    target_fully_captured: StrictBool | None = None
    cinch_drawn_tight: StrictBool | None = None


def evaluate_cinch_loop_closed_interface_verification(
    observations: CinchLoopClosedInterfaceVerification | None,
) -> str:
    """Return ``pending``, ``passed`` or ``failed`` from bounded observations only."""

    if observations is None:
        return "pending"
    required_checks = [
        observations.target_fully_captured,
        observations.cinch_drawn_tight,
    ]
    if any(check is False for check in required_checks):
        return "failed"
    if all(check is True for check in required_checks):
        return "passed"
    return "pending"
