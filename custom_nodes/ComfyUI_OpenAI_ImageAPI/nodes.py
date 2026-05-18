"""
ComfyUI OpenAI Image API Nodes
Two focused nodes:
  - OpenAIImageGeneration  →  POST /images/generations
  - OpenAIImageEdit        →  POST /images/edits
Both support custom base-URL and API key so they work with any
OpenAI-compatible proxy / gateway.

Concurrency model
-----------------
* Each blocking HTTP call runs in a thread-pool executor so it never
  blocks the asyncio event loop.
* When n > 1, the Generation node fans out into n parallel single-image
  requests so each image starts generating immediately.
* URL-based image downloads inside a response are fetched concurrently
  with asyncio.gather.
* Image tensor decoding (CPU-bound) is also offloaded to the executor.
"""
import asyncio
import base64
from io import BytesIO
from typing import Any

import numpy as np
import requests as _requests
import torch
from PIL import Image

from comfy_api.latest import IO, Input
from comfy_api_nodes.util import downscale_image_tensor, validate_string

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_PIXELS = 2048 * 2048  # largest safe size before API rejects the upload

# One shared session reuses TCP connections across concurrent requests.
_session = _requests.Session()
_session.trust_env = False  # ignore system proxy env vars


def _pil_to_png_bytes(pil_img: Image.Image) -> bytes:
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _tensor_to_pil(t: torch.Tensor) -> Image.Image:
    """(1,H,W,C) or (H,W,C) float32 [0,1] → PIL RGBA"""
    if t.ndim == 4:
        t = t.squeeze(0)
    arr = (t.cpu().numpy() * 255).astype(np.uint8)
    if arr.shape[-1] == 4:
        return Image.fromarray(arr, mode="RGBA")
    return Image.fromarray(arr).convert("RGBA")


def _bytes_to_tensor(img_bytes: bytes) -> torch.Tensor:
    """Decode raw PNG/JPEG bytes → float32 (H,W,4) tensor."""
    pil_img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    arr = np.asarray(pil_img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)


async def _fetch_url(url: str) -> bytes:
    """Download a URL asynchronously (runs in executor to avoid blocking)."""
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None, lambda: _session.get(url, timeout=120)
    )
    resp.raise_for_status()
    return resp.content


async def _decode_response_images(data: dict) -> torch.Tensor:
    """
    Parse an OpenAI images response dict.
    URL-based images are downloaded concurrently; decoding runs in the executor.
    Returns a (N, H, W, 4) float32 tensor.
    """
    items = data.get("data", [])
    if not items:
        raise ValueError("No images returned from API")

    loop = asyncio.get_running_loop()

    async def _item_to_bytes(item: dict[str, Any]) -> bytes:
        if item.get("b64_json"):
            # CPU-bound decode → executor
            return await loop.run_in_executor(
                None, base64.b64decode, item["b64_json"]
            )
        if item.get("url"):
            return await _fetch_url(item["url"])
        raise ValueError(f"Unsupported image payload: {item!r}")

    # Fetch / decode all images concurrently
    all_bytes: list[bytes] = await asyncio.gather(*[_item_to_bytes(i) for i in items])

    # Decode bytes → tensors concurrently in the executor
    tensors: list[torch.Tensor] = await asyncio.gather(
        *[loop.run_in_executor(None, _bytes_to_tensor, b) for b in all_bytes]
    )

    return torch.stack(tensors, dim=0)


# ---------------------------------------------------------------------------
# Node 1: Image Generation  (POST /images/generations)
# ---------------------------------------------------------------------------

