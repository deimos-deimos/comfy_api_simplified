"""Unit tests for mcp_server.py — all tests mock _api, no live ComfyUI required."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from comfy_api_simplified.exceptions import ComfyApiError, NodeNotFoundError


@pytest.fixture
def mock_api():
    """Patch the module-level _api singleton in mcp_server."""
    with patch("comfy_api_simplified.mcp_server._api") as m:
        yield m


# ── Discovery tools ───────────────────────────────────────────────────────────

def test_list_node_types_returns_sorted(mock_api):
    from comfy_api_simplified.mcp_server import list_node_types
    mock_api.get_object_info.return_value = {"ZNode": {}, "ANode": {}, "MNode": {}}
    assert list_node_types() == ["ANode", "MNode", "ZNode"]


def test_list_node_types_error(mock_api):
    from comfy_api_simplified.mcp_server import list_node_types
    mock_api.get_object_info.side_effect = ComfyApiError("connection refused")
    result = list_node_types()
    assert result.startswith("ERROR:")


def test_get_node_type_info_combo_input(mock_api):
    from comfy_api_simplified.mcp_server import get_node_type_info
    mock_api.get_object_info.return_value = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {"ckpt_name": [["model_a.safetensors", "model_b.ckpt"], {}]},
                "optional": {},
            },
            "output": ["MODEL", "CLIP", "VAE"],
            "display_name": "Load Checkpoint",
            "category": "loaders",
            "description": "",
        }
    }
    result = get_node_type_info("CheckpointLoaderSimple")
    assert result["inputs"]["ckpt_name"]["type"] == "COMBO"
    assert result["inputs"]["ckpt_name"]["options"] == ["model_a.safetensors", "model_b.ckpt"]
    assert result["inputs"]["ckpt_name"]["default"] == "model_a.safetensors"
    assert result["outputs"] == ["MODEL", "CLIP", "VAE"]


def test_get_node_type_info_scalar_input(mock_api):
    from comfy_api_simplified.mcp_server import get_node_type_info
    mock_api.get_object_info.return_value = {
        "KSampler": {
            "input": {
                "required": {"steps": ["INT", {"default": 20, "min": 1, "max": 10000}]},
                "optional": {},
            },
            "output": ["LATENT"],
            "display_name": "KSampler",
            "category": "sampling",
            "description": "",
        }
    }
    result = get_node_type_info("KSampler")
    assert result["inputs"]["steps"]["type"] == "INT"
    assert result["inputs"]["steps"]["default"] == 20
    assert result["inputs"]["steps"]["min"] == 1
    assert result["inputs"]["steps"]["max"] == 10000
    assert result["inputs"]["steps"]["options"] is None


def test_get_node_type_info_not_found(mock_api):
    from comfy_api_simplified.mcp_server import get_node_type_info
    mock_api.get_object_info.return_value = {}
    result = get_node_type_info("NonExistent")
    assert "not found" in result


def test_list_models_extracts_checkpoints_and_loras(mock_api):
    from comfy_api_simplified.mcp_server import list_models
    mock_api.get_object_info.return_value = {
        "CheckpointLoaderSimple": {
            "input": {
                "required": {"ckpt_name": [["v1-5.safetensors", "sdxl.safetensors"], {}]},
                "optional": {},
            }
        },
        "LoraLoader": {
            "input": {
                "required": {"lora_name": [["style_lora.safetensors"], {}]},
                "optional": {},
            }
        },
    }
    result = list_models()
    assert "checkpoints" in result
    assert "v1-5.safetensors" in result["checkpoints"]
    assert "loras" in result
    assert "style_lora.safetensors" in result["loras"]


def test_list_models_ignores_non_file_combos(mock_api):
    from comfy_api_simplified.mcp_server import list_models
    mock_api.get_object_info.return_value = {
        "KSampler": {
            "input": {
                "required": {
                    "sampler_name": [["euler", "dpm_2", "ddim"], {}],
                    "scheduler": [["normal", "karras"], {}],
                },
                "optional": {},
            }
        }
    }
    result = list_models()
    assert result == {}


def test_list_models_error(mock_api):
    from comfy_api_simplified.mcp_server import list_models
    mock_api.get_object_info.side_effect = ComfyApiError("server down")
    result = list_models()
    assert result.startswith("ERROR:")


def test_get_system_stats(mock_api):
    from comfy_api_simplified.mcp_server import get_system_stats
    mock_api.get_system_stats.return_value = {"system": {"python_version": "3.11"}, "devices": []}
    result = get_system_stats()
    assert result["system"]["python_version"] == "3.11"


def test_list_embeddings_sorted(mock_api):
    from comfy_api_simplified.mcp_server import list_embeddings
    mock_api.get_embeddings.return_value = ["EasyNegative", "badhandv4", "ADetailer"]
    assert list_embeddings() == ["ADetailer", "EasyNegative", "badhandv4"]


def test_list_embeddings_error(mock_api):
    from comfy_api_simplified.mcp_server import list_embeddings
    mock_api.get_embeddings.side_effect = ComfyApiError("not found")
    result = list_embeddings()
    assert result.startswith("ERROR:")


# ── Workflow tools ────────────────────────────────────────────────────────────

def test_load_workflow_valid_file(tmp_path):
    from comfy_api_simplified.mcp_server import load_workflow
    wf = {"1": {"class_type": "KSampler", "inputs": {"steps": 20}, "_meta": {"title": "KSampler"}}}
    f = tmp_path / "wf.json"
    f.write_text(json.dumps(wf))
    result = load_workflow(str(f))
    assert isinstance(result, dict)
    assert "1" in result


def test_load_workflow_missing_file():
    from comfy_api_simplified.mcp_server import load_workflow
    result = load_workflow("/nonexistent/path/wf.json")
    assert result.startswith("ERROR:")


def test_list_nodes_returns_fields():
    from comfy_api_simplified.mcp_server import list_nodes
    wf = {
        "3": {"class_type": "KSampler", "inputs": {}, "_meta": {"title": "KSampler"}},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {}, "_meta": {"title": "Load Checkpoint"}},
    }
    result = list_nodes(wf)
    assert len(result) == 2
    ids = {r["id"] for r in result}
    assert "3" in ids and "4" in ids
    titles = {r["title"] for r in result}
    assert "KSampler" in titles and "Load Checkpoint" in titles


def test_set_node_param_returns_modified_workflow():
    from comfy_api_simplified.mcp_server import set_node_param
    wf = {"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old"}, "_meta": {"title": "positive"}}}
    result = set_node_param(wf, "positive", "text", "new text")
    assert isinstance(result, dict)
    assert result["1"]["inputs"]["text"] == "new text"


def test_set_node_param_node_not_found():
    from comfy_api_simplified.mcp_server import set_node_param
    wf = {"1": {"class_type": "KSampler", "inputs": {}, "_meta": {"title": "KSampler"}}}
    result = set_node_param(wf, "NonExistent", "param", "value")
    assert result.startswith("ERROR:")


def test_get_node_param_returns_value():
    from comfy_api_simplified.mcp_server import get_node_param
    wf = {"1": {"class_type": "KSampler", "inputs": {"steps": 25}, "_meta": {"title": "KSampler"}}}
    assert get_node_param(wf, "KSampler", "steps") == 25


def test_get_node_param_node_not_found():
    from comfy_api_simplified.mcp_server import get_node_param
    wf = {"1": {"class_type": "KSampler", "inputs": {}, "_meta": {"title": "KSampler"}}}
    result = get_node_param(wf, "NonExistent", "steps")
    assert result.startswith("ERROR:")


# ── Execution tools ───────────────────────────────────────────────────────────

def test_upload_image_returns_server_path(mock_api):
    from comfy_api_simplified.mcp_server import upload_image
    mock_api.upload_image.return_value = {"subfolder": "uploads", "name": "my_image.png", "type": "input"}
    assert upload_image("/local/my_image.png") == "uploads/my_image.png"


def test_upload_image_no_subfolder(mock_api):
    from comfy_api_simplified.mcp_server import upload_image
    mock_api.upload_image.return_value = {"subfolder": "", "name": "my_image.png", "type": "input"}
    assert upload_image("/local/my_image.png") == "my_image.png"


def test_upload_image_error(mock_api):
    from comfy_api_simplified.mcp_server import upload_image
    mock_api.upload_image.side_effect = ComfyApiError("server error")
    result = upload_image("/bad/path.png")
    assert result.startswith("ERROR:")


def test_run_workflow_saves_files_from_history(mock_api, tmp_path):
    from comfy_api_simplified.mcp_server import run_workflow
    import comfy_api_simplified.mcp_server as srv

    wf = {
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
            "_meta": {"title": "Save Image"},
        }
    }
    fake_prompt_id = "a3f9c12b-0000-0000-0000-000000000000"
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    mock_api.queue_prompt_and_wait = MagicMock(return_value=(fake_prompt_id, []))
    mock_api.get_history.return_value = {
        fake_prompt_id: {
            "outputs": {
                "9": {
                    "images": [
                        {"filename": "ComfyUI_00001_.png", "subfolder": "", "type": "output"}
                    ]
                }
            }
        }
    }
    mock_api.get_image.return_value = fake_image_bytes

    original_output_dir = srv._OUTPUT_DIR
    srv._OUTPUT_DIR = tmp_path
    try:
        with patch("asyncio.run", return_value=(fake_prompt_id, [])):
            result = run_workflow(wf, "Save Image")
    finally:
        srv._OUTPUT_DIR = original_output_dir

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].endswith("ComfyUI_00001_.png")
    assert Path(result[0]).exists()


def test_run_workflow_saves_ws_inline_images(mock_api, tmp_path):
    from comfy_api_simplified.mcp_server import run_workflow
    import comfy_api_simplified.mcp_server as srv

    wf = {"9": {"class_type": "SaveImage", "inputs": {}, "_meta": {"title": "Save Image"}}}
    fake_prompt_id = "b1c2d3e4-0000-0000-0000-000000000000"
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

    original_output_dir = srv._OUTPUT_DIR
    srv._OUTPUT_DIR = tmp_path
    try:
        with patch("asyncio.run", return_value=(fake_prompt_id, [fake_image_bytes])):
            result = run_workflow(wf, "Save Image")
    finally:
        srv._OUTPUT_DIR = original_output_dir

    assert isinstance(result, list)
    assert len(result) == 1
    assert "ws_image_0000.png" in result[0]
    assert Path(result[0]).exists()


def test_run_workflow_error(mock_api, tmp_path):
    from comfy_api_simplified.mcp_server import run_workflow
    import comfy_api_simplified.mcp_server as srv

    original_output_dir = srv._OUTPUT_DIR
    srv._OUTPUT_DIR = tmp_path
    try:
        with patch("asyncio.run", side_effect=ComfyApiError("execution error")):
            result = run_workflow({}, "Save Image")
    finally:
        srv._OUTPUT_DIR = original_output_dir

    assert result.startswith("ERROR:")


def test_get_queue_status(mock_api):
    from comfy_api_simplified.mcp_server import get_queue_status
    mock_api.get_queue.return_value = {
        "queue_running": [["p1", "abc"]],
        "queue_pending": [["p2", "def"], ["p3", "ghi"]],
    }
    result = get_queue_status()
    assert result["queue_running"] == 1
    assert result["queue_pending"] == 2


def test_get_queue_status_error(mock_api):
    from comfy_api_simplified.mcp_server import get_queue_status
    mock_api.get_queue.side_effect = ComfyApiError("unreachable")
    result = get_queue_status()
    assert result.startswith("ERROR:")


def test_interrupt_execution_ok(mock_api):
    from comfy_api_simplified.mcp_server import interrupt_execution
    mock_api.interrupt.return_value = None
    assert interrupt_execution() == "OK"


def test_interrupt_execution_error(mock_api):
    from comfy_api_simplified.mcp_server import interrupt_execution
    mock_api.interrupt.side_effect = ComfyApiError("nothing running")
    result = interrupt_execution()
    assert result.startswith("ERROR:")
