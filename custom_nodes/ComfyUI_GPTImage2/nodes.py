"""GPT image nodes for ComfyUI."""

import asyncio
import base64
import functools
import io
import json
import os
import threading
import uuid

import numpy as np
from PIL import Image
import requests
import torch
import urllib3

import comfy.utils
import folder_paths
import nodes as comfy_nodes

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PLUGIN_CATEGORY = "YC/GPT Image"
DEFAULT_BASE_URL = "https://gw-stg.tradingbase.ai/v1"
DEFAULT_GENERATE_MODEL = "gpt-image-2"
DEFAULT_VISION_MODEL = "gpt-4o-mini"
LEGACY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CONFIG_FILE_NAME = "config.json"
CONFIG_DIRECTORY_NAME = "gptimage2"
CONFIG_KEYS = ("base_url", "api_key")
API_KEY_ALIASES = ("api_key", "api_k")
CONFIG_LOCK = threading.Lock()


class RequestStatusError(ValueError):
    def __init__(self, status_lines: list[str]):
        super().__init__("\n".join(status_lines))
        self.status_lines = status_lines


def _clean_string(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_base_url(value: str) -> str:
    cleaned = _clean_string(value)
    return cleaned.rstrip("/") if cleaned else ""


def _truncate_text(value: str, limit: int = 240) -> str:
    text = _clean_string(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _read_json_file(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def _write_json_file(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def get_config_path() -> str:
    config_dir = folder_paths.get_system_user_directory(CONFIG_DIRECTORY_NAME)
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, CONFIG_FILE_NAME)


def _default_config() -> dict:
    return {
        "base_url": _normalize_base_url(os.environ.get("GPTIMAGE2_BASE_URL")) or DEFAULT_BASE_URL,
        "api_key": _clean_string(os.environ.get("GPTIMAGE2_API_KEY")),
    }


def _read_config_file() -> dict:
    if os.path.exists(LEGACY_CONFIG_PATH):
        return _read_json_file(LEGACY_CONFIG_PATH)
    return _read_json_file(get_config_path())


def _resolve_api_key(stored: dict) -> str:
    for key in API_KEY_ALIASES:
        value = _clean_string(stored.get(key))
        if value:
            return value
    return ""


def _merge_config(stored: dict) -> dict:
    config = _default_config()
    base_url = _normalize_base_url(stored.get("base_url"))
    if base_url:
        config["base_url"] = base_url
    api_key = _resolve_api_key(stored)
    if api_key or any(key in stored for key in API_KEY_ALIASES):
        config["api_key"] = api_key
    return config


def _ensure_config_migrated() -> str:
    if os.path.exists(LEGACY_CONFIG_PATH):
        return LEGACY_CONFIG_PATH
    config_path = get_config_path()
    if os.path.exists(config_path):
        return config_path
    legacy_config = _read_json_file(LEGACY_CONFIG_PATH)
    if legacy_config:
        _write_json_file(config_path, _merge_config(legacy_config))
    return config_path


def get_config() -> dict:
    return _merge_config(_read_config_file())


def save_config(updates: dict) -> dict:
    config_path = _ensure_config_migrated()
    with CONFIG_LOCK:
        stored = _read_json_file(config_path)
        next_config = dict(stored)
        if "base_url" in updates:
            value = _normalize_base_url(updates["base_url"])
            if value:
                next_config["base_url"] = value
        if "api_key" in updates:
            value = _clean_string(updates["api_key"])
            if "api_k" in next_config and "api_key" not in next_config:
                next_config["api_k"] = value
            else:
                next_config["api_key"] = value
        _write_json_file(config_path, next_config)
    return _merge_config(next_config)


def build_request_settings(base_url: str = "", api_key: str = "", persist_settings: bool = False) -> tuple[str, str]:
    config = get_config()
    resolved_base_url = _normalize_base_url(base_url) or config.get("base_url", DEFAULT_BASE_URL)

    provided_api_key = _clean_string(api_key)
    if provided_api_key == "OPENAI_API_KEY":
        provided_api_key = ""
    resolved_api_key = provided_api_key or config.get("api_key", "")

    if persist_settings:
        updates = {}
        if _normalize_base_url(base_url) and resolved_base_url != config.get("base_url", DEFAULT_BASE_URL):
            updates["base_url"] = resolved_base_url
        if provided_api_key and provided_api_key != config.get("api_key", ""):
            updates["api_key"] = provided_api_key
        if updates:
            save_config(updates)

    return resolved_base_url, resolved_api_key


def build_headers(api_key: str, with_content_type: bool = True) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    if with_content_type:
        headers["Content-Type"] = "application/json"
    return headers


_http_session = None


def get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.trust_env = False
        _http_session.verify = False
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.retry.Retry(
                total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504]
            )
        )
        _http_session.mount("https://", adapter)
        _http_session.mount("http://", adapter)
    return _http_session


def pil_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format=fmt)
    return buffer.getvalue()


