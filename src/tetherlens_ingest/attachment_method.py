from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .models import CandidateClaim, ClaimSubjectType


ATTACHMENT_METHOD_CODE_KEY = "attachment_method_code"


class AttachmentMethodResolutionError(ValueError):
    """Accepted ToolAttachment method claims cannot be resolved consistently."""


class ToolAttachmentInstallationMethod(BaseModel):
    """Canonical ToolAttachment retention method plus accepted evidence provenance.

    The code describes how the ToolAttachment itself is physically retained on the
    Tool. It is deliberately descriptive runtime provenance: eligibility, compatibility,
    product constraints and candidate identity remain separate concerns.
    """

    source_product_ref: str = Field(min_length=1)
    attachment_method_code: str = Field(min_length=1)
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls")
    @classmethod
    def validate_source_urls(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("attachment method source URLs must be non-empty")
        if len(set(values)) != len(values):
            raise ValueError("attachment method source URLs must be unique")
        return values


def resolve_tool_attachment_installation_method(
    claims: list[CandidateClaim],
    *,
    source_product_ref: str,
) -> ToolAttachmentInstallationMethod | None:
    """Resolve accepted product-level method claims into one runtime provenance object.

    Callers must pass only accepted/reconciled claims. Multiple accepted sources may
    repeat the same canonical method and are retained as provenance. Conflicting accepted
    method values fail closed rather than being picked by source order. The vocabulary is
    intentionally open/versioned, so this resolver reconciles exact codes without
    maintaining a second closed enum.
    """

    method_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.subject_ref == "self"
        and claim.property_key == ATTACHMENT_METHOD_CODE_KEY
    ]
    if not method_claims:
        return None

    methods = {str(claim.value).strip() for claim in method_claims}
    if "" in methods:
        raise AttachmentMethodResolutionError(
            "accepted ToolAttachment attachment_method_code must be non-empty"
        )
    if len(methods) != 1:
        raise AttachmentMethodResolutionError(
            "conflicting accepted ToolAttachment attachment_method_code claims: "
            f"{sorted(methods)!r}"
        )

    source_urls = sorted(
        {
            url
            for claim in method_claims
            for url in [claim.source_url, *claim.supporting_source_urls]
            if url.strip()
        }
    )
    if not source_urls:  # CandidateClaim.source_url is required, kept defensive here.
        raise AttachmentMethodResolutionError(
            "accepted ToolAttachment attachment_method_code requires source provenance"
        )

    return ToolAttachmentInstallationMethod(
        source_product_ref=source_product_ref,
        attachment_method_code=next(iter(methods)),
        source_urls=source_urls,
    )
