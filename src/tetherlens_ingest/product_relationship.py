from __future__ import annotations

from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from .models import CandidateClaim, ClaimSubjectType


RELATIONSHIP_TYPE_KEY = "declared_relationship.type"
OBJECT_PRODUCT_IDENTIFIER_KEY = "declared_relationship.object_product_identifier"
QUANTITY_KEY = "declared_relationship.quantity"
SCOPE_KEY = "declared_relationship.scope"


class DeclaredProductRelationshipType(StrEnum):
    """Manufacturer-backed product relationships currently executable by the catalogue."""

    EXPLICITLY_ENDORSED = "explicitly_endorsed"
    KIT_RELATIONSHIP = "kit_relationship"


class DeclaredProductRelationship(BaseModel):
    """One exact manufacturer-backed relationship between two catalogued products.

    Relationship evidence is catalogue metadata. It does not itself become a runtime
    load-path component, generic compatibility rule, or recommendation candidate.
    """

    relationship_id: str = Field(min_length=1)
    subject_product_ref: str = Field(min_length=1)
    object_product_identifier: str = Field(min_length=1)
    object_product_ref: str = Field(min_length=1)
    relationship_type: DeclaredProductRelationshipType
    quantity: int | None = Field(default=None, ge=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls")
    @classmethod
    def normalize_source_urls(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip() for value in values if value.strip()})
        if not normalized:
            raise ValueError("declared product relationship requires source provenance")
        return normalized


def resolve_declared_product_relationships(
    claims: list[CandidateClaim],
    *,
    subject_product_ref: str,
    product_refs_by_identifier: dict[str, str],
) -> list[DeclaredProductRelationship]:
    """Bind accepted relationship claims to exact catalogue identities.

    The accepted raw claims remain useful even when a related product has not yet been
    catalogued. Runtime/catalogue composition, however, requires an explicit identifier
    -> stable product-ref mapping and never reconstructs product identity from SKU syntax,
    names, manufacturer conventions, or source URLs.
    """

    if not subject_product_ref.strip():
        raise ValueError("subject product ref must be non-empty")

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type == ClaimSubjectType.DECLARED_RELATIONSHIP:
            grouped[claim.subject_ref].append(claim)

    relationships: list[DeclaredProductRelationship] = []
    for relationship_id, relationship_claims in sorted(grouped.items()):
        relationship_type_raw = _required_text(
            relationship_claims,
            RELATIONSHIP_TYPE_KEY,
            relationship_id,
        )
        try:
            relationship_type = DeclaredProductRelationshipType(relationship_type_raw)
        except ValueError as exc:
            raise ValueError(
                f"unsupported declared relationship type on {relationship_id!r}: "
                f"{relationship_type_raw!r}"
            ) from exc

        object_identifier = _required_text(
            relationship_claims,
            OBJECT_PRODUCT_IDENTIFIER_KEY,
            relationship_id,
        )
        object_product_ref = product_refs_by_identifier.get(object_identifier)
        if object_product_ref is None:
            # Accepted evidence is preserved in Claims, but it cannot participate in
            # executable catalogue composition until exact product identity is mapped.
            continue

        quantity = _optional_positive_int(
            relationship_claims,
            QUANTITY_KEY,
            relationship_id,
        )
        scope = _required_text(
            relationship_claims,
            SCOPE_KEY,
            relationship_id,
        )
        source_urls = sorted(
            {
                url
                for claim in relationship_claims
                for url in [claim.source_url, *claim.supporting_source_urls]
                if url and url.strip()
            }
        )

        relationships.append(
            DeclaredProductRelationship(
                relationship_id=relationship_id,
                subject_product_ref=subject_product_ref,
                object_product_identifier=object_identifier,
                object_product_ref=object_product_ref,
                relationship_type=relationship_type,
                quantity=quantity,
                scope=scope,
                source_urls=source_urls,
            )
        )

    return relationships


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    relationship_id: str,
) -> str:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        raise ValueError(
            f"declared relationship {relationship_id!r} is missing {property_key!r}"
        )
    values = {str(claim.value).strip() for claim in matches}
    if len(values) != 1 or not next(iter(values)):
        raise ValueError(
            f"declared relationship {relationship_id!r} has conflicting/empty "
            f"{property_key!r} values"
        )
    return next(iter(values))


def _optional_positive_int(
    claims: list[CandidateClaim],
    property_key: str,
    relationship_id: str,
) -> int | None:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        return None
    values = {claim.value for claim in matches}
    if len(values) != 1:
        raise ValueError(
            f"declared relationship {relationship_id!r} has conflicting "
            f"{property_key!r} values"
        )
    value = next(iter(values))
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(
            f"declared relationship {relationship_id!r} requires a positive integer "
            f"{property_key!r}"
        )
    return value
