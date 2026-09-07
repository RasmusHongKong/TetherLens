from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field, model_validator

from .candidate_generation import ConnectionEvaluationContext
from .compatibility import ManufacturerPosition
from .connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
)
from .models import CandidateClaim, ClaimSubjectType


CONNECTOR_SPEC_REF_KEY = "connection_compatibility.connector_spec_ref"
SOURCE_INTERFACE_TYPE_KEY = "connection_compatibility.source_interface_type"
TARGET_INTERFACE_TYPE_KEY = "connection_compatibility.target_interface_type"
TARGET_ROLE_KEY = "connection_compatibility.target_role"
ISSUER_MANUFACTURER_KEY = "connection_compatibility.issuer_manufacturer"
SCOPE_KEY = "connection_compatibility.scope"
TARGET_ATTRIBUTE_PREFIX = "connection_compatibility.target_attribute."


class ConnectorInterfaceCompatibilityDeclaration(BaseModel):
    """One accepted manufacturer-declared connector-to-interface relationship.

    The declaration is reusable because it is expressed in connector/interface
    primitives rather than a tether-SKU/target-SKU pair. Product-scoped candidate
    contexts are derived only after the declaration matches concrete runtime
    interfaces.
    """

    declaration_id: str = Field(min_length=1)
    connector_spec_ref: str = Field(min_length=1)
    source_interface_type: str = Field(min_length=1)
    target_interface_type: str = Field(min_length=1)
    target_role: ConnectionInterfaceRole
    target_attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    issuer_manufacturer: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_urls(self) -> ConnectorInterfaceCompatibilityDeclaration:
        normalized = sorted({url.strip() for url in self.source_urls if url.strip()})
        if not normalized:
            raise ValueError("compatibility declaration requires at least one source URL")
        self.source_urls = normalized
        return self

    @property
    def evidence_ref(self) -> str:
        # ConnectionManufacturerAssessment currently retains one evidence reference.
        # The declaration keeps the complete URL set; v1 extraction is intentionally
        # single-source, so the first canonical URL is also the operative downstream ref.
        return self.source_urls[0]


def resolve_connector_interface_compatibility_declarations(
    claims: list[CandidateClaim],
) -> list[ConnectorInterfaceCompatibilityDeclaration]:
    """Resolve accepted declaration claims without reconstructing them from product names."""

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.CONNECTION_COMPATIBILITY:
            continue
        grouped[claim.subject_ref].append(claim)

    declarations: list[ConnectorInterfaceCompatibilityDeclaration] = []
    for declaration_id, declaration_claims in sorted(grouped.items()):
        connector_spec_ref = _required_text(
            declaration_claims,
            CONNECTOR_SPEC_REF_KEY,
            declaration_id,
        )
        source_interface_type = _required_text(
            declaration_claims,
            SOURCE_INTERFACE_TYPE_KEY,
            declaration_id,
        )
        target_interface_type = _required_text(
            declaration_claims,
            TARGET_INTERFACE_TYPE_KEY,
            declaration_id,
        )
        target_role_raw = _required_text(
            declaration_claims,
            TARGET_ROLE_KEY,
            declaration_id,
        )
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

        try:
            target_role = ConnectionInterfaceRole(target_role_raw)
        except ValueError as exc:
            raise ValueError(
                f"unsupported target role on compatibility declaration {declaration_id!r}: "
                f"{target_role_raw!r}"
            ) from exc

        target_attributes: dict[str, str | int | float | bool] = {}
        for claim in declaration_claims:
            if not claim.property_key.startswith(TARGET_ATTRIBUTE_PREFIX):
                continue
            key = claim.property_key.removeprefix(TARGET_ATTRIBUTE_PREFIX)
            if not key:
                continue
            if key in target_attributes and target_attributes[key] != claim.value:
                raise ValueError(
                    f"conflicting target attribute {key!r} on compatibility declaration "
                    f"{declaration_id!r}"
                )
            target_attributes[key] = claim.value

        source_urls = sorted(
            {
                url
                for claim in declaration_claims
                for url in [claim.source_url, *claim.supporting_source_urls]
                if url
            }
        )
        declarations.append(
            ConnectorInterfaceCompatibilityDeclaration(
                declaration_id=declaration_id,
                connector_spec_ref=connector_spec_ref,
                source_interface_type=source_interface_type,
                target_interface_type=target_interface_type,
                target_role=target_role,
                target_attributes=target_attributes,
                issuer_manufacturer=issuer_manufacturer,
                scope=scope,
                source_urls=source_urls,
            )
        )

    return declarations


