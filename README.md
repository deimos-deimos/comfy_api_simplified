# Comfy API Simplified

This is a small python wrapper over the [ComfyUI](https://github.com/comfyanonymous/ComfyUI) API. It allows you to edit API-format ComfyUI workflows and queue them programmaticaly to the already running ComfyUI.

I use it to iterate over multiple prompts and key parameters of workflow and get hundreds of images overnight to cherrypick from.

## Limitations

Only Basic auth and no auth (for local server) are supported.

## Install

```bash
pip install comfy_api_simplified          # core library
pip install comfy_api_simplified[mcp]     # + MCP server for AI agents
```

## Use prerequisits

### Prepare workflow

You would like to have your node titles unique. Usually both positive and negative prompts have title "CLIP Text Encode (Prompt)", you would like to at least give them different names in case you would like to change it's parameters from python.

### Enable "dev options"

In ComfyUI settings, check "Enable Dev mode Options":
![Alt text](misc/dev_opt.png)

### Download your workflow in API-format

<img src="misc/download.png" width="150">

### Have running ComfyUI server

## Use

```python
from comfy_api_simplified import ComfyApiWrapper, ComfyWorkflowWrapper

# create api wrapper using your ComfyUI url (add user and password params if needed)
api = ComfyApiWrapper("http://127.0.0.1:8188/")

# create workflow wrapper using your downloaded in api format workflow
wf = ComfyWorkflowWrapper("workflow_api.json")

# change anything you like in your workflow
# the syntax is "Node Title", then "Input param name", then value
wf.set_node_param("Empty Latent Image", "batch_size", 2)
wf.set_node_param("negative", "text", "embedding:EasyNegative")

# queue your workflow for completion
results = api.queue_and_wait_images(wf, "Save Image")
for filename, image_data in results.items():
    with open(f"{filename}", "wb+") as f:
        f.write(image_data)

```

More examples:

- Queue prompt and get result images [example](examples/queue_with_different_params.py).

- Queue many prompts and do not wait for completion [example](examples/queue_and_wait_result.py).

- Send input image and then call i2i workflow [example](examples/send_input_image.py).

## MCP Server (for AI agents)

The package ships an [MCP](https://modelcontextprotocol.io) server that lets AI agents (Claude, Cursor, etc.) discover nodes and models, build workflows, and run them — all via tool calls.

### Start the server

```bash
# point at your ComfyUI instance
COMFY_URL=http://192.168.1.x:8188 comfy-mcp-server

# with auth and a custom output directory
COMFY_URL=https://myserver.com COMFY_USER=user COMFY_PASSWORD=pass \
COMFY_OUTPUT_DIR=~/comfy_outputs comfy-mcp-server
```

The server uses stdio transport (compatible with Claude Desktop, Cursor, and any MCP client).

### Available tools

| Category | Tool | Description |
| -------- | ---- | ----------- |
| Discovery | `list_node_types` | All node class names available in ComfyUI |
| Discovery | `get_node_type_info` | Inputs, types, defaults for a node class |
| Discovery | `list_models` | Checkpoints, LoRAs, VAEs, etc. grouped by type |
| Discovery | `get_system_stats` | GPU VRAM, RAM, Python version |
| Discovery | `list_embeddings` | Available text embeddings |
| Workflow | `load_workflow` | Load a workflow JSON file into a dict |
| Workflow | `list_nodes` | List nodes (id, title, class_type) in a workflow |
| Workflow | `set_node_param` | Set a node parameter, returns updated workflow |
| Workflow | `get_node_param` | Read a node parameter value |
| Execution | `upload_image` | Upload a local image, returns server path |
| Execution | `run_workflow` | Run a workflow, save output images, return paths |
| Execution | `get_queue_status` | Running/pending queue counts |
| Execution | `interrupt_execution` | Stop the current generation |

Workflow tools are **stateless** — the workflow dict is passed in and returned on every call. Chain `set_node_param` calls to configure a workflow, then pass it to `run_workflow`.

### Add to Claude Desktop

```json
{
  "mcpServers": {
    "comfyui": {
      "command": "comfy-mcp-server",
      "env": { "COMFY_URL": "http://127.0.0.1:8188" }
    }
  }
}
```

## Additional info

There are some other approaches to use Python with ComfyUI out there.

If you are looking to conver your workflows to backend server code, check out [ComfyUI-to-Python-Extension](https://github.com/pydn/ComfyUI-to-Python-Extension)

If you are looking to use running ComfyUI as backend, but declare workflow in Python imperatively, check out [ComfyScript](https://github.com/Chaoses-Ib/ComfyScript/tree/main).

## Known issues

If you try to run queue_and_wait_images in async method, it may give you an error since there is already async code inside.
As a workaround, you can use

```python
import nest_asyncio
nest_asyncio.apply()
```

for now.
