from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .models import CandidateClaim, ClaimSubjectType


MEMBER_REF_KEY = "endpoint_assignment.member_ref"
SEMANTICS_KEY = "endpoint_assignment.semantics"
ISSUER_MANUFACTURER_KEY = "endpoint_assignment.issuer_manufacturer"
SCOPE_KEY = "endpoint_assignment.scope"


class EndpointAssignmentSemantics(StrEnum):
    """Reusable endpoint-assignment relations supported by candidate generation."""

    REVERSIBLE_TOOL_ANCHOR_PAIR = "reversible_tool_anchor_pair"


class TetherEndpointAssignmentDeclaration(BaseModel):
    """Accepted evidence about how a set of tether endpoints may be assigned.

    The declaration is intentionally separate from ``ConnectionInterface.tether_side``.
    It does not rewrite missing endpoint roles to ``either``; it records a relationship
    between concrete endpoint subjects owned by one tether product.
    """

    declaration_id: str = Field(min_length=1)
    tether_ref: str = Field(min_length=1)
    endpoint_refs: list[str] = Field(min_length=2, max_length=2)
    semantics: EndpointAssignmentSemantics
    issuer_manufacturer: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_members_and_sources(self) -> TetherEndpointAssignmentDeclaration:
        endpoint_refs = sorted({ref.strip() for ref in self.endpoint_refs if ref.strip()})
        if len(endpoint_refs) != 2:
            raise ValueError(
                "reversible endpoint assignment requires exactly two distinct endpoint refs"
            )
        source_urls = sorted({url.strip() for url in self.source_urls if url.strip()})
        if not source_urls:
            raise ValueError("endpoint assignment declaration requires at least one source URL")
        self.endpoint_refs = endpoint_refs
        self.source_urls = source_urls
        return self


def resolve_tether_endpoint_assignment_declarations(
    claims: list[CandidateClaim],
    *,
    tether_ref: str,
) -> list[TetherEndpointAssignmentDeclaration]:
    """Resolve accepted endpoint-assignment claims for one owning tether.

    Callers must pass reconciled/accepted claims. Product ownership is supplied
    explicitly because endpoint subject refs are local and commonly repeat across
    tether products (for example ``connection_point_1``).
    """

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type == ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT:
            grouped[claim.subject_ref].append(claim)

    declarations: list[TetherEndpointAssignmentDeclaration] = []
    for declaration_id, declaration_claims in sorted(grouped.items()):
        endpoint_refs = sorted(
            {
                str(claim.value).strip()
                for claim in declaration_claims
                if claim.property_key == MEMBER_REF_KEY and str(claim.value).strip()
            }
        )
        if len(endpoint_refs) != 2:
            raise ValueError(
                f"endpoint assignment declaration {declaration_id!r} requires exactly "
                "two distinct endpoint members"
            )

        semantics_raw = _required_text(
            declaration_claims,
            SEMANTICS_KEY,
            declaration_id,
        )
        try:
            semantics = EndpointAssignmentSemantics(semantics_raw)
        except ValueError as exc:
            raise ValueError(
                f"unsupported endpoint assignment semantics on {declaration_id!r}: "
                f"{semantics_raw!r}"
            ) from exc

        issuer_manufacturer = _required_text(
            declaration_claims,
            ISSUER_MANUFACTURER_KEY,
            declaration_id,
        )
        scope = _required_text(
            declaration_claims,
            SCOPE_KEY,
            declaration_id,
        )
        source_urls = sorted(
            {
                url
                for claim in declaration_claims
                for url in [claim.source_url, *claim.supporting_source_urls]
                if url and url.strip()
            }
        )

        declarations.append(
            TetherEndpointAssignmentDeclaration(
                declaration_id=declaration_id,
                tether_ref=tether_ref,
                endpoint_refs=endpoint_refs,
                semantics=semantics,
                issuer_manufacturer=issuer_manufacturer,
                scope=scope,
                source_urls=source_urls,
            )
        )

    return declarations


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    declaration_id: str,
) -> str:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        raise ValueError(
            f"endpoint assignment declaration {declaration_id!r} is missing {property_key!r}"
        )
    values = {str(claim.value).strip() for claim in matches}
    if len(values) != 1 or not next(iter(values)):
        raise ValueError(
            f"endpoint assignment declaration {declaration_id!r} has conflicting/empty "
            f"{property_key!r} values"
        )
    return next(iter(values))
