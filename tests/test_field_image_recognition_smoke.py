import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_field_image_recognition_smoke.py"
CATALOGUE_PATH = ROOT / "benchmarks" / "field_image_recognition_pilot.json"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "run_field_image_recognition_smoke",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pilot_recognition_catalogue_uses_existing_real_tool_identities():
    payload = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

    assert [tool["tool_ref"] for tool in payload["tools"]] == [
        "Hilti:2253847",
        "Milwaukee:48-22-7215",
        "Milwaukee:2607-20",
        "StopDrop:SDKN1802",
    ]
    assert all(tool["display_name"].strip() for tool in payload["tools"])
    assert "expected_tool_ref" not in payload
    assert "expected" not in payload


def test_smoke_catalogue_is_identity_only_and_valid_for_recognition():
    module = _load_script_module()
    catalogue = module._load_catalogue(CATALOGUE_PATH)

    assert len(catalogue.tools) == 4
    assert all(tool.operational_profiles == [] for tool in catalogue.tools)
    assert catalogue.tethers == []
    assert catalogue.anchor_paths == []
    assert catalogue.tool_attachment_assemblies == []
    assert catalogue.evidence_bound_tool_attachment_assemblies == []


@pytest.mark.parametrize(
    ("filename", "expected"),
    (
        ("tool.jpg", "image/jpeg"),
        ("tool.jpeg", "image/jpeg"),
        ("tool.png", "image/png"),
        ("tool.webp", "image/webp"),
    ),
)
def test_smoke_image_media_type_is_explicitly_bounded(filename, expected):
    module = _load_script_module()

    assert module._image_media_type(Path(filename)) == expected


def test_smoke_image_rejects_unsupported_extension():
    module = _load_script_module()

    with pytest.raises(ValueError, match="jpg/.jpeg"):
        module._image_media_type(Path("tool.gif"))
