"""
GPTImage2 API Nodes for ComfyUI.

Supports:
  - Text-to-Image generation (via /v1/images/generations)
  - Image-to-Image (via /v1/images/edits)
"""

import asyncio
import os
import io
import json
import base64
import functools
import requests
import urllib3
import numpy as np
from PIL import Image
import torch

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def get_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    base_url = os.environ.get("GPTIMAGE2_BASE_URL", "https://api.bltcy.ai/v1")
    api_key = os.environ.get("GPTIMAGE2_API_KEY", "")
    return {"base_url": base_url, "api_key": api_key}


def get_headers():
    cfg = get_config()
    api_key = cfg.get("api_key", os.environ.get("GPTIMAGE2_API_KEY", ""))
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }


_http_session = None

def get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.verify = False
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.retry.Retry(
                total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504]
            )
        )
        _http_session.mount("https://", adapter)
        _http_session.mount("http://", adapter)
    return _http_session


# ---------------------------------------------------------------------------
# Aspect Ratio → Pixel Dimensions
# ---------------------------------------------------------------------------

ASPECT_RATIOS = {
    "1:1":    (1024, 1024),
    "4:3":    (1024, 768),
    "3:2":    (1024, 682),
    "16:9":   (1280, 720),
    "21:9":   (1680, 720),
    "2:3":    (768, 1152),
    "3:4":    (768, 1024),
    "9:16":   (768, 1365),
    "9:21":   (720, 1680),
}


def resolve_size(size: str) -> str:
    """Convert aspect ratio string to pixel dimensions for API, or pass through 'auto'."""
    if size in ASPECT_RATIOS:
        w, h = ASPECT_RATIOS[size]
        return f"{w}x{h}"
    return size  # "auto" or other


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def image_to_base64(img: Image.Image) -> str:
    return base64.b64encode(pil_to_bytes(img)).decode("utf-8")


