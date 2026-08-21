from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    MANUFACTURER_WEBPAGE = "manufacturer_webpage"
    MANUFACTURER_JSON = "manufacturer_json"
    MANUFACTURER_DOCUMENT = "manufacturer_document"
    SECONDARY_WEBPAGE = "secondary_webpage"


class ProductType(StrEnum):
    TOOL = "tool"
    TETHER = "tether"
    TOOL_ATTACHMENT = "tool_attachment"
    ANCHOR_ATTACHMENT = "anchor_attachment"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class ClaimSubjectType(StrEnum):
    PRODUCT = "product"
    PRODUCT_VARIANT = "product_variant"
    PHYSICAL_INTERFACE = "physical_interface"
    TETHER_CONNECTION_POINT = "tether_connection_point"
    CONNECTOR_SPEC = "connector_spec"
    RELATED_PRODUCT = "related_product"
    OPERATIONAL_PROFILE = "operational_profile"


class ClaimType(StrEnum):
    DIRECT = "direct"
    MEASURED = "measured"
    DECLARED_CONSTRAINT = "declared_constraint"
    DERIVED = "derived"


class ConstraintOperator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    REQUIRES = "requires"
    PROHIBITS = "prohibits"


class ProductIdentity(BaseModel):
    manufacturer: str
    product_type: ProductType = ProductType.UNKNOWN
    name: str | None = None
    model: str | None = None
    sku: str | None = None
    url: str
    manufacturer_ids: dict[str, str] = Field(default_factory=dict)


class SourceRequest(BaseModel):
    url: str
    source_type: SourceType = SourceType.MANUFACTURER_WEBPAGE
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceArtifact(BaseModel):
    url: str
    source_type: SourceType
    content_type: str
    body: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateClaim(BaseModel):
    subject_type: ClaimSubjectType = ClaimSubjectType.PRODUCT
    subject_ref: str = "self"
    property_key: str
    value: int | float | str | bool
    unit: str | None = None
    raw_value: str | None = None
    source_url: str
    supporting_source_urls: list[str] = Field(default_factory=list)
    evidence_method: str = "manufacturer_stated"
    extractor: str
    # Transitional ingestion metadata. Existing adapters can remain unclassified
    # while new structured constraints map explicitly to the persisted Claim model.
    claim_type: ClaimType | None = None
    constraint_operator: ConstraintOperator | None = None


class AcquisitionObservation(BaseModel):
    code: str
    value: int | float | str | bool | None = None
    detail: str | None = None
    source_url: str | None = None
    extractor: str | None = None


class ReadinessIssue(BaseModel):
    code: str
    property_key: str | None = None
    detail: str | None = None


class IngestionResult(BaseModel):
    identity: ProductIdentity
    artifacts: list[SourceArtifact] = Field(default_factory=list)
    claims: list[CandidateClaim] = Field(default_factory=list)
    acquisition_observations: list[AcquisitionObservation] = Field(default_factory=list)
    issues: list[ReadinessIssue] = Field(default_factory=list)
    readiness_assessed: bool = False

    def claim(self, property_key: str) -> CandidateClaim | None:
        return next((c for c in self.claims if c.property_key == property_key), None)

    def claims_for(
        self,
        property_key: str,
        subject_type: ClaimSubjectType | None = None,
        subject_ref: str | None = None,
    ) -> list[CandidateClaim]:
        return [
            claim
            for claim in self.claims
            if claim.property_key == property_key
            and (subject_type is None or claim.subject_type == subject_type)
            and (subject_ref is None or claim.subject_ref == subject_ref)
        ]
