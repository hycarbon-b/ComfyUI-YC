# ComfyUI GPTImage2

Community-ready ComfyUI nodes for GPT Image APIs.

This plugin provides:
- Text-to-image generation (`/v1/images/generations`)
- Image-to-image editing (`/v1/images/edits`)
- Gateway-compatible fallback for edit flows when multipart is blocked

## Features

- OpenAI-compatible API support (base URL + API key)
- Multi-image references for image editing
- Editable model name for image edit (default: `gpt-image-2-edit`)
- Optional fallback from `/images/edits` to `/images/generations` for restricted gateways
- Aspect-ratio presets with automatic size conversion

## Installation

### Option 1: Manual install

1. Copy this folder into `ComfyUI/custom_nodes/ComfyUI_GPTImage2`
2. Install dependencies:

```bash
cd ComfyUI/custom_nodes/ComfyUI_GPTImage2
pip install -r requirements.txt
```

3. Configure API settings in `config.json`
4. Restart ComfyUI

### Option 2: Git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/hycarbon-b/ComfyUI-YC.git
cd ComfyUI-YC/custom_nodes/ComfyUI_GPTImage2
pip install -r requirements.txt
```

Then restart ComfyUI.

## Configuration

Edit `config.json`:

```json
{
  "base_url": "https://api.bltcy.ai/v1",
  "api_key": "YOUR_API_KEY",
  "edit_model": "gpt-image-2-edit"
}
```

Environment variables are also supported:
- `GPTIMAGE2_BASE_URL`
- `GPTIMAGE2_API_KEY`
- `GPTIMAGE2_EDIT_MODEL`

## Nodes

### GPT_Image Text2Img

Generate image(s) from a prompt.

Key inputs:
- `prompt`
- `model` (`gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`)
- `quality` (`low`, `medium`, `high`, `auto`)
- `size` (ratio presets + `auto`)
- `n`, `seed`, `output_format`

### GPT_Image Img2Img

Edit an input image with prompt guidance.

Key inputs:
- `image1` (required), optional `image2..image5`
- `prompt` (required)
- `model` (free text, default `gpt-image-2-edit`)
- `input_fidelity`, `quality`, `size`, `n`, `seed`, `output_format`

Notes:
- Reference images are uploaded individually (no local sprite stitching).
- For `gpt-image-2*` models, `input_fidelity` is omitted automatically.

## Gateway Compatibility

Some API gateways block `multipart/form-data` for `/images/edits`.

This plugin detects that failure path and can fallback to JSON references through `/images/generations`, including an automatic transparent mask for better compatibility.

## Installation Support

If installation fails, check in this order:

1. **Python environment**: install dependencies inside the same Python used by ComfyUI
2. **Node loading**: confirm `ComfyUI_GPTImage2` is under `ComfyUI/custom_nodes`
3. **API config**: verify `base_url` and `api_key` are valid
4. **Model access**: ensure your gateway account has model routing and pricing configured

If you still need help, open an issue with:
- ComfyUI version
- Full node error traceback
- Your gateway type (OpenAI direct / proxy / one-api style)
- Whether `/images/edits` accepts multipart

## Known Issues

- If your gateway returns pricing errors (for example `model_price_error`), configure model pricing on the gateway first.
- If only JSON is accepted for edit endpoint but backend expects multipart, this is a gateway-side misconfiguration.

## License

MIT
