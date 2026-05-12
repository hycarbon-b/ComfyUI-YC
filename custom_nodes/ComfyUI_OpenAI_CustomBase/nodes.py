"""
ComfyUI Custom OpenAI Node with Customizable Base URL and API Key
Provides GPT Image generation with custom OpenAI-compatible API endpoints
"""
import base64
from io import BytesIO
from urllib.parse import urljoin

import numpy as np
import torch
from PIL import Image

from comfy_api.latest import IO, Input
from comfy_api_nodes.apis.openai import (
    OpenAIImageEditRequest,
    OpenAIImageGenerationRequest,
    OpenAIImageGenerationResponse,
)
from comfy_api_nodes.util import (
    ApiEndpoint,
    downscale_image_tensor,
    sync_op,
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

        if model in ("gpt-image-1", "gpt-image-1.5"):
            if size not in ("auto", "1024x1024", "1024x1536", "1536x1024"):
                raise ValueError(f"Resolution {size} is only supported by GPT Image 2 model")

        if model == "gpt-image-1":
            price_extractor = calculate_tokens_price_image_1
        elif model == "gpt-image-1.5":
            price_extractor = calculate_tokens_price_image_1_5
        elif model == "gpt-image-2":
            price_extractor = calculate_tokens_price_image_2_0
            if background == "transparent":
                raise ValueError("Transparent background is not supported for GPT Image 2 model")
        else:
            raise ValueError(f"Unknown model: {model}")

        # Normalize base URL and prepare headers
        normalized_base_url = base_url.strip().rstrip("/") + "/"
        headers: dict[str, str] = {
            "Authorization": f"Bearer {api_key.strip()}",
        }

        if image is not None:
            # Image editing mode
            files = []
            batch_size = image.shape[0]
            for i in range(batch_size):
                single_image = image[i : i + 1]
                scaled_image = downscale_image_tensor(single_image, total_pixels=2048 * 2048).squeeze()

                image_np = (scaled_image.numpy() * 255).astype(np.uint8)
                img = Image.fromarray(image_np)
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format="PNG")
                img_byte_arr.seek(0)

                if batch_size == 1:
                    files.append(("image", (f"image_{i}.png", img_byte_arr, "image/png")))
                else:
                    files.append(("image[]", (f"image_{i}.png", img_byte_arr, "image/png")))

            if mask is not None:
                if image.shape[0] != 1:
                    raise Exception("Cannot use a mask with multiple images")
                if mask.shape[1:] != image.shape[1:-1]:
                    raise Exception("Mask and Image must be the same size")
                _, height, width = mask.shape
                rgba_mask = torch.zeros(height, width, 4, device="cpu")
                rgba_mask[:, :, 3] = 1 - mask.squeeze().cpu()

                scaled_mask = downscale_image_tensor(rgba_mask.unsqueeze(0), total_pixels=2048 * 2048).squeeze()

                mask_np = (scaled_mask.numpy() * 255).astype(np.uint8)
                mask_img = Image.fromarray(mask_np)
                mask_img_byte_arr = BytesIO()
                mask_img.save(mask_img_byte_arr, format="PNG")
                mask_img_byte_arr.seek(0)
                files.append(("mask", ("mask.png", mask_img_byte_arr, "image/png")))

            response = await sync_op(
                cls,
                ApiEndpoint(
                    path=urljoin(normalized_base_url, "images/edits"),
                    method="POST",
                    headers=headers,
                ),
                response_model=OpenAIImageGenerationResponse,
                data=OpenAIImageEditRequest(
                    model=model,
                    prompt=prompt,
                    quality=quality,
                    background=background,
                    n=n,
                    seed=seed,
                    size=size,
                    moderation="low",
                ),
                content_type="multipart/form-data",
                files=files,
                price_extractor=price_extractor,
            )
        else:
            # Text-to-image mode
            response = await sync_op(
                cls,
                ApiEndpoint(
                    path=urljoin(normalized_base_url, "images/generations"),
                    method="POST",
                    headers=headers,
                ),
                response_model=OpenAIImageGenerationResponse,
                data=OpenAIImageGenerationRequest(
                    model=model,
                    prompt=prompt,
                    quality=quality,
                    background=background,
                    n=n,
                    seed=seed,
                    size=size,
                    moderation="low",
                ),
                price_extractor=price_extractor,
            )
        return IO.NodeOutput(await validate_and_cast_response(response))


# Node mapping for ComfyUI
NODE_CLASS_MAPPINGS = {
    "OpenAIGPTImageCustom": OpenAIGPTImageCustom,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenAIGPTImageCustom": "OpenAI GPT Image (Custom API)",
}
