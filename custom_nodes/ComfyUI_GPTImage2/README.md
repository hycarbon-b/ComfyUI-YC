# ComfyUI GPTImage2

[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-oriented ComfyUI nodes for GPT image providers.

This extension focuses on practical gateway compatibility: configurable base URL, independent model routing for generation and editing, and robust edit fallback behavior.

## Highlights

- Custom `base_url` and `api_key` for OpenAI-compatible providers
- Separate model names for Image Gen and Image Edit
- Concurrent multi-image generation support (no serial waiting)
- `Img2Img` supports multi-reference input (`image1..image5`)
- Automatic gateway fallback for edit requests when multipart is blocked
- Aspect-ratio helper node for prompt workflows

## Why Separate Gen/Edit Models?

Some gateways route `/images/generations` and `/images/edits` differently. Using the same model name for both endpoints may cause provider-side forwarding bugs. This plugin lets you set generation and edit model names independently to avoid those issues.

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

Create or edit `config.json`:

```json
{
  "base_url": "https://api.your-provider.com/v1",
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
| `GPT_Image Text2Img` | Text to image | Per-node `model` | Supports `n` for multi-image generation |
| `GPT_Image Img2Img` | Image edit / transform | Per-node `model` + config fallback | Supports `image1..image5` references |
| `GPT_比例提示词` | Prompt aspect helper | N/A | Ratio-aware prompt enhancement |

## Provider Compatibility Requirements

Your provider should expose both endpoints:

- `POST /v1/images/generations`
- `POST /v1/images/edits`

Recommended:

- Allow different model names per endpoint (Gen vs Edit)
- Proper multipart support for edit requests

If multipart edit is blocked by the gateway, plugin fallback logic can route via generation-style JSON references where available.

## Troubleshooting

- `model_price_error`: configure model pricing/routing on your provider
- `invalid_image_request`: provider may reject multipart edit payloads
- Empty output: verify API key, quota, endpoint availability, and model access

When opening an issue, include:

- ComfyUI version
- Full traceback
- Provider/gateway type
- Whether `/images/edits` accepts multipart

## Roadmap

- Support more provider-specific image endpoints
- Add Response API support
- Improve automatic gateway capability detection

PRs are welcome for new providers and endpoint integrations.

## License

MIT
