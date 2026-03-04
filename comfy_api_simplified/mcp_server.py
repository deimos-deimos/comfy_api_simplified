"""
MCP server exposing ComfyUI as an AI agent tool suite.

Configuration via environment variables:
  COMFY_URL         - ComfyUI server URL (default: http://127.0.0.1:8188)
  COMFY_USER        - HTTP Basic Auth username (default: empty = no auth)
  COMFY_PASSWORD    - HTTP Basic Auth password (default: empty)
  COMFY_OUTPUT_DIR  - Directory to save output images (default: /tmp/comfy_mcp_output)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from comfy_api_simplified.comfy_api_wrapper import ComfyApiWrapper
from comfy_api_simplified.comfy_workflow_wrapper import ComfyWorkflowWrapper
from comfy_api_simplified.exceptions import ComfyApiError, NodeNotFoundError

_log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
_COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
_COMFY_USER = os.environ.get("COMFY_USER", "")
_COMFY_PASSWORD = os.environ.get("COMFY_PASSWORD", "")
_OUTPUT_DIR = Path(os.environ.get("COMFY_OUTPUT_DIR", "/tmp/comfy_mcp_output"))

# ── Shared client (module-level singleton) ────────────────────────────────────
_api = ComfyApiWrapper(url=_COMFY_URL, user=_COMFY_USER, password=_COMFY_PASSWORD)

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP("ComfyUI MCP Server")


def _fmt_error(e: Exception) -> str:
    return f"ERROR: {type(e).__name__}: {e}"


# ── Model extraction helpers ──────────────────────────────────────────────────

_MODEL_NODE_CATEGORIES: dict[str, str] = {
    "CheckpointLoaderSimple": "checkpoints",
    "CheckpointLoader": "checkpoints",
    "LoraLoader": "loras",
    "LoraLoaderModelOnly": "loras",
    "VAELoader": "vaes",
    "UNETLoader": "unets",
    "CLIPLoader": "clips",
    "ControlNetLoader": "controlnets",
    "DiffusersLoader": "diffusers",
    "HypernetworkLoader": "hypernetworks",
    "GLIGENLoader": "gligen",
    "StyleModelLoader": "style_models",
    "UpscaleModelLoader": "upscale_models",
}

_PARAM_KEYWORDS: list[tuple[str, str]] = [
    ("ckpt_name", "checkpoints"),
    ("lora_name", "loras"),
    ("vae_name", "vaes"),
    ("unet_name", "unets"),
    ("clip_name", "clips"),
    ("control_net_name", "controlnets"),
    ("upscale_model", "upscale_models"),
    ("style_model_name", "style_models"),
    ("hypernetwork_name", "hypernetworks"),
]

_MODEL_EXTENSIONS = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf"}


# ── Discovery tools ───────────────────────────────────────────────────────────

@mcp.tool
def list_node_types() -> list[str] | str:
    """
    Lists all node class types available in the connected ComfyUI instance.

    Returns a sorted list of class type names (e.g. 'KSampler',
    'CheckpointLoaderSimple', 'CLIPTextEncode'). Use get_node_type_info()
    to see the parameters accepted by any specific class type.

    Returns:
        list[str]: Sorted list of available node class type names.
    """
    try:
        info = _api.get_object_info()
        return sorted(info.keys())
    except ComfyApiError as e:
        return _fmt_error(e)


@mcp.tool
def get_node_type_info(class_type: str) -> dict[str, Any] | str:
    """
    Returns the input parameters, their types, and default values for a
    specific ComfyUI node class type.

    The returned dict has keys:
      - 'display_name': human-readable node name
      - 'category': node category string
      - 'description': node docstring if available
      - 'inputs': dict mapping param_name -> {'type': str, 'default': any,
                  'options': list | None, 'min': number | None, 'max': number | None}
      - 'outputs': list of output type names

    Args:
        class_type (str): The exact node class type name, e.g. 'KSampler'.

    Returns:
        dict: Node schema info, or an error string if not found.
    """
    try:
        info = _api.get_object_info(node_type=class_type)
        if not info or class_type not in info:
            return f"ERROR: Node type '{class_type}' not found in ComfyUI."
        node = info[class_type]

        all_inputs: dict[str, Any] = {}
        for section in ("required", "optional"):
            for param_name, param_def in node.get("input", {}).get(section, {}).items():
                if isinstance(param_def, (list, tuple)) and len(param_def) >= 1:
                    first = param_def[0]
                    kwargs = param_def[1] if len(param_def) > 1 else {}
                    if isinstance(first, list):
                        all_inputs[param_name] = {
                            "type": "COMBO",
                            "options": first,
                            "default": first[0] if first else None,
                            "min": None,
                            "max": None,
                        }
                    else:
                        all_inputs[param_name] = {
                            "type": str(first),
                            "options": None,
                            "default": kwargs.get("default"),
                            "min": kwargs.get("min"),
                            "max": kwargs.get("max"),
                        }

        return {
            "display_name": node.get("display_name", class_type),
            "category": node.get("category", ""),
            "description": node.get("description", ""),
            "inputs": all_inputs,
            "outputs": list(node.get("output", [])),
        }
    except ComfyApiError as e:
        return _fmt_error(e)


@mcp.tool
def list_models() -> dict[str, list[str]] | str:
    """
    Returns available models grouped by type (checkpoints, loras, vaes, etc.)
    as reported by the connected ComfyUI instance.

    The returned dict maps category name -> sorted list of model filenames.
    Categories may include: 'checkpoints', 'loras', 'vaes', 'controlnets',
    'upscale_models', 'clips', 'unets', and others depending on what is
    installed.

    Returns:
        dict: Mapping of model category -> list of available model names.
    """
    try:
        info = _api.get_object_info()
    except ComfyApiError as e:
        return _fmt_error(e)

    models: dict[str, set[str]] = {}

    for class_type, node in info.items():
        category = _MODEL_NODE_CATEGORIES.get(class_type)

        all_inputs: dict[str, Any] = {}
        for section in ("required", "optional"):
            all_inputs.update(node.get("input", {}).get(section, {}))

        for param_name, param_def in all_inputs.items():
            if not (isinstance(param_def, (list, tuple)) and len(param_def) >= 1):
                continue
            first = param_def[0]
            if not isinstance(first, list):
                continue

            model_files = [
                opt for opt in first
                if isinstance(opt, str) and Path(opt).suffix.lower() in _MODEL_EXTENSIONS
            ]
            if not model_files:
                continue

            param_category = category
            if not param_category:
                for keyword, kw_category in _PARAM_KEYWORDS:
                    if keyword in param_name.lower():
                        param_category = kw_category
                        break
            if not param_category:
                param_category = "other"

            if param_category not in models:
                models[param_category] = set()
            models[param_category].update(model_files)

    return {cat: sorted(files) for cat, files in models.items()}


@mcp.tool
def get_system_stats() -> dict[str, Any] | str:
    """
    Returns hardware resource statistics from the ComfyUI server including
    GPU VRAM usage, system RAM, and Python/ComfyUI version information.

    Returns:
        dict: System stats with keys like 'system', 'devices' (GPU info).
    """
    try:
        return _api.get_system_stats()
    except ComfyApiError as e:
        return _fmt_error(e)


@mcp.tool
def list_embeddings() -> list[str] | str:
    """
    Returns a list of available text embedding names from the ComfyUI server.

    Embeddings can be referenced in text prompts using the syntax:
    'embedding:EmbeddingName'. For example: 'masterpiece, embedding:EasyNegative'.

    Returns:
        list[str]: Sorted list of available embedding names.
    """
    try:
        result = _api.get_embeddings()
        return sorted(result) if isinstance(result, list) else result
    except ComfyApiError as e:
        return _fmt_error(e)


# ── Workflow tools ────────────────────────────────────────────────────────────

@mcp.tool
def load_workflow(file_path: str) -> dict[str, Any] | str:
    """
    Loads a ComfyUI API-format workflow from a JSON file on disk.

    The returned dict can be passed directly to other workflow tools such as
    list_nodes(), set_node_param(), and run_workflow().

    Args:
        file_path (str): Absolute or relative path to the workflow JSON file.

    Returns:
        dict: The workflow as a plain dict, or an error string on failure.
    """
    try:
        wf = ComfyWorkflowWrapper(file_path)
        return dict(wf)
    except FileNotFoundError as e:
        return _fmt_error(e)
    except json.JSONDecodeError as e:
        return _fmt_error(e)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool
def list_nodes(workflow: dict[str, Any]) -> list[dict[str, str]] | str:
    """
    Returns a list of all nodes in a workflow, each with their ID, title,
    and class type.

    Use this to discover node titles before calling set_node_param() or
    get_node_param(). Node titles are used to reference nodes in other tools.

    Args:
        workflow (dict): A ComfyUI API-format workflow dict (as returned by
                         load_workflow() or set_node_param()).

    Returns:
        list[dict]: List of dicts with keys 'id', 'title', 'class_type'.
    """
    try:
        return [
            {
                "id": node_id,
                "title": node_data.get("_meta", {}).get("title", ""),
                "class_type": node_data.get("class_type", ""),
            }
            for node_id, node_data in workflow.items()
        ]
    except Exception as e:
        return _fmt_error(e)


@mcp.tool
def set_node_param(
    workflow: dict[str, Any], node_title: str, param: str, value: Any
) -> dict[str, Any] | str:
    """
    Sets a parameter value on a node identified by its title, and returns the
    modified workflow dict.

    This tool is stateless: it accepts the full workflow dict, modifies it
    in-memory, and returns the updated copy. Chain multiple calls to build
    up the desired workflow state before running it.

    Args:
        workflow (dict): A ComfyUI API-format workflow dict.
        node_title (str): The title of the node to modify (case-sensitive),
                          as shown in list_nodes().
        param (str): The parameter/input name to set (e.g. 'text', 'seed',
                     'ckpt_name').
        value (Any): The new value. Must match the expected type for the param.

    Returns:
        dict: The updated workflow dict with the parameter changed, or an
              error string if the node title is not found.
    """
    try:
        wf = ComfyWorkflowWrapper(workflow)
        wf.set_node_param(node_title, param, value)
        return dict(wf)
    except NodeNotFoundError as e:
        return _fmt_error(e)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool
def get_node_param(workflow: dict[str, Any], node_title: str, param: str) -> Any:
    """
    Reads the current value of a parameter on a node identified by its title.

    Args:
        workflow (dict): A ComfyUI API-format workflow dict.
        node_title (str): The title of the node to read from (case-sensitive).
        param (str): The parameter/input name to read (e.g. 'text', 'steps').

    Returns:
        The current value of the parameter, or an error string if the node
        or parameter is not found.
    """
    try:
        wf = ComfyWorkflowWrapper(workflow)
        return wf.get_node_param(node_title, param)
    except NodeNotFoundError as e:
        return _fmt_error(e)
    except KeyError:
        return f"ERROR: KeyError: Parameter '{param}' not found on node '{node_title}'."
    except Exception as e:
        return _fmt_error(e)


# ── Execution tools ───────────────────────────────────────────────────────────

@mcp.tool
def upload_image(image_path: str) -> str:
    """
    Uploads a local image file to the ComfyUI server and returns a server-side
    path string suitable for use as a 'Load Image' node parameter.

    The returned string has the format 'subfolder/filename.ext' and should be
    set on a LoadImage node using:
        set_node_param(workflow, 'Load Image', 'image', <returned_value>)

    Args:
        image_path (str): Absolute path to the local image file to upload.

    Returns:
        str: Server-side image reference string (e.g. 'uploads/my_image.png'),
             or an error string on failure.
    """
    try:
        resp = _api.upload_image(image_path)
        subfolder = resp.get("subfolder", "")
        name = resp.get("name", "")
        return f"{subfolder}/{name}" if subfolder else name
    except ComfyApiError as e:
        return _fmt_error(e)
    except FileNotFoundError as e:
        return _fmt_error(e)


@mcp.tool
def run_workflow(workflow: dict[str, Any], output_node_title: str) -> list[str] | str:
    """
    Executes a ComfyUI workflow and saves the generated images to disk.

    The workflow is queued on the ComfyUI server and this tool waits
    synchronously for completion. Result images are saved to the configured
    output directory (COMFY_OUTPUT_DIR env var, default /tmp/comfy_mcp_output).

    Saved filenames use the format:
        {YYYYMMDD_HHMMSS}_{first8charsOfPromptId}_{original_filename}

    Example: '20240315_143022_a3f9c12b_ComfyUI_00001_.png'

    The workflow dict must use ComfyUI API format: top-level keys are string
    node IDs (e.g. "1", "2"), each value has "class_type", "_meta" (with
    "title"), and "inputs". Node connections are expressed as [node_id, output_index]
    lists inside inputs. You can build this dict in two ways:
      1. Load from file: load_workflow(path) -> then set_node_param() to customise
      2. Construct directly: build the dict from scratch and pass it here — no
         file or intermediate tools needed. This is the recommended approach when
         an agent creates a workflow programmatically.

    Example minimal workflow structure:
        {
          "1": {"class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"},
                "inputs": {"ckpt_name": "model.safetensors"}},
          "2": {"class_type": "CLIPTextEncode",
                "_meta": {"title": "Positive Prompt"},
                "inputs": {"text": "a cat", "clip": ["1", 1]}},
          ...
          "N": {"class_type": "SaveImage",
                "_meta": {"title": "Save Image"},
                "inputs": {"images": ["N-1", 0], "filename_prefix": "output"}}
        }

    Args:
        workflow (dict): A fully configured ComfyUI API-format workflow dict.
                         Can be built from scratch or via load_workflow() +
                         set_node_param().
        output_node_title (str): The title of the output node whose images
                                 should be retrieved (e.g. 'Save Image').

    Returns:
        list[str]: Absolute file paths to the saved images, or an error string.
    """
    try:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        wf = ComfyWorkflowWrapper(workflow)

        prompt_id, ws_images = asyncio.run(_api.queue_prompt_and_wait(wf))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{timestamp}_{prompt_id[:8]}_"
        saved_paths: list[str] = []

        if ws_images:
            for i, img_bytes in enumerate(ws_images):
                dest = _OUTPUT_DIR / f"{prefix}ws_image_{i:04d}.png"
                dest.write_bytes(img_bytes)
                saved_paths.append(str(dest))
        else:
            history = _api.get_history(prompt_id)
            node_id = wf.get_node_id(output_node_title)
            result_node = history[prompt_id]["outputs"].get(node_id, {})

            output_list = (
                result_node.get("images")
                or result_node.get("gifs")
                or result_node.get("audio")
                or []
            )

            for item in output_list:
                img_bytes = _api.get_image(
                    item["filename"], item["subfolder"], item["type"]
                )
                dest = _OUTPUT_DIR / f"{prefix}{item['filename']}"
                dest.write_bytes(img_bytes)
                saved_paths.append(str(dest))

        return saved_paths

    except ComfyApiError as e:
        return _fmt_error(e)
    except NodeNotFoundError as e:
        return _fmt_error(e)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool
def get_queue_status() -> dict[str, int] | str:
    """
    Returns the current state of the ComfyUI execution queue.

    Use this to check whether the server is busy before submitting a new
    workflow with run_workflow().

    Returns:
        dict: A dict with keys:
              - 'queue_running': number of prompts currently executing (0 or 1)
              - 'queue_pending': number of prompts waiting to run
    """
    try:
        q = _api.get_queue()
        return {
            "queue_running": len(q.get("queue_running", [])),
            "queue_pending": len(q.get("queue_pending", [])),
        }
    except ComfyApiError as e:
        return _fmt_error(e)


@mcp.tool
def interrupt_execution() -> str:
    """
    Sends an interrupt signal to the ComfyUI server to stop the currently
    running generation immediately.

    This is a non-reversible action. The interrupted workflow will not produce
    output. Use get_queue_status() first to confirm a workflow is running.

    Returns:
        str: 'OK' on success, or an error string on failure.
    """
    try:
        _api.interrupt()
        return "OK"
    except ComfyApiError as e:
        return _fmt_error(e)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the comfy-mcp-server console script."""
    logging.basicConfig(level=logging.INFO)
    _log.info(f"Starting ComfyUI MCP server, connecting to {_COMFY_URL}")
    _log.info(f"Output images will be saved to {_OUTPUT_DIR}")
    mcp.run()


if __name__ == "__main__":
    main()
