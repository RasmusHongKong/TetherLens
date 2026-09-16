from __future__ import annotations

import math
from collections import defaultdict

from pydantic import BaseModel, Field, field_validator

from .candidate_generation import ResolvedToolCandidate
from .compatibility import ToolInterfaceFeature
from .connection import ConnectionInterface
from .field_recommendation import OperationalToolProfile
from .models import CandidateClaim, ClaimSubjectType


OPERATIONAL_MASS_KEY = "operational_mass_kg"


class OperationalProfileResolutionError(ValueError):
    """Accepted operational-profile evidence cannot be bound safely to catalogue identity."""


class OperationalProfileDescriptor(BaseModel):
    """Exact catalogue identity of one operational Tool configuration.

    The descriptor is intentionally separate from Claim resolution. Its profile and
    configuration-product refs must already come from normalized catalogue relationships;
    this layer never reconstructs Battery identity by parsing a compound profile ref or
    by matching masses/source URLs heuristically.
    """

    profile_ref: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    configuration_product_refs: list[str] = Field(min_length=1)

    @field_validator("configuration_product_refs")
    @classmethod
    def validate_configuration_refs(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("configuration product refs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("configuration product refs must be unique within one descriptor")
        return values


def resolve_operational_tool_profiles(
    claims: list[CandidateClaim],
    *,
    tool_ref: str,
    descriptors: list[OperationalProfileDescriptor],
    features: list[ToolInterfaceFeature] | None = None,
    direct_interfaces: list[ConnectionInterface] | None = None,
) -> list[OperationalToolProfile]:
    """Bind accepted operational-mass Claims to exact normalized configuration identity.

    Every descriptor is preserved, even when no accepted operational mass is available.
    Such a profile reaches the existing field readiness boundary with ``object_mass_kg``
    unset rather than disappearing and allowing another configuration to be selected
    silently.

    Conversely, an accepted operational-mass Claim without a descriptor fails closed.
    The resolver will not infer configuration identity from ``subject_ref`` syntax,
    evidence URLs, Battery mass arithmetic, manufacturer names, or SKU conventions.
    """

    if not tool_ref.strip():
        raise ValueError("tool_ref must be non-empty")

    descriptor_refs = [descriptor.profile_ref for descriptor in descriptors]
    if len(set(descriptor_refs)) != len(descriptor_refs):
        raise ValueError("operational profile descriptor refs must be unique")

    mass_claims_by_ref: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if (
            claim.subject_type == ClaimSubjectType.OPERATIONAL_PROFILE
            and claim.property_key == OPERATIONAL_MASS_KEY
        ):
            mass_claims_by_ref[claim.subject_ref].append(claim)

    unexpected = sorted(set(mass_claims_by_ref) - set(descriptor_refs))
    if unexpected:
        raise OperationalProfileResolutionError(
            "operational-mass evidence has no normalized configuration descriptor: "
            f"{unexpected!r}"
        )

    resolved_features = list(features or [])
    resolved_direct_interfaces = list(direct_interfaces or [])
    profiles: list[OperationalToolProfile] = []
    for descriptor in descriptors:
        mass = _resolve_operational_mass(
            descriptor.profile_ref,
            mass_claims_by_ref.get(descriptor.profile_ref, []),
        )
        profiles.append(
            OperationalToolProfile(
                profile_ref=descriptor.profile_ref,
                display_name=descriptor.display_name,
                tool=ResolvedToolCandidate(
                    tool_ref=tool_ref,
                    object_mass_kg=mass,
                    features=[feature.model_copy(deep=True) for feature in resolved_features],
                    direct_interfaces=[
                        interface.model_copy(deep=True)
                        for interface in resolved_direct_interfaces
                    ],
                ),
                configuration_product_refs=list(
                    descriptor.configuration_product_refs
                ),
            )
        )

    return profiles


def _resolve_operational_mass(
    profile_ref: str,
    claims: list[CandidateClaim],
) -> float | None:
    if not claims:
        return None

    values: set[float] = set()
    for claim in claims:
        value = claim.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise OperationalProfileResolutionError(
                f"operational mass for profile {profile_ref!r} must be numeric"
            )
        numeric = float(value)
        if not math.isfinite(numeric) or numeric <= 0:
            raise OperationalProfileResolutionError(
                f"operational mass for profile {profile_ref!r} must be finite and positive"
            )
        values.add(numeric)

    if len(values) != 1:
        raise OperationalProfileResolutionError(
            f"conflicting accepted operational masses for profile {profile_ref!r}: "
            f"{sorted(values)!r}"
        )
    return next(iter(values))