def image_b64_to_data_url(image_b64: str, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{image_b64}"


def make_empty_mask_b64_from_image_b64(image_b64: str) -> str:
    img_bytes = base64.b64decode(image_b64)
    with Image.open(io.BytesIO(img_bytes)) as img:
        rgba = img.convert("RGBA")
        empty_mask = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    return image_to_base64(empty_mask)


def parse_error_message(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return resp.text[:500]

    error = payload.get("error")
    if isinstance(error, dict):
        return error.get("message") or json.dumps(error, ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False)


def should_send_input_fidelity(model: str, input_fidelity: str | None) -> bool:
    if not input_fidelity:
        return False
    normalized = (model or "").strip().lower()
    return not normalized.startswith("gpt-image-2")


def np_to_pil(arr: np.ndarray) -> Image.Image:
    arr = arr.clip(0, 1) if arr.max() <= 1.0 else arr
    arr = (arr * 255).astype(np.uint8)
    if arr.ndim == 3 and arr.shape[0] in (1, 3, 4):
        arr = np.transpose(arr, (1, 2, 0))
    if arr.shape[-1] == 1:
        return Image.fromarray(arr.squeeze(-1), mode="L")
    if arr.shape[-1] == 4:
        return Image.fromarray(arr, mode="RGBA")
    return Image.fromarray(arr, mode="RGB")


# ---------------------------------------------------------------------------
# API Calls

# ---------------------------------------------------------------------------
# API Calls
# ---------------------------------------------------------------------------

def call_images_generate(prompt: str, model: str = "gpt-image-2",
                          n: int = 1, quality: str = "medium",
                          size: str = "1024x1024", output_format: str = "png",
                          seed: int = -1, timeout: int | None = None) -> list[str]:
    """Call POST /v1/images/generations and return list of base64 image strings."""
    cfg = get_config()
    base_url = cfg.get("base_url", os.environ.get(
        "GPTIMAGE2_BASE_URL", "https://api.bltcy.ai/v1")).rstrip("/")

    payload = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "quality": quality,
        "size": size,
        "output_format": output_format,
        "seed": seed,
    }

    resp = get_http_session().post(
        f"{base_url}/images/generations",
        headers=get_headers(),
        json=payload,
        timeout=timeout,
    )
    print(f"[GPTImage2] Status: {resp.status_code}, Body: {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()

    images = []
    for item in data.get("data", []):
        if "b64_json" in item:
            images.append(item["b64_json"])
        elif "url" in item:
            img_resp = get_http_session().get(item["url"], timeout=timeout)
            img_resp.raise_for_status()
            images.append(base64.b64encode(img_resp.content).decode("utf-8"))
    return images


def call_images_edit(prompt: str, image_b64_list: list[str],
                     mask_b64: str | None = None,
                     model: str = "gpt-image-2",
                     n: int = 1, quality: str = "medium",
                     input_fidelity: str = "high",
                     size: str = "1024x1024", output_format: str = "png",
                     seed: int = -1, timeout: int | None = None) -> list[str]:
    """Call POST /v1/images/edits and return list of base64 image strings."""
    cfg = get_config()
    base_url = cfg.get("base_url", os.environ.get(
        "GPTIMAGE2_BASE_URL", "https://api.bltcy.ai/v1")).rstrip("/")

    if not image_b64_list:
        raise ValueError("At least one input image is required for image edits.")

    files = [
        ("prompt", (None, prompt)),
        ("model", (None, model)),
        ("n", (None, str(n))),
        ("quality", (None, quality)),
        ("size", (None, size)),
        ("output_format", (None, output_format)),
        ("seed", (None, str(seed))),
    ]

    if should_send_input_fidelity(model, input_fidelity):
        files.append(("input_fidelity", (None, input_fidelity)))

    for index, image_b64 in enumerate(image_b64_list, start=1):
        files.append((
            "image",
            (f"image{index}.png", base64.b64decode(image_b64), "image/png"),
        ))

    if mask_b64:
        files.append(("mask", ("mask.png", base64.b64decode(mask_b64), "image/png")))

    headers = {
        "Authorization": get_headers()["Authorization"],
    }

    resp = get_http_session().post(
        f"{base_url}/images/edits",
        headers=headers,
        files=files,
        timeout=timeout,
    )
    print(f"[GPTImage2] Status: {resp.status_code}, Body: {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()

    images = []
    for item in data.get("data", []):
        if "b64_json" in item:
            images.append(item["b64_json"])
        elif "url" in item:
            img_resp = get_http_session().get(item["url"], timeout=timeout)
            img_resp.raise_for_status()
            images.append(base64.b64encode(img_resp.content).decode("utf-8"))
    return images


def call_images_generate_with_refs(prompt: str, image_b64_list: list[str],
                                   mask_b64: str | None = None,
                                   model: str = "gpt-image-2",
                                   n: int = 1, quality: str = "medium",
                                   size: str = "1024x1024", output_format: str = "png",
                                   seed: int = -1, timeout: int | None = None) -> list[str]:
    """Gateway fallback: call POST /v1/images/generations with image references in JSON."""
    cfg = get_config()
    base_url = cfg.get("base_url", os.environ.get(
        "GPTIMAGE2_BASE_URL", "https://api.bltcy.ai/v1")).rstrip("/")

    if not image_b64_list:
        raise ValueError("At least one input image is required for image generation with references.")

    payload = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "quality": quality,
        "size": size,
        "output_format": output_format,
        "seed": seed,
    }

    data_urls = [image_b64_to_data_url(b64) for b64 in image_b64_list]
    if len(data_urls) == 1:
        payload["image"] = data_urls[0]
    else:
        payload["images"] = data_urls

    # For this gateway family, an explicit transparent mask improves compatibility.
    effective_mask_b64 = mask_b64 or make_empty_mask_b64_from_image_b64(image_b64_list[0])
    payload["mask"] = image_b64_to_data_url(effective_mask_b64)

    resp = get_http_session().post(
        f"{base_url}/images/generations",
        headers=get_headers(),
        json=payload,
        timeout=timeout,
    )
    print(f"[GPTImage2-fallback] Status: {resp.status_code}, Body: {resp.text[:500]}")
    resp.raise_for_status()
    data = resp.json()

    images = []
    for item in data.get("data", []):
        if "b64_json" in item:
            images.append(item["b64_json"])
        elif "url" in item:
            img_resp = get_http_session().get(item["url"], timeout=timeout)
            img_resp.raise_for_status()
            images.append(base64.b64encode(img_resp.content).decode("utf-8"))
    return images


# ---------------------------------------------------------------------------
# ComfyUI Node — Text to Image
# ---------------------------------------------------------------------------

class GPTImage2Text2Img:
    """Generate images from a text prompt using gpt-image-2."""

    CATEGORY = "🔵BB GPTIMAGE2"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "A beautiful landscape at sunset",
                    "placeholder": "Enter your prompt here...",
                }),
                "model": (["gpt-image-2", "gpt-image-1.5", "gpt-image-1"], {
                    "default": "gpt-image-2",
                }),
                "quality": (["low", "medium", "high", "auto"], {
                    "default": "medium",
                }),
                "size": (["1:1", "4:3", "3:2", "16:9", "21:9", "2:3", "3:4", "9:16", "9:21", "auto"], {
                    "default": "auto",
                }),
                "n": ("INT", {
                    "default": 1, "min": 1, "max": 10, "step": 1,
                }),
                "seed": ("INT", {
                    "default": -1, "min": -1, "max": 2147483647, "step": 1,
                }),
            },
            "optional": {
                "output_format": (["png", "jpeg", "webp"], {
                    "default": "png",
                }),
            }
        }

    async def generate(self, prompt, model, quality, size, n, seed, output_format="png"):
        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(
            None,
            functools.partial(
                call_images_generate,
                prompt=prompt,
                model=model,
                n=n,
                quality=quality,
                size=resolve_size(size),
                seed=seed,
                output_format=output_format,
            ),
        )

        tensors = []
        for b64 in images:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None]
            tensors.append(tensor)

        if not tensors:
            raise ValueError("No images were returned from the API.")
        return (torch.cat(tensors, dim=0),)


