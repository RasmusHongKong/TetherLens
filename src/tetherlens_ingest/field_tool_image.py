from __future__ import annotations

from io import BytesIO
from typing import Protocol, Sequence

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator

from .field_recommendation import FieldRecommendationCatalogue


_SUPPORTED_MEDIA_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
_MAX_IMAGE_PIXELS = 25_000_000
_DEFAULT_MAX_DIMENSION = 1600


class FieldToolImage(BaseModel):
    """One worker-supplied Tool image with no source identity metadata.

    The demand-side recognition boundary accepts only encoded image bytes plus the
    declared media type. Source URLs, filenames, page titles, alt text and known
    product identity are deliberately absent from this model.
    """

    content: bytes = Field(min_length=1)
    media_type: str = Field(min_length=1)

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _SUPPORTED_MEDIA_TYPES:
            raise ValueError(
                "field Tool image media type must be image/jpeg, image/png or image/webp"
            )
        return normalized


class FieldImageRecognitionToolOption(BaseModel):
    """Catalogue identity exposed to an advisory image recognizer."""

    tool_ref: str = Field(min_length=1)
    display_name: str = Field(min_length=1)


class ToolImageRecognizer(Protocol):
    """Provider boundary for advisory Tool image recognition.

    Implementations receive sanitized image pixels plus only the catalogue Tool
    identities they are allowed to return. They do not receive operational profiles,
    Battery/configuration identity, recommendation facts or a pre-confirmed Tool.
    """

    def recognize_tool_refs(
        self,
        image: FieldToolImage,
        tools: Sequence[FieldImageRecognitionToolOption],
        *,
        max_candidates: int,
    ) -> Sequence[str]:
        ...


def sanitize_field_tool_image(
    image: FieldToolImage,
    *,
    max_dimension: int = _DEFAULT_MAX_DIMENSION,
) -> FieldToolImage:
    """Decode and re-encode a static Tool image before recognition.

    Re-encoding strips EXIF/text metadata and normalizes orientation. The recognizer
    therefore receives image pixels rather than filename/source/page metadata. Large
    mobile photos are bounded to a practical longest edge without changing aspect ratio.
    """

    if isinstance(max_dimension, bool) or not isinstance(max_dimension, int):
        raise ValueError("max_dimension must be a positive integer")
    if max_dimension <= 0:
        raise ValueError("max_dimension must be a positive integer")

    try:
        with Image.open(BytesIO(image.content)) as opened:
            actual_format = opened.format
            expected_format = _SUPPORTED_MEDIA_TYPES[image.media_type]
            if actual_format != expected_format:
                raise ValueError(
                    "declared field Tool image media type does not match encoded image"
                )
            if getattr(opened, "is_animated", False):
                raise ValueError("field Tool image must be a single static image")
            if opened.width * opened.height > _MAX_IMAGE_PIXELS:
                raise ValueError(
                    "field Tool image exceeds the maximum decoded pixel count"
                )

            normalized = ImageOps.exif_transpose(opened)
            normalized.load()
            normalized.thumbnail(
                (max_dimension, max_dimension),
                Image.Resampling.LANCZOS,
            )
            normalized = normalized.convert("RGB")

            output = BytesIO()
            normalized.save(
                output,
                format="JPEG",
                quality=90,
                optimize=True,
            )
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("field Tool image could not be decoded") from exc

    return FieldToolImage(
        content=output.getvalue(),
        media_type="image/jpeg",
    )


def candidate_tool_refs_from_image(
    image: FieldToolImage,
    catalogue: FieldRecommendationCatalogue,
    recognizer: ToolImageRecognizer,
    *,
    max_candidates: int = 5,
) -> list[str]:
    """Return a bounded advisory Tool shortlist from one sanitized image.

    Recognition is not identity confirmation. This function returns catalogue refs only;
    callers must pass them through FieldToolObservation(candidate_tool_refs=...) so the
    existing field coordinator still requires explicit worker confirmation.
    """

    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise ValueError("max_candidates must be a positive integer")
    if max_candidates <= 0:
        raise ValueError("max_candidates must be a positive integer")

    tools = tuple(
        FieldImageRecognitionToolOption(
            tool_ref=entry.tool_ref,
            display_name=entry.display_name,
        )
        for entry in catalogue.tools
    )
    if not tools:
        return []

    sanitized = sanitize_field_tool_image(image)
    returned = recognizer.recognize_tool_refs(
        sanitized,
        tools,
        max_candidates=max_candidates,
    )
    if isinstance(returned, (str, bytes)):
        raise ValueError("image recognizer must return a sequence of Tool refs")

    try:
        refs = list(returned)
    except TypeError as exc:
        raise ValueError("image recognizer must return a sequence of Tool refs") from exc

    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError("image recognizer Tool refs must be non-empty strings")
    if len(set(refs)) != len(refs):
        raise ValueError("image recognizer Tool refs must be unique")

    known_refs = {tool.tool_ref for tool in tools}
    unknown_refs = [ref for ref in refs if ref not in known_refs]
    if unknown_refs:
        raise ValueError(
            "image recognizer returned Tool refs outside the supplied field catalogue: "
            f"{unknown_refs!r}"
        )

    return refs[:max_candidates]
