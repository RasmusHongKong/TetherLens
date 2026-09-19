import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image

from tetherlens_ingest.field_recommendation import (
    FieldRecommendationCatalogue,
    FieldToolCatalogueEntry,
)
from tetherlens_ingest.field_tool_image import (
    FieldToolImage,
    candidate_tool_refs_from_image,
)
from tetherlens_ingest.field_tool_image_openai import (
    OpenAIToolImageRecognizer,
    ToolImageRecognitionProviderError,
)


def _image() -> FieldToolImage:
    image = Image.new("RGB", (16, 12), (200, 20, 20))
    exif = Image.Exif()
    exif[0x010E] = "source-page-answer"
    output = BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return FieldToolImage(content=output.getvalue(), media_type="image/jpeg")


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


def _completed_response(refs):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": (
                            '{"candidate_tool_refs":'
                            + str(refs).replace("'", '"')
                            + "}"
                        ),
                    }
                ],
            }
        ],
    }


def test_openai_adapter_sends_sanitized_image_and_closed_catalogue_schema(monkeypatch):
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json=_completed_response(["maker:tool-b"]),
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    refs = candidate_tool_refs_from_image(
        _image(),
        _catalogue(),
        OpenAIToolImageRecognizer(
            api_key="test-key",
            model="vision-test-model",
        ),
        max_candidates=2,
    )

    assert refs == ["maker:tool-b"]
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "vision-test-model"
    assert captured["json"]["store"] is False

    content = captured["json"]["input"][0]["content"]
    assert [part["type"] for part in content] == ["input_text", "input_image"]
    assert "source-page-answer" not in content[0]["text"]
    assert "maker:tool-a" in content[0]["text"]
    assert "maker:tool-b" in content[0]["text"]

    data_url = content[1]["image_url"]
    assert data_url.startswith("data:image/jpeg;base64,")
    encoded = data_url.split(",", 1)[1]
    with Image.open(BytesIO(base64.b64decode(encoded))) as decoded:
        assert dict(decoded.getexif()) == {}

    schema = captured["json"]["text"]["format"]["schema"]
    assert schema["properties"]["candidate_tool_refs"]["items"]["enum"] == [
        "maker:tool-a",
        "maker:tool-b",
    ]
    assert schema["properties"]["candidate_tool_refs"]["maxItems"] == 2


def test_openai_adapter_surfaces_provider_failures(monkeypatch):
    def fake_post(url, *, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(500, request=request, json={"error": "failed"})

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(ToolImageRecognitionProviderError, match="request failed"):
        candidate_tool_refs_from_image(
            _image(),
            _catalogue(),
            OpenAIToolImageRecognizer(
                api_key="test-key",
                model="vision-test-model",
            ),
        )


@pytest.mark.parametrize("output_text", ('["maker:tool-a"]', '"maker:tool-a"', "null", "1"))
def test_openai_adapter_rejects_non_object_structured_output(monkeypatch, output_text):
    def fake_post(url, *, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": output_text,
                            }
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(ToolImageRecognitionProviderError, match="JSON object"):
        candidate_tool_refs_from_image(
            _image(),
            _catalogue(),
            OpenAIToolImageRecognizer(
                api_key="test-key",
                model="vision-test-model",
            ),
        )


def test_openai_adapter_rejects_refusal_or_missing_output_text(monkeypatch):
    responses = iter(
        [
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "no"}],
                    }
                ],
            },
            {"status": "completed", "output": []},
        ]
    )

    def fake_post(url, *, headers, json, timeout):
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json=next(responses))

    monkeypatch.setattr(httpx, "post", fake_post)
    recognizer = OpenAIToolImageRecognizer(
        api_key="test-key",
        model="vision-test-model",
    )

    with pytest.raises(ToolImageRecognitionProviderError, match="refused"):
        candidate_tool_refs_from_image(
            _image(),
            _catalogue(),
            recognizer,
        )
    with pytest.raises(ToolImageRecognitionProviderError, match="output text"):
        candidate_tool_refs_from_image(
            _image(),
            _catalogue(),
            recognizer,
        )
