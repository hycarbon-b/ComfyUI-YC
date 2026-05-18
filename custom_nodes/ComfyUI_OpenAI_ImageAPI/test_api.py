"""
Quick smoke-test for the OpenAI Image API nodes.
Run from the repo root:
    python custom_nodes/ComfyUI_OpenAI_ImageAPI/test_api.py

Saves output PNGs next to this script.
"""
import asyncio
import base64
import os
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

BASE_URL = os.environ.get("OPENAI_IMAGE_API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("OPENAI_IMAGE_API_KEY", "")
HERE     = Path(__file__).parent

session = requests.Session()
session.trust_env = False
HEADERS_JSON = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_response_images(data: dict, prefix: str):
    saved = []
    for idx, item in enumerate(data.get("data", [])):
        if item.get("b64_json"):
            img_bytes = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            r = session.get(item["url"], timeout=60)
            r.raise_for_status()
            img_bytes = r.content
        else:
            print(f"  [!] item {idx}: no b64_json or url, skipping")
            continue
        path = HERE / f"{prefix}_{idx}.png"
        Image.open(BytesIO(img_bytes)).save(path)
        saved.append(path)
        print(f"  saved → {path}")
    return saved


# ---------------------------------------------------------------------------
# Test 1: /images/generations  (3 prompts concurrently)
# ---------------------------------------------------------------------------

async def test_generation():
    print("\n=== Test: /images/generations (3 concurrent prompts) ===")

    prompts = [
        "A serene mountain lake at sunset, photorealistic",
        "A futuristic city skyline at night, neon lights",
        "A cozy coffee shop interior, warm lighting, watercolor style",
    ]

    async def _one(i: int, prompt: str):
        payload = {
            "model": "gpt-image-2",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "low",
        }
        loop = asyncio.get_running_loop()

        def _post():
            resp = session.post(
                f"{BASE_URL}/images/generations",
                headers=HEADERS_JSON,
                json=payload,
                timeout=None,
            )
            print(f"  [{i}] status={resp.status_code}  prompt='{prompt[:40]}…'")
            resp.raise_for_status()
            return resp.json()

        data = await loop.run_in_executor(None, _post)
        save_response_images(data, f"gen_{i}")

    # Fire all three at the same time
    await asyncio.gather(*[_one(i, p) for i, p in enumerate(prompts)])
    print("Generation test PASSED")


# ---------------------------------------------------------------------------
# Test 2: /images/edits  (edit with a solid-color reference image)
# ---------------------------------------------------------------------------

async def test_edit():
    print("\n=== Test: /images/edits ===")

    # Create a simple 512x512 blue reference image in memory
    ref_img = Image.new("RGBA", (512, 512), (70, 130, 180, 255))
    buf = BytesIO()
    ref_img.save(buf, format="PNG")
    ref_bytes = buf.getvalue()

    files = [
        ("image",  ("reference.png", ref_bytes, "image/png")),
        ("prompt", (None, "Turn the blue background into a starry night sky")),
        ("model",  (None, "gpt-image-2")),
        ("n",      (None, "1")),
        ("size",   (None, "1024x1024")),
        ("quality",(None, "low")),
    ]
    headers = {"Authorization": f"Bearer {API_KEY}"}

    loop = asyncio.get_running_loop()

    def _post():
        resp = session.post(
            f"{BASE_URL}/images/edits",
            headers=headers,
            files=files,
            timeout=None,
        )
        print(f"  status={resp.status_code}")
        if resp.status_code >= 400:
            print(f"  body={resp.text[:600]}")
        resp.raise_for_status()
        return resp.json()

    data = await loop.run_in_executor(None, _post)
    save_response_images(data, "edit_0")
    print("Edit test PASSED")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    if not API_KEY:
        print(
            "Set OPENAI_IMAGE_API_KEY before running tests. "
            "Optional: OPENAI_IMAGE_API_BASE_URL",
            file=sys.stderr,
        )
        return

    try:
        await test_generation()
    except Exception as e:
        print(f"Generation test FAILED: {e}", file=sys.stderr)

    try:
        await test_edit()
    except Exception as e:
        print(f"Edit test FAILED: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