def connection_contexts_from_compatibility_declarations(
    *,
    tether_ref: str,
    endpoints: list[ConnectionInterface],
    target_owner_ref: str,
    target_interfaces: list[ConnectionInterface],
    declarations: list[ConnectorInterfaceCompatibilityDeclaration],
    existing_contexts: list[ConnectionEvaluationContext] | None = None,
) -> list[ConnectionEvaluationContext]:
    """Bind reusable declarations to concrete endpoint/target pairs for one owner scope.

    Runtime product references participate only in the resulting context key. Matching
    itself uses the retained connector/interface primitives, so this helper does not
    create or persist SKU-pair compatibility.
    """

    contexts: dict[tuple[str, str, str, str], ConnectionEvaluationContext] = {}
    for context in existing_contexts or []:
        key = _context_key(context)
        if key in contexts:
            raise ValueError(f"duplicate existing connection context: {key!r}")
        contexts[key] = context

    for endpoint in endpoints:
        for target in target_interfaces:
            matching = [
                declaration
                for declaration in declarations
                if _declaration_matches(declaration, endpoint, target)
            ]
            if not matching:
                continue

            assessments = [
                ConnectionManufacturerAssessment(
                    issuer_manufacturer=declaration.issuer_manufacturer,
                    scope=declaration.scope,
                    position=ManufacturerPosition.EXPLICITLY_COMPATIBLE,
                    claim_or_evidence_ref=declaration.evidence_ref,
                )
                for declaration in matching
            ]
            key = (
                tether_ref,
                target_owner_ref,
                endpoint.interface_id,
                target.interface_id,
            )
            existing = contexts.get(key)
            if existing is None:
                contexts[key] = ConnectionEvaluationContext(
                    tether_ref=tether_ref,
                    target_owner_ref=target_owner_ref,
                    endpoint_id=endpoint.interface_id,
                    target_interface_id=target.interface_id,
                    manufacturer_assessments=_dedupe_assessments(assessments),
                )
                continue

            contexts[key] = existing.model_copy(
                update={
                    "manufacturer_assessments": _dedupe_assessments(
                        [*existing.manufacturer_assessments, *assessments]
                    )
                }
            )

    return [contexts[key] for key in sorted(contexts)]


def _declaration_matches(
    declaration: ConnectorInterfaceCompatibilityDeclaration,
    endpoint: ConnectionInterface,
    target: ConnectionInterface,
) -> bool:
    if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION:
        return False
    if endpoint.connector_spec_ref != declaration.connector_spec_ref:
        return False
    if endpoint.interface_type != declaration.source_interface_type:
        return False
    if target.role != declaration.target_role:
        return False
    if target.interface_type != declaration.target_interface_type:
        return False
    return all(
        target.attributes.get(key) == value
        for key, value in declaration.target_attributes.items()
    )


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    declaration_id: str,
) -> str:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        raise ValueError(
            f"compatibility declaration {declaration_id!r} is missing {property_key!r}"
        )
    values = {str(claim.value).strip() for claim in matches}
    if len(values) != 1 or not next(iter(values)):
        raise ValueError(
            f"compatibility declaration {declaration_id!r} has conflicting/empty "
            f"{property_key!r} values"
        )
    return next(iter(values))


def _context_key(context: ConnectionEvaluationContext) -> tuple[str, str, str, str]:
    return (
        context.tether_ref,
        context.target_owner_ref,
        context.endpoint_id,
        context.target_interface_id,
    )


def _dedupe_assessments(
    assessments: list[ConnectionManufacturerAssessment],
) -> list[ConnectionManufacturerAssessment]:
    out: list[ConnectionManufacturerAssessment] = []
    seen: set[tuple[object, ...]] = set()
    for assessment in assessments:
        key = (
            assessment.issuer_manufacturer,
            assessment.scope,
            assessment.position,
            assessment.claim_or_evidence_ref,
            assessment.authoritative,
            assessment.technical_causal_scope_established,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(assessment)
    return out