# ---------------------------------------------------------------------------
# ComfyUI Node — Image to Image
# ---------------------------------------------------------------------------

class GPTImage2Img2Img:
    """Transform an input image using gpt-image-2 with text guidance."""

    CATEGORY = "🔵BB GPTIMAGE2"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "transform"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image1": ("IMAGE",),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "Transform this image into a painting",
                    "placeholder": "Describe how to transform the image...",
                }),
                "model": (["gpt-image-2", "gpt-image-1.5", "gpt-image-1"], {
                    "default": "gpt-image-2",
                }),
                "input_fidelity": (["low", "high"], {
                    "default": "high",
                }),
                "quality": (["low", "medium", "high", "auto"], {
                    "default": "medium",
                }),
                "size": (["1:1", "4:3", "3:2", "16:9", "21:9", "2:3", "3:4", "9:16", "9:21", "auto"], {
                    "default": "auto",
                }),
                "n": ("INT", {
                    "default": 1, "min": 1, "max": 10, "step": 1,
                }),
                "seed": ("INT", {
                    "default": -1, "min": -1, "max": 2147483647, "step": 1,
                }),
            },
            "optional": {
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "output_format": (["png", "jpeg", "webp"], {
                    "default": "png",
                }),
            }
        }

    async def transform(self, image1, prompt, model, input_fidelity,
                        quality, size, n, seed, output_format="png",
                        image2=None, image3=None, image4=None, image5=None):
        all_images = [image1, image2, image3, image4, image5]
        valid_images = []
        for img in all_images:
            if img is not None:
                img_tensor = img[0] if img.ndim == 4 else img
                if img_tensor.shape[-1] in (1, 3, 4):
                    img_tensor = img_tensor[..., :3]
                pil_img = np_to_pil(img_tensor.cpu().numpy())
                valid_images.append(pil_img)

        if not valid_images:
            raise ValueError("At least one image input is required.")
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        image_b64_list = [image_to_base64(img) for img in valid_images]

        loop = asyncio.get_event_loop()
        images = await loop.run_in_executor(
            None,
            functools.partial(
                call_images_edit,
                prompt=prompt,
                image_b64_list=image_b64_list,
                model=model,
                n=n,
                input_fidelity=input_fidelity,
                quality=quality,
                size=resolve_size(size),
                seed=seed,
                output_format=output_format,
            ),
        )

        tensors = []
        for b64 in images:
            img_bytes = base64.b64decode(b64)
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensor = torch.from_numpy(arr)[None]
            tensors.append(tensor)

        if not tensors:
            raise ValueError("No images were returned from the API.")
        return (torch.cat(tensors, dim=0),)