class OpenAIImageGeneration(IO.ComfyNode):
    """
    Generate images via any OpenAI-compatible /images/generations endpoint.
    Works with OpenAI, Azure OpenAI, LaoZhang, and other compatible proxies.

    Concurrency: INPUT_IS_LIST=True tells ComfyUI to collect all batched prompt
    values and pass them together in a single execute() call.  Every prompt then
    fires its own HTTP request concurrently via asyncio.gather – no request waits
    for another to finish.
    """

    # Pass all batched inputs as lists in one call so we can fire every
    # HTTP request concurrently instead of sequentially.
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="OpenAIImageGeneration",
            display_name="OpenAI Image Generation",
            category="API/OpenAI ImageAPI",
            description=(
                "Generate images via OpenAI-compatible /images/generations API. "
                "Supports gpt-image-*, dall-e-3, dall-e-2 and compatible models."
            ),
            inputs=[
                IO.String.Input(
                    "prompt",
                    default="A serene mountain lake at sunset",
                    multiline=True,
                    tooltip="Text prompt describing the image to generate.",
                ),
                IO.String.Input(
                    "base_url",
                    default="https://api.openai.com/v1",
                    tooltip="OpenAI-compatible API base URL (no trailing slash).",
                ),
                IO.String.Input(
                    "api_key",
                    default="sk-...",
                    tooltip="API key / bearer token for the endpoint.",
                ),
                IO.Combo.Input(
                    "model",
                    options=[
                        "gpt-image-1",
                        "gpt-image-1.5",
                        "gpt-image-2",
                        "dall-e-3",
                        "dall-e-2",
                    ],
                    default="gpt-image-1",
                    tooltip="Model to use for generation.",
                    optional=True,
                ),
                IO.Combo.Input(
                    "size",
                    options=[
                        "auto",
                        "256x256",
                        "512x512",
                        "1024x1024",
                        "1024x1536",
                        "1536x1024",
                        "1792x1024",
                        "1024x1792",
                    ],
                    default="1024x1024",
                    tooltip="Output image dimensions.",
                    optional=True,
                ),
                IO.Combo.Input(
                    "quality",
                    options=["auto", "low", "medium", "high", "standard", "hd"],
                    default="auto",
                    tooltip="Image quality (model-dependent).",
                    optional=True,
                ),
                IO.Combo.Input(
                    "style",
                    options=["vivid", "natural"],
                    default="vivid",
                    tooltip="Style hint – only used by dall-e-3.",
                    optional=True,
                ),
                IO.Combo.Input(
                    "background",
                    options=["auto", "opaque", "transparent"],
                    default="auto",
                    tooltip="Background transparency (gpt-image-* only).",
                    optional=True,
                ),
                IO.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=2**31 - 1,
                    step=1,
                    display_mode=IO.NumberDisplay.number,
                    control_after_generate=True,
                    tooltip="Seed for reproducibility (if supported by the endpoint).",
                    optional=True,
                ),
            ],
            outputs=[
                IO.Image.Output(tooltip="Generated image(s) as RGBA tensor (N,H,W,4)."),
            ],
            hidden=[IO.Hidden.unique_id],
            is_api_node=True,
        )

    @classmethod
    async def execute(
        cls,
        prompt: list[str],
        base_url: list[str],
        api_key: list[str],
        model: list[str] | None = None,
        size: list[str] | None = None,
        quality: list[str] | None = None,
        style: list[str] | None = None,
        background: list[str] | None = None,
        seed: list[int] | None = None,
    ) -> IO.NodeOutput:
        # With INPUT_IS_LIST=True every param arrives as a list.
        # Non-batched params (e.g. api_key set once) will be a 1-element list;
        # use the last element as a fallback for shorter lists.
        def _get(lst: list | None, i: int, default):
            if not lst:
                return default
            return lst[i] if i < len(lst) else lst[-1]

        loop = asyncio.get_running_loop()

        async def _one_request(i: int) -> torch.Tensor:
            p    = _get(prompt,     i, "")
            url  = _get(base_url,   i, "https://api.openai.com/v1").strip().rstrip("/")
            key  = _get(api_key,    i, "").strip()
            mdl  = _get(model,      i, "gpt-image-1")
            sz   = _get(size,       i, "1024x1024")
            qual = _get(quality,    i, "auto")
            styl = _get(style,      i, "vivid")
            bg   = _get(background, i, "auto")
            sd   = _get(seed,       i, 0)

            validate_string(p,   strip_whitespace=False)
            validate_string(url, strip_whitespace=True, min_length=1)
            validate_string(key, strip_whitespace=True, min_length=1)

            payload: dict = {"model": mdl, "prompt": p, "n": 1}
            if sz   != "auto":     payload["size"]       = sz
            if qual != "auto":     payload["quality"]    = qual
            if bg   != "auto":     payload["background"] = bg
            if mdl  == "dall-e-3": payload["style"]      = styl
            if sd   != 0:          payload["seed"]       = sd

            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            }

            def _post():
                resp = _session.post(
                    f"{url}/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=None,
                )
                print(
                    f"[OpenAIImageGen] POST {url}/images/generations "
                    f"prompt_idx={i} → status={resp.status_code} "
                    f"body_preview={resp.text[:300]}"
                )
                resp.raise_for_status()
                return resp.json()

            data = await loop.run_in_executor(None, _post)
            return await _decode_response_images(data)

        # Fire all prompts concurrently – no prompt waits for another.
        tensors: list[torch.Tensor] = await asyncio.gather(
            *[_one_request(i) for i in range(len(prompt))]
        )
        return IO.NodeOutput(torch.cat(tensors, dim=0))


