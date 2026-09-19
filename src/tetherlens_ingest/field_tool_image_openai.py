from __future__ import annotations

import base64
import json
from typing import Sequence

import httpx

from .field_tool_image import (
    FieldImageRecognitionToolOption,
    FieldToolImage,
)


class ToolImageRecognitionProviderError(RuntimeError):
    """Raised when a concrete vision provider cannot return a usable shortlist."""


class OpenAIToolImageRecognizer:
    """OpenAI Responses API adapter for the provider-neutral Tool recognizer boundary.

    The caller supplies the model explicitly. The adapter sends only the sanitized image
    it receives plus the allowed catalogue Tool identities and requests structured refs.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key must be non-empty")
        if not model.strip():
            raise ValueError("OpenAI vision model must be non-empty")
        if timeout_seconds <= 0:
            raise ValueError("OpenAI timeout must be positive")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def recognize_tool_refs(
        self,
        image: FieldToolImage,
        tools: Sequence[FieldImageRecognitionToolOption],
        *,
        max_candidates: int,
    ) -> Sequence[str]:
        if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
            raise ValueError("max_candidates must be a positive integer")
        if max_candidates <= 0:
            raise ValueError("max_candidates must be a positive integer")
        if not tools:
            return []

        tool_refs = [tool.tool_ref for tool in tools]
        if len(set(tool_refs)) != len(tool_refs):
            raise ValueError("recognition Tool options must have unique refs")

        options = [
            {
                "tool_ref": tool.tool_ref,
                "display_name": tool.display_name,
            }
            for tool in tools
        ]
        prompt = (
            "Identify the pictured physical Tool only against the supplied catalogue options. "
            "Return up to the requested number of plausible exact Tool refs, best visual match "
            "first. Visible manufacturer/model markings in the image are valid evidence. "
            "Do not choose a Battery or operational profile, do not invent a Tool outside the "
            "list, and return an empty list when none is a plausible match. Catalogue options: "
            + json.dumps(options, ensure_ascii=False, separators=(",", ":"))
        )

        encoded_image = base64.b64encode(image.content).decode("ascii")
        schema = {
            "type": "object",
            "properties": {
                "candidate_tool_refs": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": tool_refs,
                    },
                    "maxItems": min(max_candidates, len(tool_refs)),
                    "uniqueItems": True,
                }
            },
            "required": ["candidate_tool_refs"],
            "additionalProperties": False,
        }
        request_body = {
            "model": self.model,
            "store": False,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": (
                                f"data:{image.media_type};base64,{encoded_image}"
                            ),
                            "detail": "auto",
                        },
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "tetherlens_tool_candidates",
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": 200,
        }

        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolImageRecognitionProviderError(
                "OpenAI image recognition request failed"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ToolImageRecognitionProviderError(
                "OpenAI image recognition response was not valid JSON"
            ) from exc

        if payload.get("status") == "incomplete":
            raise ToolImageRecognitionProviderError(
                "OpenAI image recognition response was incomplete"
            )

        output_text = _response_output_text(payload)
        try:
            parsed = json.loads(output_text)
        except (TypeError, ValueError) as exc:
            raise ToolImageRecognitionProviderError(
                "OpenAI image recognition output was not valid structured JSON"
            ) from exc

        refs = parsed.get("candidate_tool_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            raise ToolImageRecognitionProviderError(
                "OpenAI image recognition output did not contain Tool refs"
            )
        return refs


def _response_output_text(payload: dict) -> str:
    for item in payload.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if not isinstance(part, dict):
                continue
            if part.get("type") == "refusal":
                raise ToolImageRecognitionProviderError(
                    "OpenAI image recognition request was refused"
                )
            if part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    return text

    raise ToolImageRecognitionProviderError(
        "OpenAI image recognition response did not contain output text"
    )
