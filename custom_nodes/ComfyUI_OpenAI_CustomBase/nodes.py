"""
ComfyUI Custom OpenAI Node with Customizable Base URL and API Key
Provides GPT Image generation with custom OpenAI-compatible API endpoints
"""
import asyncio
import base64
import functools
from io import BytesIO
from urllib.parse import urljoin

import numpy as np
import requests as _requests
import torch
from PIL import Image

from comfy_api.latest import IO, Input
from comfy_api_nodes.util import (
    downscale_image_tensor,
    validate_string,
)


def calculate_tokens_price_image_1(response: OpenAIImageGenerationResponse) -> float | None:
    """Calculate price for gpt-image-1 model"""
    return ((response.usage.input_tokens * 10.0) + (response.usage.output_tokens * 40.0)) / 1_000_000.0


def calculate_tokens_price_image_1_5(response: OpenAIImageGenerationResponse) -> float | None:
    """Calculate price for gpt-image-1.5 model"""
    return ((response.usage.input_tokens * 8.0) + (response.usage.output_tokens * 32.0)) / 1_000_000.0


def calculate_tokens_price_image_2_0(response: OpenAIImageGenerationResponse) -> float | None:
    """Calculate price for gpt-image-2 model"""
    return ((response.usage.input_tokens * 8.0) + (response.usage.output_tokens * 30.0)) / 1_000_000.0


async def validate_and_cast_response(response, timeout: int = None) -> torch.Tensor:
    """Validates and casts a response to a torch.Tensor.

    Args:
        response: The response to validate and cast.
        timeout: Request timeout in seconds. Defaults to None (no timeout).

    Returns:
        A torch.Tensor representing the image (1, H, W, C).

    Raises:
        ValueError: If the response is not valid.
    """
    from comfy_api_nodes.util import download_url_to_bytesio

    # validate raw JSON response
    data = response.data
    if not data or len(data) == 0:
        raise ValueError("No images returned from API endpoint")

    # Initialize list to store image tensors
    image_tensors: list[torch.Tensor] = []

    # Process each image in the data array
    for img_data in data:
        if img_data.b64_json:
            img_io = BytesIO(base64.b64decode(img_data.b64_json))
        elif img_data.url:
            img_io = BytesIO()
            await download_url_to_bytesio(img_data.url, img_io, timeout=timeout)
        else:
            raise ValueError("Invalid image payload – neither URL nor base64 data present.")

        pil_img = Image.open(img_io).convert("RGBA")
        arr = np.asarray(pil_img).astype(np.float32) / 255.0
        image_tensors.append(torch.from_numpy(arr))

    return torch.stack(image_tensors, dim=0)


