from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    MANUFACTURER_WEBPAGE = "manufacturer_webpage"
    MANUFACTURER_JSON = "manufacturer_json"
    MANUFACTURER_DOCUMENT = "manufacturer_document"


class ProductType(StrEnum):
    TOOL = "tool"
    TETHER = "tether"
    TOOL_ATTACHMENT = "tool_attachment"
    ANCHOR_ATTACHMENT = "anchor_attachment"
    CONTAINER = "container"
    UNKNOWN = "unknown"


class ProductIdentity(BaseModel):
    manufacturer: str
    product_type: ProductType = ProductType.UNKNOWN
    name: str | None = None
    model: str | None = None
    sku: str | None = None
    url: str
    manufacturer_ids: dict[str, str] = Field(default_factory=dict)


class SourceArtifact(BaseModel):
    url: str
    source_type: SourceType
    content_type: str
    body: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateClaim(BaseModel):
    property_key: str
    value: int | float | str | bool
    unit: str | None = None
    raw_value: str | None = None
    source_url: str
    evidence_method: str = "manufacturer_stated"
    extractor: str


class ReadinessIssue(BaseModel):
    code: str
    property_key: str | None = None
    detail: str | None = None


class IngestionResult(BaseModel):
    identity: ProductIdentity
    artifacts: list[SourceArtifact] = Field(default_factory=list)
    claims: list[CandidateClaim] = Field(default_factory=list)
    issues: list[ReadinessIssue] = Field(default_factory=list)

    def claim(self, property_key: str) -> CandidateClaim | None:
        return next((c for c in self.claims if c.property_key == property_key), None)