# ---------------------------------------------------------------------------
# GPTImageNode — compatible with test_gpt_image_plugin.json workflow
# ---------------------------------------------------------------------------

class GPTImageNode:
    """GPT-Image node compatible with the GPTImageNode class_type workflow."""

    CATEGORY = "🔵BB GPTIMAGE2"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "A beautiful landscape",
                }),
                "model": (["gpt-image-2", "gpt-image-1.5", "gpt-image-1"], {
                    "default": "gpt-image-2",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "placeholder": "Leave empty to use config.json",
                }),
                "quality": (["low", "medium", "high", "auto"], {
                    "default": "high",
                }),
                "size": (["1024x1024", "1536x1024", "1024x1536", "auto"], {
                    "default": "1024x1024",
                }),
                "background": (["auto", "opaque", "transparent"], {
                    "default": "auto",
                }),
                "output_format": (["png", "jpeg", "webp"], {
                    "default": "png",
                }),
                "output_compression": ("INT", {
                    "default": 100, "min": 0, "max": 100, "step": 1,
                }),
                "n_images": ("INT", {
                    "default": 1, "min": 1, "max": 10, "step": 1,
                }),
            },
        }

    async def generate(self, prompt, model, api_key, quality, size, background,
                       output_format, output_compression, n_images):
        cfg = get_config()
        base_url = cfg.get("base_url", os.environ.get(
            "GPTIMAGE2_BASE_URL", "https://api.bltcy.ai/v1")).rstrip("/")

        # Use provided api_key if given, else fall back to config
        key = api_key.strip() if api_key and api_key.strip() and api_key.strip() != "OPENAI_API_KEY" else cfg.get("api_key", "")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "n": n_images,
            "quality": quality,
            "size": size,
            "output_format": output_format,
        }
        if background != "auto":
            payload["background"] = background

        def _do_request():
            resp = get_http_session().post(
                f"{base_url}/images/generations",
                headers=headers,
                json=payload,
                timeout=None,
            )
            print(f"[GPTImageNode] Status: {resp.status_code}, Body: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, _do_request)

        tensors = []
        for item in data.get("data", []):
            if "b64_json" in item:
                b64 = item["b64_json"]
            elif "url" in item:
                img_resp = await loop.run_in_executor(
                    None, functools.partial(get_http_session().get, item["url"], timeout=None)
                )
                img_resp.raise_for_status()
                b64 = base64.b64encode(img_resp.content).decode("utf-8")
            else:
                continue
            img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            tensors.append(torch.from_numpy(arr)[None])

        if not tensors:
            raise ValueError("No images returned from the API.")
        return (torch.cat(tensors, dim=0),)


# ---------------------------------------------------------------------------
# Node Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "GPTImage2_Text2Img": GPTImage2Text2Img,
    "GPTImage2_Img2Img": GPTImage2Img2Img,
    "GPTImageNode": GPTImageNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage2_Text2Img": "GPT_Image 文生图",
    "GPTImage2_Img2Img": "GPT_Image 图生图",
    "GPTImageNode": "GPT_Image",
}
