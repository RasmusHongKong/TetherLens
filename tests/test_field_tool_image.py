from io import BytesIO

import pytest
from PIL import Image

from tetherlens_ingest.field_recommendation import (
    FieldInputRequirementKind,
    FieldRecommendationCatalogue,
    FieldRecommendationState,
    FieldToolCatalogueEntry,
    FieldToolObservation,
    run_field_recommendation,
)
from tetherlens_ingest.field_tool_image import (
    FieldImageRecognitionToolOption,
    FieldToolImage,
    candidate_tool_refs_from_image,
    sanitize_field_tool_image,
)


def _image_with_metadata() -> FieldToolImage:
    image = Image.new("RGB", (24, 12), (220, 20, 20))
    exif = Image.Exif()
    exif[0x010E] = "known-answer: tool-a"
    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return FieldToolImage(content=output.getvalue(), media_type="image/jpeg")


def _transparent_image_with_hidden_rgb() -> FieldToolImage:
    image = Image.new("RGBA", (24, 12), (220, 20, 20, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return FieldToolImage(content=output.getvalue(), media_type="image/png")


def _catalogue() -> FieldRecommendationCatalogue:
    return FieldRecommendationCatalogue(
        tools=[
            FieldToolCatalogueEntry(
                tool_ref="maker:tool-a",
                display_name="Maker Tool A",
            ),
            FieldToolCatalogueEntry(
                tool_ref="maker:tool-b",
                display_name="Maker Tool B",
            ),
        ]
    )


class _CapturingRecognizer:
    def __init__(self, refs):
        self.refs = refs
        self.image = None
        self.tools = None
        self.max_candidates = None

    def recognize_tool_refs(self, image, tools, *, max_candidates):
        self.image = image
        self.tools = tools
        self.max_candidates = max_candidates
        return self.refs


def test_sanitization_strips_metadata_and_bounds_pixels():
    sanitized = sanitize_field_tool_image(_image_with_metadata(), max_dimension=10)

    assert sanitized.media_type == "image/jpeg"
    with Image.open(BytesIO(sanitized.content)) as image:
        assert image.size == (10, 5)
        assert dict(image.getexif()) == {}


def test_sanitization_flattens_transparency_without_exposing_hidden_rgb():
    sanitized = sanitize_field_tool_image(_transparent_image_with_hidden_rgb())

    with Image.open(BytesIO(sanitized.content)) as image:
        assert image.mode == "RGB"
        red, green, blue = image.getpixel((image.width // 2, image.height // 2))
        assert min(red, green, blue) >= 250


def test_image_recognizer_receives_only_sanitized_pixels_and_catalogue_identity():
    recognizer = _CapturingRecognizer(["maker:tool-b", "maker:tool-a"])

    refs = candidate_tool_refs_from_image(
        _image_with_metadata(),
        _catalogue(),
        recognizer,
        max_candidates=1,
    )

    assert refs == ["maker:tool-b"]
    assert recognizer.max_candidates == 1
    assert recognizer.tools == (
        FieldImageRecognitionToolOption(
            tool_ref="maker:tool-a",
            display_name="Maker Tool A",
        ),
        FieldImageRecognitionToolOption(
            tool_ref="maker:tool-b",
            display_name="Maker Tool B",
        ),
    )
    assert recognizer.image is not None
    assert recognizer.image.media_type == "image/jpeg"
    with Image.open(BytesIO(recognizer.image.content)) as image:
        assert dict(image.getexif()) == {}


def test_image_candidate_producer_rejects_unknown_or_duplicate_refs():
    with pytest.raises(ValueError, match="outside the supplied field catalogue"):
        candidate_tool_refs_from_image(
            _image_with_metadata(),
            _catalogue(),
            _CapturingRecognizer(["maker:unknown"]),
        )

    with pytest.raises(ValueError, match="must be unique"):
        candidate_tool_refs_from_image(
            _image_with_metadata(),
            _catalogue(),
            _CapturingRecognizer(["maker:tool-a", "maker:tool-a"]),
        )


def test_one_image_candidate_still_requires_explicit_worker_confirmation():
    catalogue = _catalogue()
    refs = candidate_tool_refs_from_image(
        _image_with_metadata(),
        catalogue,
        _CapturingRecognizer(["maker:tool-a"]),
    )

    result = run_field_recommendation(
        FieldToolObservation(candidate_tool_refs=refs),
        catalogue,
    )

    assert result.state == FieldRecommendationState.NEEDS_INPUT
    requirement = result.tool_resolution.requirements[0]
    assert requirement.kind == FieldInputRequirementKind.TOOL_CONFIRMATION
    assert [option.ref for option in requirement.options] == ["maker:tool-a"]


@pytest.mark.parametrize(
    ("content", "media_type"),
    (
        (b"not-an-image", "image/jpeg"),
        (_image_with_metadata().content, "image/png"),
    ),
)
def test_image_sanitization_fails_closed_on_invalid_or_mismatched_input(
    content: bytes,
    media_type: str,
):
    with pytest.raises(ValueError):
        sanitize_field_tool_image(
            FieldToolImage(content=content, media_type=media_type)
        )