def image_to_base64(img: Image.Image) -> str:
    return base64.b64encode(pil_to_bytes(img)).decode("utf-8")


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


def _pick_list_value(values, index: int):
    if not isinstance(values, list):
        return values
    if not values:
        return None
    return values[index if index < len(values) else -1]


def _max_list_length(*values) -> int:
    lengths = [len(value) for value in values if isinstance(value, list)]
    return max(lengths, default=1)


def _b64_to_tensor(image_b64: str) -> torch.Tensor:
    img_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    arr = np.array(image).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None]


def _flatten_image_batches(image_inputs: list[torch.Tensor | None]) -> list[list[str]]:
    max_batch = 1
    normalized_inputs = []
    for image in image_inputs:
        if image is None:
            normalized_inputs.append(None)
            continue
        normalized_inputs.append(image)
        if image.ndim == 4:
            max_batch = max(max_batch, image.shape[0])

    jobs = []
    for batch_index in range(max_batch):
        job_images = []
        for image in normalized_inputs:
            if image is None:
                continue
            if image.ndim == 4:
                if image.shape[0] not in (1, max_batch):
                    raise ValueError("Batched image inputs must all share the same batch size, or be a single image.")
                image_tensor = image[batch_index if image.shape[0] > 1 else 0]
            else:
                image_tensor = image
            if image_tensor.shape[-1] in (1, 3, 4):
                image_tensor = image_tensor[..., :3]
            job_images.append(image_to_base64(np_to_pil(image_tensor.cpu().numpy())))
        if job_images:
            jobs.append(job_images)
    return jobs


def _request_with_status(method: str, url: str, *, headers: dict, json_payload=None, files=None, timeout: int | None = None) -> tuple[requests.Response, list[str]]:
    status_lines = [f"SENT {method} {url}"]
    try:
        response = get_http_session().request(
            method=method,
            url=url,
            headers=headers,
            json=json_payload,
            files=files,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        status_lines.append(f"FAILED {method} {url} -> {exc.__class__.__name__}: {exc}")
        raise RequestStatusError(status_lines) from exc

    body_preview = _truncate_text(response.text or "<empty>")
    status_lines.append(f"HTTP {response.status_code} {response.reason}: {body_preview}")
    if not response.ok:
        raise RequestStatusError(status_lines)
    return response, status_lines


def _download_image_as_b64(url: str, timeout: int | None = None) -> tuple[str, list[str]]:
    response, status_lines = _request_with_status("GET", url, headers={}, timeout=timeout)
    return base64.b64encode(response.content).decode("utf-8"), status_lines


def extract_response_images(data: dict, timeout: int | None = None) -> tuple[list[str], list[str]]:
    images = []
    download_statuses = []
    for item in data.get("data", []):
        if "b64_json" in item:
            images.append(item["b64_json"])
        elif "url" in item:
            image_b64, status_lines = _download_image_as_b64(item["url"], timeout=timeout)
            images.append(image_b64)
            download_statuses.extend(status_lines)
    return images, download_statuses


def extract_response_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    content = (choices[0].get("message") or {}).get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part.strip() for part in parts if part.strip())
    return str(content).strip()


