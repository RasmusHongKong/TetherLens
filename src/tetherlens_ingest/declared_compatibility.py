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
SOURCE_PRODUCT_IDENTIFIER_KEY = "connection_compatibility.source_product_identifier"
TARGET_PRODUCT_IDENTIFIER_KEY = "connection_compatibility.target_product_identifier"
TARGET_ATTRIBUTE_PREFIX = "connection_compatibility.target_attribute."


class ConnectorInterfaceCompatibilityDeclaration(BaseModel):
    """One accepted manufacturer-declared connector-to-interface relationship.

    Generic declarations remain reusable because they are expressed in connector/interface
    primitives rather than a tether-SKU/target-SKU pair. When the accepted source itself
    names concrete products, ``source_product_ref`` and ``target_product_ref`` retain that
    issuer scope and prevent the manufacturer assessment from widening to other products
    that merely share the same generic primitives.
    """

    declaration_id: str = Field(min_length=1)
    connector_spec_ref: str | None = Field(default=None, min_length=1)
    source_interface_type: str | None = Field(default=None, min_length=1)
    target_interface_type: str | None = Field(default=None, min_length=1)
    target_role: ConnectionInterfaceRole | None = None
    target_attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    source_product_ref: str | None = Field(default=None, min_length=1)
    target_product_ref: str | None = Field(default=None, min_length=1)
    issuer_manufacturer: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_declaration(self) -> ConnectorInterfaceCompatibilityDeclaration:
        normalized = sorted({url.strip() for url in self.source_urls if url.strip()})
        if not normalized:
            raise ValueError("compatibility declaration requires at least one source URL")
        self.source_urls = normalized
        if (self.source_product_ref is None) != (self.target_product_ref is None):
            raise ValueError(
                "product-scoped compatibility declarations require both source and target product refs"
            )

        product_scoped = self.source_product_ref is not None
        primitive_fields = {
            "connector_spec_ref": self.connector_spec_ref,
            "source_interface_type": self.source_interface_type,
            "target_interface_type": self.target_interface_type,
            "target_role": self.target_role,
        }
        if not product_scoped:
            missing = [name for name, value in primitive_fields.items() if value is None]
            if missing:
                raise ValueError(
                    "generic compatibility declarations require complete connector/interface "
                    f"primitives; missing {missing!r}"
                )
        return self

    @property
    def evidence_ref(self) -> str:
        # ConnectionManufacturerAssessment currently retains one evidence reference.
        # The declaration keeps the complete URL set; v1 extraction is intentionally
        # single-source, so the first canonical URL is also the operative downstream ref.
        return self.source_urls[0]


