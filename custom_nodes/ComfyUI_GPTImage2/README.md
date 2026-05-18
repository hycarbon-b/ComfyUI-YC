# ComfyUI GPTImage2

[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-oriented ComfyUI nodes for GPT image providers.

This extension focuses on practical gateway compatibility: configurable base URL, persistent credential settings, visible HTTP status feedback, and parallel task execution wrapped inside a single ComfyUI node run.

## Highlights

- Custom `base_url` and `api_key` for OpenAI-compatible providers
- Only two nodes: Text2Img and Img2Img
- Parallel execution for prompt lists, split-line prompts, and image batches inside one node execution
- Visible request status output such as `SENT`, `HTTP 200`, and `HTTP 403`
- Output node previews all generated images directly in ComfyUI

## Installation

### Method A: Existing ComfyUI (recommended)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/hycarbon-b/ComfyUI-YC.git
cd ComfyUI-YC/custom_nodes/ComfyUI_GPTImage2
pip install -r requirements.txt
```

Restart ComfyUI after installation.

### Method B: Copy Folder

1. Copy this directory to `ComfyUI/custom_nodes/ComfyUI_GPTImage2`
2. Run `pip install -r requirements.txt` in that directory
3. Restart ComfyUI

## Quick Configuration

Create or edit the persisted config file at `user/__gptimage2/config.json`.

Legacy `custom_nodes/ComfyUI_GPTImage2/config.json` will be migrated automatically on first load.

Example:

```json
{
  "base_url": "https://gw-stg.tradingbase.ai/v1",
  "api_key": "YOUR_API_KEY",
  "edit_model": "gpt-image-2-edit"
}
```

Environment variable overrides:

- `GPTIMAGE2_BASE_URL`
- `GPTIMAGE2_API_KEY`
- `GPTIMAGE2_EDIT_MODEL`

## Node Overview

| Node | Purpose | Model Input | Notes |
|---|---|---|---|
| `GPT_Image 文生图` | Text to image | Per-node `model` | Can split prompt lines into parallel tasks and returns an extra status text output |
| `GPT_Image 图生图` | Image edit / transform | Per-node `model` | Supports `image1..image5`, image batch fan-out, prompt splitting, and parallel requests |

## Provider Compatibility Requirements

Your provider should expose both endpoints:

- `POST /v1/images/generations`
- `POST /v1/images/edits`

Recommended:

- Proper multipart support for edit requests
- OpenAI-compatible `POST /v1/images/generations`
- OpenAI-compatible `POST /v1/images/edits`

## Troubleshooting

- `HTTP 403`: check API key permissions or provider allowlist
- `HTTP 4xx/5xx`: the node status output includes the response code and body preview
- Empty output: verify endpoint availability and model access

When opening an issue, include:

- ComfyUI version
- Full traceback
- Provider/gateway type
- Whether `/images/edits` accepts multipart

## License

MIT
