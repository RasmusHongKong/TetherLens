from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field, field_validator

from .candidate_generation import ConnectionEvaluationContext
from .compatibility import ManufacturerPosition
from .connection import (
    ConnectionInterface,
    ConnectionInterfaceRole,
    ConnectionManufacturerAssessment,
)
from .models import CandidateClaim, ClaimSubjectType


REQUIRED_TETHER_MANUFACTURER_KEY = "manufacturer_instruction.required_tether_manufacturer"
TARGET_INTERFACE_REF_KEY = "manufacturer_instruction.target_interface_ref"
ISSUER_MANUFACTURER_KEY = "manufacturer_instruction.issuer_manufacturer"
SCOPE_KEY = "manufacturer_instruction.scope"


class RequiredTetherManufacturerInstruction(BaseModel):
    """One issuer-scoped instruction requiring a tether-manufacturer family.

    This object carries manufacturer position only. It does not establish physical
    incompatibility for alternatives and does not itself apply site policy. Catalogue
    composition supplies the selected tether manufacturer's accepted identity and the
    exact target product/interface before a contrary assessment may be emitted.
    """

    instruction_id: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    target_interface_ref: str = Field(min_length=1)
    required_tether_manufacturer: str = Field(min_length=1)
    issuer_manufacturer: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip() for value in values if value.strip()})
        if not normalized:
            raise ValueError("manufacturer instruction requires at least one source URL")
        return normalized

    @property
    def evidence_ref(self) -> str:
        return self.source_urls[0]


def resolve_required_tether_manufacturer_instructions(
    claims: list[CandidateClaim],
    *,
    source_product_ref: str,
) -> list[RequiredTetherManufacturerInstruction]:
    """Resolve accepted product-scoped tether-manufacturer instructions.

    Claims use a non-``self`` PRODUCT subject so they cannot be mistaken for ordinary
    product constraints. The caller supplies the stable catalogue product ref rather
    than reconstructing product identity from claim wording or identifier conventions.
    """

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type != ClaimSubjectType.PRODUCT:
            continue
        if claim.property_key not in {
            REQUIRED_TETHER_MANUFACTURER_KEY,
            TARGET_INTERFACE_REF_KEY,
            ISSUER_MANUFACTURER_KEY,
            SCOPE_KEY,
        }:
            continue
        grouped[claim.subject_ref].append(claim)

    instructions: list[RequiredTetherManufacturerInstruction] = []
    for instruction_id, instruction_claims in sorted(grouped.items()):
        if not any(
            claim.property_key == REQUIRED_TETHER_MANUFACTURER_KEY
            for claim in instruction_claims
        ):
            continue
        source_urls = sorted(
            {
                url
                for claim in instruction_claims
                for url in [claim.source_url, *claim.supporting_source_urls]
                if url and url.strip()
            }
        )
        instructions.append(
            RequiredTetherManufacturerInstruction(
                instruction_id=instruction_id,
                source_product_ref=source_product_ref,
                target_interface_ref=_required_text(
                    instruction_claims,
                    TARGET_INTERFACE_REF_KEY,
                    instruction_id,
                ),
                required_tether_manufacturer=_required_text(
                    instruction_claims,
                    REQUIRED_TETHER_MANUFACTURER_KEY,
                    instruction_id,
                ),
                issuer_manufacturer=_required_text(
                    instruction_claims,
                    ISSUER_MANUFACTURER_KEY,
                    instruction_id,
                ),
                scope=_required_text(
                    instruction_claims,
                    SCOPE_KEY,
                    instruction_id,
                ),
                source_urls=source_urls,
            )
        )
    return instructions


def connection_contexts_from_required_tether_manufacturer_instructions(
    *,
    tether_ref: str,
    tether_manufacturer: str,
    endpoints: list[ConnectionInterface],
    target_owner_ref: str,
    target_product_ref: str,
    target_interfaces: list[ConnectionInterface],
    instructions: list[RequiredTetherManufacturerInstruction],
    existing_contexts: list[ConnectionEvaluationContext] | None = None,
) -> list[ConnectionEvaluationContext]:
    """Attach contrary OEM assessments to concrete mixed-manufacturer connections.

    Exact selected-product/manufacturer identity is supplied by catalogue composition.
    No manufacturer is parsed from product refs. A non-matching known manufacturer gets
    ``CONTRARY_TO_MANUFACTURER_INSTRUCTION`` while technical connection status remains
    independent. A matching manufacturer receives no positive assessment because wording
    such as "appropriate <manufacturer> tether" does not prove every product from that
    manufacturer is endorsed for this exact connection.
    """

    normalized_tether_manufacturer = tether_manufacturer.strip()
    if not normalized_tether_manufacturer:
        raise ValueError("tether_manufacturer must be non-empty")

    contexts: dict[tuple[str, str, str, str], ConnectionEvaluationContext] = {}
    for context in existing_contexts or []:
        key = _context_key(context)
        if key in contexts:
            raise ValueError(f"duplicate existing connection context: {key!r}")
        contexts[key] = context

    interfaces_by_id = {interface.interface_id: interface for interface in target_interfaces}
    if len(interfaces_by_id) != len(target_interfaces):
        raise ValueError("target interface ids must be unique")

    for instruction in instructions:
        if instruction.source_product_ref != target_product_ref:
            continue
        target = interfaces_by_id.get(instruction.target_interface_ref)
        if target is None:
            raise ValueError(
                "manufacturer instruction target interface is absent from selected target product: "
                f"{instruction.target_interface_ref!r}"
            )
        if target.role != ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE:
            raise ValueError(
                "required tether manufacturer instruction must target a ToolAttachment tether-side interface"
            )
        if normalized_tether_manufacturer.casefold() == instruction.required_tether_manufacturer.casefold():
            continue

        assessment = ConnectionManufacturerAssessment(
            issuer_manufacturer=instruction.issuer_manufacturer,
            scope=instruction.scope,
            position=ManufacturerPosition.CONTRARY_TO_MANUFACTURER_INSTRUCTION,
            claim_or_evidence_ref=instruction.evidence_ref,
            technical_causal_scope_established=False,
        )
        for endpoint in endpoints:
            if endpoint.role != ConnectionInterfaceRole.TETHER_CONNECTION:
                continue
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
                    manufacturer_assessments=[assessment],
                )
                continue
            contexts[key] = existing.model_copy(
                update={
                    "manufacturer_assessments": _dedupe_assessments(
                        [*existing.manufacturer_assessments, assessment]
                    )
                }
            )

    return [contexts[key] for key in sorted(contexts)]


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    instruction_id: str,
) -> str:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        raise ValueError(
            f"manufacturer instruction {instruction_id!r} is missing {property_key!r}"
        )
    values = {str(claim.value).strip() for claim in matches}
    if len(values) != 1 or not next(iter(values)):
        raise ValueError(
            f"manufacturer instruction {instruction_id!r} has conflicting/empty {property_key!r} values"
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