# ---------------------------------------------------------------------------
# Node 2: Image Edit  (POST /images/edits)
# ---------------------------------------------------------------------------

class OpenAIImageEdit(IO.ComfyNode):
    """
    Edit / inpaint images via any OpenAI-compatible /images/edits endpoint.
    Provide one or more source images and an optional mask; the API fills in
    the masked region (or re-renders the whole image) according to the prompt.

    Concurrency: INPUT_IS_LIST=True means all batched (image, prompt) pairs are
    delivered to a single execute() call so every edit request is fired
    concurrently via asyncio.gather.
    """

    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)

    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="OpenAIImageEdit",
            display_name="OpenAI Image Edit",
            category="API/OpenAI ImageAPI",
            description=(
                "Edit images via OpenAI-compatible /images/edits API. "
                "Supports inpainting with an optional mask, multi-image input, "
                "and custom base URL / API key."
            ),
            inputs=[
                IO.Image.Input(
                    "image",
                    tooltip=(
                        "Source image(s) to edit. "
                        "Batch of N images is passed as image[] to the API."
                    ),
                ),
                IO.String.Input(
                    "prompt",
                    default="",
                    multiline=True,
                    tooltip="Description of the desired edit.",
                ),
                IO.String.Input(
                    "base_url",
                    default="https://api.openai.com/v1",
                    tooltip="OpenAI-compatible API base URL (no trailing slash).",
                ),
                IO.String.Input(
                    "api_key",
                    default="sk-...",
                    tooltip="API key / bearer token for the endpoint.",
                ),
                IO.Mask.Input(
                    "mask",
                    tooltip=(
                        "Optional inpaint mask. White areas are edited; "
                        "black areas are preserved. Only valid with a single image."
                    ),
                    optional=True,
                ),
                IO.Combo.Input(
                    "model",
                    options=[
                        "gpt-image-1",
                        "gpt-image-1.5",
                        "gpt-image-2",
                        "dall-e-2",
                    ],
                    default="gpt-image-1",
                    optional=True,
                ),
                IO.Combo.Input(
                    "size",
                    options=[
                        "auto",
                        "256x256",
                        "512x512",
                        "1024x1024",
                        "1024x1536",
                        "1536x1024",
                    ],
                    default="auto",
                    tooltip="Output image dimensions.",
                    optional=True,
                ),
                IO.Combo.Input(
                    "quality",
                    options=["auto", "low", "medium", "high", "standard"],
                    default="auto",
                    tooltip="Image quality.",
                    optional=True,
                ),
                IO.Combo.Input(
                    "background",
                    options=["auto", "opaque", "transparent"],
                    default="auto",
                    tooltip="Background transparency (gpt-image-* only).",
                    optional=True,
                ),
                IO.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=2**31 - 1,
                    step=1,
                    display_mode=IO.NumberDisplay.number,
                    control_after_generate=True,
                    tooltip="Seed for reproducibility (if supported by the endpoint).",
                    optional=True,
                ),
            ],
            outputs=[
                IO.Image.Output(tooltip="Edited image(s) as RGBA tensor (N,H,W,4)."),
            ],
            hidden=[IO.Hidden.unique_id],
            is_api_node=True,
        )

    @classmethod
    async def execute(
        cls,
        image: list[Input.Image],
        prompt: list[str],
        base_url: list[str],
        api_key: list[str],
        mask: list[Input.Image | None] | None = None,
        model: list[str] | None = None,
        size: list[str] | None = None,
        quality: list[str] | None = None,
        background: list[str] | None = None,
        seed: list[int] | None = None,
    ) -> IO.NodeOutput:
        def _get(lst: list | None, i: int, default):
            if not lst:
                return default
            return lst[i] if i < len(lst) else lst[-1]

        loop = asyncio.get_running_loop()

        async def _encode_one_image(img: Input.Image, idx: int, is_single: bool) -> tuple:
            field = "image" if is_single else "image[]"
            def _enc():
                single = img[idx : idx + 1] if img.ndim == 4 else img.unsqueeze(0)
                scaled = downscale_image_tensor(single, total_pixels=_MAX_PIXELS).squeeze()
                return _pil_to_png_bytes(_tensor_to_pil(scaled))
            img_bytes = await loop.run_in_executor(None, _enc)
            return (field, (f"image_{idx}.png", img_bytes, "image/png"))

        async def _one_request(i: int) -> torch.Tensor:
            img  = _get(image,      i, None)
            p    = _get(prompt,     i, "")
            url  = _get(base_url,   i, "https://api.openai.com/v1").strip().rstrip("/")
            key  = _get(api_key,    i, "").strip()
            msk  = _get(mask,       i, None)
            mdl  = _get(model,      i, "gpt-image-1")
            sz   = _get(size,       i, "auto")
            qual = _get(quality,    i, "auto")
            bg   = _get(background, i, "auto")
            sd   = _get(seed,       i, 0)

            validate_string(p,   strip_whitespace=False)
            validate_string(url, strip_whitespace=True, min_length=1)
            validate_string(key, strip_whitespace=True, min_length=1)

            if img is None:
                raise ValueError(f"No image supplied for request {i}")
            if msk is not None and img.shape[0] != 1:
                raise ValueError(f"Mask is only supported with a single image (request {i}).")

            # Encode source image frames concurrently
            n_frames = img.shape[0]
            image_parts: list[tuple] = list(
                await asyncio.gather(*[
                    _encode_one_image(img, f, is_single=(n_frames == 1))
                    for f in range(n_frames)
                ])
            )

            # Encode mask if provided
            mask_part: tuple | None = None
            if msk is not None:
                def _enc_mask():
                    _, h, w = msk.shape
                    rgba_mask = torch.zeros(h, w, 4, device="cpu")
                    rgba_mask[:, :, 3] = 1.0 - msk.squeeze().cpu()
                    scaled_mask = downscale_image_tensor(
                        rgba_mask.unsqueeze(0), total_pixels=_MAX_PIXELS
                    ).squeeze()
                    return _pil_to_png_bytes(_tensor_to_pil(scaled_mask))
                mask_bytes = await loop.run_in_executor(None, _enc_mask)
                mask_part = ("mask", ("mask.png", mask_bytes, "image/png"))

            files = image_parts.copy()
            if mask_part:
                files.append(mask_part)
            files += [
                ("prompt", (None, p)),
                ("model",  (None, mdl)),
                ("n",      (None, "1")),
            ]
            if sz   != "auto": files.append(("size",       (None, sz)))
            if qual != "auto": files.append(("quality",    (None, qual)))
            if bg   != "auto": files.append(("background", (None, bg)))
            if sd   != 0:      files.append(("seed",       (None, str(sd))))

            headers = {"Authorization": f"Bearer {key}"}

            def _post():
                resp = _session.post(
                    f"{url}/images/edits",
                    headers=headers,
                    files=files,
                    timeout=None,
                )
                print(
                    f"[OpenAIImageEdit] POST {url}/images/edits "
                    f"request_idx={i} → status={resp.status_code} "
                    f"body_preview={resp.text[:300]}"
                )
                resp.raise_for_status()
                return resp.json()

            data = await loop.run_in_executor(None, _post)
            return await _decode_response_images(data)

        # Fire all edit requests concurrently – no request waits for another.
        tensors: list[torch.Tensor] = await asyncio.gather(
            *[_one_request(i) for i in range(len(prompt))]
        )
        return IO.NodeOutput(torch.cat(tensors, dim=0))


# ---------------------------------------------------------------------------
# ComfyUI node registry
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "OpenAIImageGeneration": OpenAIImageGeneration,
    "OpenAIImageEdit": OpenAIImageEdit,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenAIImageGeneration": "OpenAI Image Generation",
    "OpenAIImageEdit": "OpenAI Image Edit",
}
