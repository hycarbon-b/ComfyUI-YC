# ComfyUI OpenAI ImageAPI

[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Production-ready ComfyUI nodes for OpenAI-compatible image providers.

## Highlights

- Text-to-image via `POST /images/generations`
- Image edit/inpaint via `POST /images/edits`
- Custom `base_url` + `api_key` support
- Model name configurable per request for both Gen and Edit
- Supports different model names for Gen/Edit to avoid gateway same-name routing bugs
- Concurrent multi-image generation/edit execution (no sequential waiting per prompt)
- Open to extension for more providers and endpoint flavors

## Why Separate Model Names for Gen/Edit?

Some gateways map generation and edit endpoints to different backend channels.
Using the same model name on both endpoints can trigger routing/forwarding bugs.
This plugin allows setting model names independently on each node call.

## Installation

### Method A: Manual

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/hycarbon-b/ComfyUI_OpenAI_ImageAPI.git
cd ComfyUI_OpenAI_ImageAPI
pip install -r requirements.txt
```

Restart ComfyUI.

### Method B: ComfyUI Manager

Install from Manager if listed, then restart ComfyUI.

## Node Path in UI

- `Add Node -> API -> OpenAI ImageAPI`

## Node Overview

| Node | Endpoint | Purpose | Concurrency |
|---|---|---|---|
| `OpenAI Image Generation` | `/images/generations` | Prompt to image | Batched prompts fire concurrently |
| `OpenAI Image Edit` | `/images/edits` | Edit/inpaint with image+prompt | Batched edit requests fire concurrently |

## Configuration

Primary runtime config is per-node input:

- `base_url`
- `api_key`
- `model`

This design makes provider and model switching explicit per workflow.

## Provider Requirements

Your provider should expose both:

- `POST /images/generations`
- `POST /images/edits`

Recommended:

- Support separate model routing for Gen/Edit
- Support multipart on edits (or provide a documented JSON alternative)

## Troubleshooting

- `model_not_found` / `model_price_error`: configure model routing and pricing provider-side
- `invalid_image_request`: provider may reject request content-type or payload format
- No images returned: verify key, quota, and model availability

## Roadmap

- Add support for more provider-specific image interfaces
- Add Response API compatibility path
- Add adaptive capability probing per provider

PRs are welcome.

## License

MIT — see [LICENSE](LICENSE).
