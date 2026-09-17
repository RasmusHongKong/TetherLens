from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .attachment_method import ToolAttachmentInstallationMethod
from .candidate_generation import CandidateComponentOption
from .connection import ConnectionInterface, ConnectionInterfaceRole
from .models import CandidateClaim, ClaimSubjectType


ATTACHMENT_IDENTIFIER_KEY = "tool_attachment_installation.attachment_identifier"
INSTALLATION_FEATURE_REF_KEY = "tool_attachment_installation.feature_ref"
ISSUER_MANUFACTURER_KEY = "tool_attachment_installation.issuer_manufacturer"
SCOPE_KEY = "tool_attachment_installation.scope"


class ToolAttachmentInstallationBinding(BaseModel):
    """Accepted positive evidence for one concrete ToolAttachment installation.

    The binding is deliberately not a generic geometry rule and deliberately not an
    exclusion rule. It records that accepted manufacturer evidence establishes one
    attachment product as installable at one concrete feature of one Tool. Other
    attachment products remain free to qualify through reusable technical eligibility
    or through their own accepted installation evidence.
    """

    binding_id: str = Field(min_length=1)
    tool_ref: str = Field(min_length=1)
    source_product_ref: str = Field(min_length=1)
    installation_feature_id: str = Field(min_length=1)
    issuer_manufacturer: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls", mode="before")
    @classmethod
    def validate_source_urls(cls, source_urls: Any) -> Any:
        if not isinstance(source_urls, list):
            return source_urls
        normalized = sorted({str(url).strip() for url in source_urls if str(url).strip()})
        if not normalized:
            raise ValueError("ToolAttachment installation binding requires source URLs")
        return normalized


class EvidenceBoundToolAttachmentAssemblyOption(BaseModel):
    """ToolAttachment assembly whose Tool-side installability is evidence-bound.

    This is intentionally separate from ``ToolAttachmentAssemblyOption``. The latter
    represents reusable technical eligibility and remains unchanged. This model is used
    only when accepted first-party evidence says that an attachment installs on a named
    Tool feature but does not establish enough geometry to compile a reusable rule.
    """

    assembly_ref: str = Field(min_length=1)
    components: list[CandidateComponentOption] = Field(min_length=1)
    provided_interfaces: list[ConnectionInterface] = Field(min_length=1)
    installation_bindings: list[ToolAttachmentInstallationBinding] = Field(min_length=1)
    installation_method: ToolAttachmentInstallationMethod | None = None

    @model_validator(mode="after")
    def validate_assembly(self) -> EvidenceBoundToolAttachmentAssemblyOption:
        invalid_interfaces = [
            interface.interface_id
            for interface in self.provided_interfaces
            if interface.role != ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE
        ]
        if invalid_interfaces:
            raise ValueError(
                "evidence-bound ToolAttachment interfaces must use role "
                f"tool_attachment_tether_side: {invalid_interfaces!r}"
            )

        interface_ids = [interface.interface_id for interface in self.provided_interfaces]
        if len(set(interface_ids)) != len(interface_ids):
            raise ValueError(
                "evidence-bound ToolAttachment interface ids must be unique within an assembly"
            )

        component_refs = [component.component_ref for component in self.components]
        if len(set(component_refs)) != len(component_refs):
            raise ValueError(
                "evidence-bound ToolAttachment component refs must be unique within an assembly"
            )
        if not any(component.load_bearing for component in self.components):
            raise ValueError(
                "evidence-bound ToolAttachment assemblies require a load-bearing component"
            )

        component_products = {component.source_product_ref for component in self.components}
        invalid_bindings = [
            binding.binding_id
            for binding in self.installation_bindings
            if binding.source_product_ref not in component_products
        ]
        if invalid_bindings:
            raise ValueError(
                "ToolAttachment installation binding provenance must belong to a selected "
                f"assembly component product: {invalid_bindings!r}"
            )

        binding_ids = [binding.binding_id for binding in self.installation_bindings]
        if len(set(binding_ids)) != len(binding_ids):
            raise ValueError(
                "ToolAttachment installation binding ids must be unique within an assembly"
            )
        routes = [
            (binding.tool_ref, binding.source_product_ref, binding.installation_feature_id)
            for binding in self.installation_bindings
        ]
        if len(set(routes)) != len(routes):
            raise ValueError(
                "one evidence-bound assembly may retain only one binding per Tool/product/feature route"
            )

        if (
            self.installation_method is not None
            and self.installation_method.source_product_ref not in component_products
        ):
            raise ValueError(
                "ToolAttachment installation method provenance must belong to a selected "
                "assembly component product"
            )
        return self