def _save_preview_images(images: torch.Tensor, prefix: str) -> list[dict]:
    preview_node = comfy_nodes.PreviewImage()
    preview_node.prefix_append = f"_{prefix}_{uuid.uuid4().hex[:8]}"
    ui_payload = preview_node.save_images(images)
    return ui_payload.get("ui", {}).get("images", [])


def _format_status_text(status_lines: list[str]) -> str:
    return "\n".join(status_lines)


def _build_result_payload(image_groups: list[dict], status_lines: list[str], preview_prefix: str) -> dict:
    tensors = []
    for group in image_groups:
        for image_b64 in group["images"]:
            tensors.append(_b64_to_tensor(image_b64))
    if not tensors:
        raise ValueError("No images were returned from the API.")

    image_tensor = torch.cat(tensors, dim=0)
    status_text = _format_status_text(status_lines)
    return {
        "ui": {
            "images": _save_preview_images(image_tensor, preview_prefix),
            "text": (status_text,),
        },
        "result": (image_tensor, status_text),
    }


def call_images_generate(
    prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    persist_settings: bool,
    timeout: int | None = None,
) -> dict:
    resolved_base_url, resolved_api_key = build_request_settings(base_url, api_key, persist_settings)
    response, status_lines = _request_with_status(
        "POST",
        f"{resolved_base_url}/images/generations",
        headers=build_headers(resolved_api_key),
        json_payload={
            "model": model,
            "prompt": prompt,
        },
        timeout=timeout,
    )
    images, download_statuses = extract_response_images(response.json(), timeout=timeout)
    status_lines.extend(download_statuses)
    status_lines.append(f"RECEIVED {len(images)} image(s)")
    return {"images": images, "status_lines": status_lines}


def call_images_edit(
    prompt: str,
    image_b64: str,
    model: str,
    base_url: str,
    api_key: str,
    persist_settings: bool,
    timeout: int | None = None,
) -> dict:
    resolved_base_url, resolved_api_key = build_request_settings(base_url, api_key, persist_settings)
    if not image_b64:
        raise ValueError("An input image is required for image-to-image edit.")
    if not prompt:
        raise ValueError("A prompt (edit instruction) is required.")

    edit_model = model if model.endswith("-edit") else f"{model}-edit"
    image_bytes = base64.b64decode(image_b64)
    
    files = {
        "image": ("image.png", image_bytes, "image/png"),
        "prompt": (None, prompt),
        "model": (None, edit_model),
    }
    headers = {"Authorization": f"Bearer {resolved_api_key}"}
    
    status_lines = [f"SENT POST {resolved_base_url}/images/edits"]
    try:
        response = requests.post(
            f"{resolved_base_url}/images/edits",
            headers=headers,
            files=files,
            timeout=timeout,
            verify=False,
        )
    except requests.RequestException as exc:
        status_lines.append(f"FAILED POST -> {exc.__class__.__name__}: {exc}")
        raise RequestStatusError(status_lines) from exc

    body_preview = _truncate_text(response.text or "<empty>")
    status_lines.append(f"HTTP {response.status_code} {response.reason}: {body_preview}")
    if not response.ok:
        raise RequestStatusError(status_lines)

    images, download_statuses = extract_response_images(response.json(), timeout=timeout)
    status_lines.extend(download_statuses)
    status_lines.append(f"RECEIVED {len(images)} edited image(s)")
    return {"images": images, "status_lines": status_lines}


async def _run_parallel_jobs(callables: list[functools.partial], unique_id: str | None) -> tuple[list[dict], list[str]]:
    loop = asyncio.get_running_loop()
    progress = comfy.utils.ProgressBar(len(callables), node_id=unique_id)

    async def run_one(index: int, func: functools.partial):
        result = await loop.run_in_executor(None, func)
        return index, result

    tasks = [asyncio.create_task(run_one(index, func)) for index, func in enumerate(callables)]
    results = [None] * len(callables)
    errors = []
    completed = 0

    for task in asyncio.as_completed(tasks):
        try:
            index, result = await task
            results[index] = result
        except RequestStatusError as exc:
            errors.extend(exc.status_lines)
        except Exception as exc:
            errors.append(str(exc))
        completed += 1
        progress.update_absolute(completed, len(callables))

    if errors:
        raise ValueError("\n".join(errors))

    status_lines = []
    ordered_results = []
    for index, result in enumerate(results, start=1):
        ordered_results.append(result)
        status_lines.append(f"TASK {index}")
        status_lines.extend(result["status_lines"])
    return ordered_results, status_lines