def resolve_connector_interface_compatibility_declarations(
    claims: list[CandidateClaim],
    *,
    product_refs_by_identifier: dict[str, str] | None = None,
) -> list[ConnectorInterfaceCompatibilityDeclaration]:
    """Resolve accepted declarations without reconstructing product identity from names.

    A declaration that contains explicit source/target product identifiers is executable
    only after catalogue composition maps both identifiers to stable product refs. Missing
    mappings fail closed by leaving that declaration out of the runtime set; they do not
    erase the accepted raw claims or widen product-scoped evidence into a generic rule.
    """

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.CONNECTION_COMPATIBILITY:
            continue
        grouped[claim.subject_ref].append(claim)

    declarations: list[ConnectorInterfaceCompatibilityDeclaration] = []
    for declaration_id, declaration_claims in sorted(grouped.items()):
        connector_spec_ref = _optional_text(
            declaration_claims,
            CONNECTOR_SPEC_REF_KEY,
            declaration_id,
        )
        source_interface_type = _optional_text(
            declaration_claims,
            SOURCE_INTERFACE_TYPE_KEY,
            declaration_id,
        )
        target_interface_type = _optional_text(
            declaration_claims,
            TARGET_INTERFACE_TYPE_KEY,
            declaration_id,
        )
        target_role_raw = _optional_text(
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
        source_product_identifier = _optional_text(
            declaration_claims,
            SOURCE_PRODUCT_IDENTIFIER_KEY,
            declaration_id,
        )
        target_product_identifier = _optional_text(
            declaration_claims,
            TARGET_PRODUCT_IDENTIFIER_KEY,
            declaration_id,
        )
        if (source_product_identifier is None) != (target_product_identifier is None):
            raise ValueError(
                f"compatibility declaration {declaration_id!r} must scope both source and target products"
            )

        source_product_ref: str | None = None
        target_product_ref: str | None = None
        if source_product_identifier is not None and target_product_identifier is not None:
            product_refs = product_refs_by_identifier or {}
            source_product_ref = product_refs.get(source_product_identifier)
            target_product_ref = product_refs.get(target_product_identifier)
            if source_product_ref is None or target_product_ref is None:
                continue

        target_role: ConnectionInterfaceRole | None = None
        if target_role_raw is not None:
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
                source_product_ref=source_product_ref,
                target_product_ref=target_product_ref,
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
    tether_product_ref: str | None = None,
    target_product_refs: set[str] | None = None,
    target_interface_product_refs: dict[str, str] | None = None,
    existing_contexts: list[ConnectionEvaluationContext] | None = None,
) -> list[ConnectionEvaluationContext]:
    """Bind declarations to concrete endpoint/target pairs for one owner scope.

    Generic declarations match only retained connector/interface primitives. If a source
    explicitly scoped its statement to named products, the resolved stable product refs
    must also match the concrete tether product and the product that owns the *current*
    target interface before an ``EXPLICITLY_COMPATIBLE`` manufacturer assessment is
    emitted. A single-product target may omit the per-interface ownership map because
    ownership is unambiguous; multi-product targets fail closed without exact ownership.
    """

    contexts: dict[tuple[str, str, str, str], ConnectionEvaluationContext] = {}
    for context in existing_contexts or []:
        key = _context_key(context)
        if key in contexts:
            raise ValueError(f"duplicate existing connection context: {key!r}")
        contexts[key] = context

    concrete_target_product_refs = target_product_refs or set()
    interface_ids = {interface.interface_id for interface in target_interfaces}
    interface_product_refs = dict(target_interface_product_refs or {})
    unexpected_interface_ids = sorted(set(interface_product_refs) - interface_ids)
    if unexpected_interface_ids:
        raise ValueError(
            "target interface product ownership refers to interfaces outside the target set: "
            f"{unexpected_interface_ids!r}"
        )
    if concrete_target_product_refs:
        unexpected_products = sorted(
            set(interface_product_refs.values()) - concrete_target_product_refs
        )
        if unexpected_products:
            raise ValueError(
                "target interface product ownership must refer to selected target products: "
                f"{unexpected_products!r}"
            )

    inferred_single_target_product_ref = (
        next(iter(concrete_target_product_refs))
        if len(concrete_target_product_refs) == 1
        else None
    )

    for endpoint in endpoints:
        for target in target_interfaces:
            target_interface_product_ref = interface_product_refs.get(
                target.interface_id,
                inferred_single_target_product_ref,
            )
            matching = [
                declaration
                for declaration in declarations
                if _product_scoped_target_is_unambiguous(
                    declaration,
                    target_interfaces=target_interfaces,
                    target_interface_product_refs=interface_product_refs,
                    inferred_single_target_product_ref=inferred_single_target_product_ref,
                )
                and _declaration_matches(
                    declaration,
                    endpoint,
                    target,
                    tether_product_ref=tether_product_ref,
                    target_interface_product_ref=target_interface_product_ref,
                )
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
    *,
    tether_product_ref: str | None,
    target_interface_product_ref: str | None,
) -> bool:
    if declaration.source_product_ref is not None:
        if tether_product_ref != declaration.source_product_ref:
            return False
        if target_interface_product_ref != declaration.target_product_ref:
            return False
    if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION:
        return False
    if (
        declaration.connector_spec_ref is not None
        and endpoint.connector_spec_ref != declaration.connector_spec_ref
    ):
        return False
    if (
        declaration.source_interface_type is not None
        and endpoint.interface_type != declaration.source_interface_type
    ):
        return False
    if declaration.target_role is not None and target.role != declaration.target_role:
        return False
    if (
        declaration.target_interface_type is not None
        and target.interface_type != declaration.target_interface_type
    ):
        return False
    return all(
        target.attributes.get(key) == value
        for key, value in declaration.target_attributes.items()
    )


def _product_scoped_target_is_unambiguous(
    declaration: ConnectorInterfaceCompatibilityDeclaration,
    *,
    target_interfaces: list[ConnectionInterface],
    target_interface_product_refs: dict[str, str],
    inferred_single_target_product_ref: str | None,
) -> bool:
    """Fail closed when an unconstrained exact-product declaration has multiple targets."""

    if declaration.target_product_ref is None:
        return True
    if (
        declaration.target_role is not None
        or declaration.target_interface_type is not None
        or declaration.target_attributes
    ):
        return True

    owned_targets = 0
    for interface in target_interfaces:
        owner_ref = target_interface_product_refs.get(
            interface.interface_id,
            inferred_single_target_product_ref,
        )
        if owner_ref == declaration.target_product_ref:
            owned_targets += 1
    return owned_targets == 1


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    declaration_id: str,
) -> str:
    value = _optional_text(claims, property_key, declaration_id)
    if value is None:
        raise ValueError(
            f"compatibility declaration {declaration_id!r} is missing {property_key!r}"
        )
    return value


def _optional_text(
    claims: list[CandidateClaim],
    property_key: str,
    declaration_id: str,
) -> str | None:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        return None
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