class ToolAttachmentInstallationResolutionError(ValueError):
    """Accepted installation evidence is internally inconsistent or cannot be bound."""


def resolve_tool_attachment_installation_bindings(
    claims: list[CandidateClaim],
    *,
    tool_ref: str,
    attachment_product_refs: dict[str, str],
) -> list[ToolAttachmentInstallationBinding]:
    """Resolve accepted installation evidence to stable catalogue product refs.

    Raw manufacturer identifiers remain ingestion facts. ``attachment_product_refs`` is
    supplied by catalogue composition, so the resolver does not parse or invent catalogue
    identity from claim text. A referenced attachment that is absent from the supplied
    catalogue mapping simply cannot become an executable runtime binding yet.

    Returned bindings establish only positive support for the documented path. Missing
    bindings do not mean that another ToolAttachment is incompatible.
    """

    if not tool_ref.strip():
        raise ToolAttachmentInstallationResolutionError("tool_ref must be non-empty")
    if any(
        not str(identifier).strip() or not str(product_ref).strip()
        for identifier, product_ref in attachment_product_refs.items()
    ):
        raise ToolAttachmentInstallationResolutionError(
            "attachment product identifier mappings must use non-empty keys and refs"
        )

    grouped: dict[str, list[CandidateClaim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_type == ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH:
            grouped[claim.subject_ref].append(claim)

    bindings: list[ToolAttachmentInstallationBinding] = []
    for binding_id, binding_claims in sorted(grouped.items()):
        attachment_identifier = _required_text(
            binding_claims,
            ATTACHMENT_IDENTIFIER_KEY,
            binding_id,
        )
        feature_ref = _required_text(
            binding_claims,
            INSTALLATION_FEATURE_REF_KEY,
            binding_id,
        )
        issuer = _required_text(
            binding_claims,
            ISSUER_MANUFACTURER_KEY,
            binding_id,
        )
        scope = _required_text(binding_claims, SCOPE_KEY, binding_id)

        source_product_ref = attachment_product_refs.get(attachment_identifier)
        if source_product_ref is None:
            continue

        source_urls = sorted(
            {
                url
                for claim in binding_claims
                for url in [claim.source_url, *claim.supporting_source_urls]
                if url and url.strip()
            }
        )
        if not source_urls:
            raise ToolAttachmentInstallationResolutionError(
                f"installation binding {binding_id!r} has no accepted source URL"
            )

        bindings.append(
            ToolAttachmentInstallationBinding(
                binding_id=binding_id,
                tool_ref=tool_ref,
                source_product_ref=source_product_ref,
                installation_feature_id=feature_ref,
                issuer_manufacturer=issuer,
                scope=scope,
                source_urls=source_urls,
            )
        )

    return bindings


def _required_text(
    claims: list[CandidateClaim],
    property_key: str,
    binding_id: str,
) -> str:
    matches = [claim for claim in claims if claim.property_key == property_key]
    if not matches:
        raise ToolAttachmentInstallationResolutionError(
            f"installation binding {binding_id!r} is missing {property_key!r}"
        )
    values = {str(claim.value).strip() for claim in matches}
    if len(values) != 1 or not next(iter(values)):
        raise ToolAttachmentInstallationResolutionError(
            f"installation binding {binding_id!r} has conflicting/empty {property_key!r} values"
        )
    return next(iter(values))
