from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path

from tetherlens_ingest.field_recommendation import (
    FieldRecommendationCatalogue,
    FieldToolCatalogueEntry,
)
from tetherlens_ingest.field_tool_image import (
    FieldToolImage,
    candidate_tool_refs_from_image,
)
from tetherlens_ingest.field_tool_image_openai import OpenAIToolImageRecognizer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGUE = ROOT / "benchmarks" / "field_image_recognition_pilot.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a blind advisory Tool-image recognition smoke against the pilot "
            "identity catalogue. The expected answer is scored only after recognition."
        )
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--expected-tool-ref", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    return parser


def _load_catalogue(path: Path) -> FieldRecommendationCatalogue:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tools = payload.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("recognition pilot catalogue must contain Tool identities")

    return FieldRecommendationCatalogue(
        tools=[
            FieldToolCatalogueEntry(
                tool_ref=tool["tool_ref"],
                display_name=tool["display_name"],
            )
            for tool in tools
        ]
    )


def _image_media_type(path: Path) -> str:
    media_type, _ = mimetypes.guess_type(path.name)
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(
            "smoke image must have a .jpg/.jpeg, .png or .webp extension"
        )
    return media_type


def main() -> int:
    args = _parser().parse_args()

    catalogue = _load_catalogue(args.catalogue)
    allowed_refs = {tool.tool_ref for tool in catalogue.tools}
    if args.expected_tool_ref not in allowed_refs:
        raise ValueError(
            "expected Tool ref must already be present in the identity-only pilot catalogue"
        )

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise RuntimeError(
            f"missing API key in environment variable {args.api_key_env!r}"
        )

    image = FieldToolImage(
        content=args.image.read_bytes(),
        media_type=_image_media_type(args.image),
    )
    recognizer = OpenAIToolImageRecognizer(
        api_key=api_key,
        model=args.model,
    )

    candidate_refs = candidate_tool_refs_from_image(
        image,
        catalogue,
        recognizer,
        max_candidates=args.max_candidates,
    )

    try:
        rank = candidate_refs.index(args.expected_tool_ref) + 1
    except ValueError:
        rank = None

    result = {
        "catalogue_size": len(catalogue.tools),
        "max_candidates": args.max_candidates,
        "candidate_tool_refs": candidate_refs,
        "expected_tool_ref": args.expected_tool_ref,
        "expected_in_shortlist": rank is not None,
        "expected_rank": rank,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if rank is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
