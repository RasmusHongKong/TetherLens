from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConnectionInterfaceRole(StrEnum):
    TOOL_ATTACHMENT_TETHER_SIDE = "tool_attachment_tether_side"
    TOOL_DIRECT_TETHER_INTERFACE = "tool_direct_tether_interface"
    TETHER_CONNECTION = "tether_connection"
    ANCHOR_ATTACHMENT_TETHER_SIDE = "anchor_attachment_tether_side"
    CONTAINER_CONNECTION = "container_connection"
    UNKNOWN = "unknown"


class TetherSide(StrEnum):
    TOOL_SIDE = "tool_side"
    ANCHOR_SIDE = "anchor_side"
    EITHER = "either"
    UNKNOWN = "unknown"


class ConnectionStatus(StrEnum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNRESOLVED = "unresolved"


class ConnectionInterface(BaseModel):
    """One physical interface participating in a tether connection.

    This is intentionally separate from ``ToolInterfaceFeature``. A ToolAttachment
    can consume one tool feature while providing a different tether-side interface.
    """

    interface_id: str
    role: ConnectionInterfaceRole
    interface_type: str
    tether_side: TetherSide = TetherSide.UNKNOWN
    connector_spec_ref: str | None = None
    dimensions_mm: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("interface_type must be non-empty")
        return normalized

    @field_validator("dimensions_mm", mode="before")
    @classmethod
    def validate_dimensions_mm(cls, dimensions: Any) -> Any:
        if not isinstance(dimensions, dict):
            return dimensions
        for key, value in dimensions.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"dimension {key!r} must be a finite positive number")
            try:
                numeric = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"dimension {key!r} must be a finite positive number") from exc
            if not math.isfinite(numeric) or numeric <= 0:
                raise ValueError(f"dimension {key!r} must be a finite positive number")
        return dimensions


class ConnectionEvaluation(BaseModel):
    status: ConnectionStatus
    endpoint_id: str
    target_interface_id: str
    reason: str

    @property
    def compatible(self) -> bool:
        return self.status == ConnectionStatus.COMPATIBLE


def evaluate_endpoint_engagement(
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
) -> ConnectionEvaluation:
    """Evaluate one tether endpoint against one target interface conservatively.

    This first slice establishes topology and role semantics. It deliberately does
    not infer physical fit from names such as ``carabiner`` + ``ring``. Unless a
    future validated geometry rule has enough measurements to prove engagement,
    a physically plausible pairing remains unresolved.
    """

    if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION:
        return ConnectionEvaluation(
            status=ConnectionStatus.INCOMPATIBLE,
            endpoint_id=endpoint.interface_id,
            target_interface_id=target.interface_id,
            reason="source interface is not a tether connection point",
        )

    if target.role not in {
        ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
        ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.CONTAINER_CONNECTION,
    }:
        return ConnectionEvaluation(
            status=ConnectionStatus.INCOMPATIBLE,
            endpoint_id=endpoint.interface_id,
            target_interface_id=target.interface_id,
            reason="target interface is not a connectable tether-side interface",
        )

    if target.role in {
        ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.TOOL_DIRECT_TETHER_INTERFACE,
    } and endpoint.tether_side == TetherSide.ANCHOR_SIDE:
        return ConnectionEvaluation(
            status=ConnectionStatus.INCOMPATIBLE,
            endpoint_id=endpoint.interface_id,
            target_interface_id=target.interface_id,
            reason="anchor-side-only tether endpoint cannot serve the tool side",
        )

    if target.role in {
        ConnectionInterfaceRole.ANCHOR_ATTACHMENT_TETHER_SIDE,
        ConnectionInterfaceRole.CONTAINER_CONNECTION,
    } and endpoint.tether_side == TetherSide.TOOL_SIDE:
        return ConnectionEvaluation(
            status=ConnectionStatus.INCOMPATIBLE,
            endpoint_id=endpoint.interface_id,
            target_interface_id=target.interface_id,
            reason="tool-side-only tether endpoint cannot serve the anchor side",
        )

    return ConnectionEvaluation(
        status=ConnectionStatus.UNRESOLVED,
        endpoint_id=endpoint.interface_id,
        target_interface_id=target.interface_id,
        reason="interface topology is plausible but no validated geometry rule proves engagement",
    )