class GPTImage2Text2Img:
    CATEGORY = PLUGIN_CATEGORY
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    FUNCTION = "generate"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        config = get_config()
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "A beautiful landscape at sunset",
                    "placeholder": "Enter your prompt here...",
                }),
                "base_url": ("STRING", {
                    "default": config.get("base_url", DEFAULT_BASE_URL),
                    "placeholder": "OpenAI-compatible base URL",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "placeholder": "Leave empty to use saved API key",
                }),
                "persist_settings": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    async def generate(self, prompt, base_url, api_key, persist_settings, unique_id):
        task_count = _max_list_length(prompt, base_url, api_key, persist_settings)
        callables = []

        for index in range(task_count):
            prompt_value = _clean_string(_pick_list_value(prompt, index))
            if not prompt_value:
                raise ValueError("Prompt cannot be empty.")
            callables.append(functools.partial(
                call_images_generate,
                prompt=prompt_value,
                model=DEFAULT_GENERATE_MODEL,
                base_url=_pick_list_value(base_url, index),
                api_key=_pick_list_value(api_key, index),
                persist_settings=bool(_pick_list_value(persist_settings, index)),
            ))

        image_groups, status_lines = await _run_parallel_jobs(callables, _pick_list_value(unique_id, 0))
        return _build_result_payload(image_groups, status_lines, "gptimage2_text2img")


class GPTImage2Img2Img:
    CATEGORY = PLUGIN_CATEGORY
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    FUNCTION = "edit"
    OUTPUT_NODE = True
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        config = get_config()
        return {
            "required": {
                "image1": ("IMAGE",),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "Apply artistic style and enhance colors",
                    "placeholder": "Describe how to edit the image...",
                }),
                "base_url": ("STRING", {
                    "default": config.get("base_url", DEFAULT_BASE_URL),
                    "placeholder": "OpenAI-compatible base URL",
                }),
                "api_key": ("STRING", {
                    "default": "",
                    "placeholder": "Leave empty to use saved API key",
                }),
                "persist_settings": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    async def edit(
        self,
        image1,
        prompt,
        base_url,
        api_key,
        persist_settings,
        unique_id,
    ):
        config = get_config()
        edit_model = config.get("edit_model", DEFAULT_GENERATE_MODEL)

        task_count = _max_list_length(
            image1,
            prompt,
            base_url,
            api_key,
            persist_settings,
        )

        callables = []
        for index in range(task_count):
            prompt_value = _clean_string(_pick_list_value(prompt, index))
            if not prompt_value:
                raise ValueError("Prompt (edit instruction) cannot be empty.")

            selected_images = [_pick_list_value(image1, index)]
            image_jobs = _flatten_image_batches(selected_images)
            if not image_jobs:
                raise ValueError("At least one image input is required.")

            for image_b64_list in image_jobs:
                if len(image_b64_list) != 1:
                    raise ValueError("Image-to-image edit accepts exactly one image per task.")
                callables.append(functools.partial(
                    call_images_edit,
                    prompt=prompt_value,
                    image_b64=image_b64_list[0],
                    model=edit_model,
                    base_url=_pick_list_value(base_url, index),
                    api_key=_pick_list_value(api_key, index),
                    persist_settings=bool(_pick_list_value(persist_settings, index)),
                ))

        image_groups, status_lines = await _run_parallel_jobs(callables, _pick_list_value(unique_id, 0))
        return _build_result_payload(image_groups, status_lines, "gptimage2_img2img")


NODE_CLASS_MAPPINGS = {
    "GPTImage2_Text2Img": GPTImage2Text2Img,
    "GPTImage2_Img2Img": GPTImage2Img2Img,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage2_Text2Img": "GPT_Image 文生图",
    "GPTImage2_Img2Img": "GPT_Image 图生图",
}
