# ComfyUI GPTImage2

[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-oriented ComfyUI nodes for GPT image providers.

This extension focuses on the two core GPT image workflows: text-to-image and image-to-text. The node surface stays intentionally small while keeping configurable gateway settings, visible HTTP status feedback, and batched execution support inside a single ComfyUI node run.

## Highlights

- Custom `base_url` and `api_key` for OpenAI-compatible providers
- Only two nodes: Text2Img and Img2Text
- Minimal inputs: prompt/image plus base URL, API key, and persistence toggle
- Parallel execution for ComfyUI list/batch inputs inside one node execution
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
  "api_key": "YOUR_API_KEY"
}
```

Environment variable overrides:

- `GPTIMAGE2_BASE_URL`
- `GPTIMAGE2_API_KEY`
## Node Overview

| Node | Purpose | Model Input | Notes |
|---|---|---|---|
| `GPT_Image 文生图` | Text to image | Fixed default | Returns generated images plus status text |
| `GPT_Image 图生文` | Image to text | Fixed default | Supports image batch fan-out and returns extracted text plus status text |

## Provider Compatibility Requirements

Your provider should expose both endpoints:

- `POST /v1/images/generations`
- `POST /v1/chat/completions`

Recommended:

- OpenAI-compatible `POST /v1/images/generations`
- OpenAI-compatible vision input for `POST /v1/chat/completions`

## Troubleshooting

- `HTTP 403`: check API key permissions or provider allowlist
- `HTTP 4xx/5xx`: the node status output includes the response code and body preview
- Empty output: verify endpoint availability and model access

When opening an issue, include:

- ComfyUI version
- Full traceback
- Provider/gateway type
- Whether `/chat/completions` accepts vision image inputs

## License

MIT