class OpenAIGPTImageCustom(IO.ComfyNode):
    """
    Custom OpenAI GPT Image node with configurable API endpoint and authentication.
    Supports OpenAI-compatible APIs like custom API gateways.
    """

    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="OpenAIGPTImageCustom",
            display_name="OpenAI GPT Image (Custom API)",
            category="api node/image/OpenAI",
            description="Generates images via OpenAI-compatible GPT Image endpoint with custom base URL and API key.",
            inputs=[
                IO.String.Input(
                    "prompt",
                    default="",
                    multiline=True,
                    tooltip="Text prompt for GPT Image",
                ),
                IO.String.Input(
                    "base_url",
                    default="https://api.laozhang.ai/v1",
                    tooltip="OpenAI-compatible API base URL",
                ),
                IO.String.Input(
                    "api_key",
                    default="sk-doKcKuvmFoM7RAARaNO1Uyda4e6mJUGt0CIW3Y8B4oC5Xtlx",
                    tooltip="API key for authentication",
                ),
                IO.Int.Input(
                    "seed",
                    default=0,
                    min=0,
                    max=2**31 - 1,
                    step=1,
                    display_mode=IO.NumberDisplay.number,
                    control_after_generate=True,
                    optional=True,
                ),
                IO.Combo.Input(
                    "quality",
                    default="low",
                    options=["low", "medium", "high"],
                    tooltip="Image quality",
                    optional=True,
                ),
                IO.Combo.Input(
                    "background",
                    default="auto",
                    options=["auto", "opaque", "transparent"],
                    tooltip="Background mode",
                    optional=True,
                ),
                IO.Combo.Input(
                    "size",
                    default="auto",
                    options=[
                        "auto",
                        "1024x1024",
                        "1024x1536",
                        "1536x1024",
                        "2048x2048",
                        "2048x1152",
                        "1152x2048",
                        "3840x2160",
                        "2160x3840",
                    ],
                    tooltip="Image size",
                    optional=True,
                ),
                IO.Int.Input(
                    "n",
                    default=1,
                    min=1,
                    max=8,
                    step=1,
                    tooltip="Number of images to generate",
                    display_mode=IO.NumberDisplay.number,
                    optional=True,
                ),
                IO.Image.Input(
                    "image",
                    tooltip="Optional reference image for image editing",
                    optional=True,
                ),
                IO.Mask.Input(
                    "mask",
                    tooltip="Optional mask for inpainting",
                    optional=True,
                ),
                IO.Combo.Input(
                    "model",
                    options=["gpt-image-1", "gpt-image-1.5", "gpt-image-2"],
                    default="gpt-image-2",
                    optional=True,
                ),
            ],
            outputs=[
                IO.Image.Output(),
            ],
            hidden=[
                IO.Hidden.unique_id,
            ],
            is_api_node=True,
        )

    @classmethod
    async def execute(
        cls,
        prompt: str,
        base_url: str = "https://api.laozhang.ai/v1",
        api_key: str = "sk-doKcKuvmFoM7RAARaNO1Uyda4e6mJUGt0CIW3Y8B4oC5Xtlx",
        seed: int = 0,
        quality: str = "low",
        background: str = "opaque",
        image: Input.Image | None = None,
        mask: Input.Image | None = None,
        n: int = 1,
        size: str = "1024x1024",
        model: str = "gpt-image-2",
    ) -> IO.NodeOutput:
        validate_string(prompt, strip_whitespace=False)
        validate_string(base_url, strip_whitespace=True, min_length=1)
        validate_string(api_key, strip_whitespace=True, min_length=1)

        if mask is not None and image is None:
            raise ValueError("Cannot use a mask without an input image")

        normalized_base_url = base_url.strip().rstrip("/")
        headers = {"Authorization": f"Bearer {api_key.strip()}"}

        if image is not None:
            # Build multipart files list
            files = []
            batch_size = image.shape[0]
            for i in range(batch_size):
                single_image = image[i : i + 1]
                scaled_image = downscale_image_tensor(single_image, total_pixels=2048 * 2048).squeeze()
                image_np = (scaled_image.numpy() * 255).astype(np.uint8)
                img_buf = BytesIO()
                Image.fromarray(image_np).save(img_buf, format="PNG")
                field = "image" if batch_size == 1 else "image[]"
                files.append((field, (f"image_{i}.png", img_buf.getvalue(), "image/png")))

            if mask is not None:
                if image.shape[0] != 1:
                    raise ValueError("Cannot use a mask with multiple images")
                _, height, width = mask.shape
                rgba_mask = torch.zeros(height, width, 4, device="cpu")
                rgba_mask[:, :, 3] = 1 - mask.squeeze().cpu()
                scaled_mask = downscale_image_tensor(rgba_mask.unsqueeze(0), total_pixels=2048 * 2048).squeeze()
                mask_np = (scaled_mask.numpy() * 255).astype(np.uint8)
                mask_buf = BytesIO()
                Image.fromarray(mask_np).save(mask_buf, format="PNG")
                files.append(("mask", ("mask.png", mask_buf.getvalue(), "image/png")))

            # Append text fields
            files += [
                ("prompt", (None, prompt)),
                ("model",  (None, model)),
                ("n",      (None, str(n))),
                ("quality",(None, quality)),
                ("size",   (None, size)),
                ("seed",   (None, str(seed))),
            ]
            if background != "auto":
                files.append(("background", (None, background)))

            def _do_edit():
                resp = _requests.post(
                    f"{normalized_base_url}/images/edits",
                    headers=headers,
                    files=files,
                    timeout=None,
                    proxies={},  # bypass system proxy
                )
                print(f"[OpenAICustom] edits status={resp.status_code} body={resp.text[:300]}")
                resp.raise_for_status()
                return resp.json()

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _do_edit)
        else:
            payload = {
                "model": model, "prompt": prompt, "n": n,
                "quality": quality, "size": size, "seed": seed,
            }
            if background != "auto":
                payload["background"] = background

            def _do_gen():
                resp = _requests.post(
                    f"{normalized_base_url}/images/generations",
                    headers={**headers, "Content-Type": "application/json"},
                    json=payload,
                    timeout=None,
                    proxies={},  # bypass system proxy
                )
                print(f"[OpenAICustom] gen status={resp.status_code} body={resp.text[:300]}")
                resp.raise_for_status()
                return resp.json()

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _do_gen)

        # Decode response images into tensors
        tensors = []
        for item in data.get("data", []):
            if item.get("b64_json"):
                img_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                r = await loop.run_in_executor(
                    None,
                    functools.partial(_requests.get, item["url"], timeout=None, proxies={}),
                )
                r.raise_for_status()
                img_bytes = r.content
            else:
                continue
            pil_img = Image.open(BytesIO(img_bytes)).convert("RGBA")
            arr = np.asarray(pil_img).astype(np.float32) / 255.0
            tensors.append(torch.from_numpy(arr))

        if not tensors:
            raise ValueError("No images returned from API")
        return IO.NodeOutput(torch.stack(tensors, dim=0))


# Node mapping for ComfyUI
NODE_CLASS_MAPPINGS = {
    "OpenAIGPTImageCustom": OpenAIGPTImageCustom,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenAIGPTImageCustom": "OpenAI GPT Image (Custom API)",
}
