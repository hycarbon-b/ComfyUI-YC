"""
Prompt Enhancement Nodes for ComfyUI.

Provides:
  - Aspect ratio prompt enhancer: takes raw text, prepends ratio-aware
    photography/imagery descriptor, and appends the chosen aspect ratio.
"""

from typing import Tuple

ASPECT_RATIOS = {
    "21:9":  "图像比例21:9",
    "16:9":  "图像比例16:9",
    "4:3":   "图像比例4:3",
    "3:2":   "图像比例3:2",
    "1:1":   "图像比例1:1",
    "2:3":   "图像比例2:3",
    "3:4":   "图像比例3:4",
    "9:16":  "图像比例9:16",
    "9:21":  "图像比例9:21",
}

ASPECT_RATIO_OPTIONS = list(ASPECT_RATIOS.keys())


class AspectRatioPrompt:
    """
    Takes a raw text prompt and injects ratio-aware photography modifiers.

    Input:  raw_prompt   e.g. "a photo of a cat"
    Output: enhanced_prompt  e.g. "a photo of a cat, 16:9 wide-angle landscape, cinematic composition"

    Usage in workflow:
        [Any text node] → [AspectRatioPrompt] → [GPT_T2文生图 prompt]
    """

    CATEGORY = "🔵BB GPTIMAGE2"
    RETURN_TYPES = ("STRING",)
    FUNCTION = "enhance"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "raw_prompt": ("STRING", {
                    "multiline": True,
                    "default": "a photo of a cat",
                    "placeholder": "Enter your base prompt...",
                }),
                "aspect_ratio": (ASPECT_RATIO_OPTIONS, {
                    "default": "16:9",
                }),
                "enhance_mode": (["append", "prepend", "both"], {
                    "default": "append",
                }),
            },
            "optional": {
                "custom_prefix": ("STRING", {
                    "default": "",
                    "placeholder": "Custom prefix override (optional)",
                }),
                "custom_suffix": ("STRING", {
                    "default": "",
                    "placeholder": "Custom suffix override (optional)",
                }),
            }
        }

    def enhance(
        self,
        raw_prompt: str,
        aspect_ratio: str,
        enhance_mode: str,
        custom_prefix: str = "",
        custom_suffix: str = "",
    ) -> Tuple[str]:
        if not raw_prompt or not raw_prompt.strip():
            raise ValueError("raw_prompt cannot be empty.")

        ratio_text = ASPECT_RATIOS.get(aspect_ratio, aspect_ratio)

        if custom_prefix:
            prefix = custom_prefix
        else:
            if enhance_mode in ("prepend", "both"):
                prefix = ratio_text + ", "
            else:
                prefix = ""

        if custom_suffix:
            suffix = ", " + custom_suffix
        else:
            if enhance_mode in ("append", "both"):
                suffix = ", " + ratio_text
            else:
                suffix = ""

        enhanced = f"{prefix}{raw_prompt.strip()}{suffix}"
        return (enhanced,)


# ---------------------------------------------------------------------------
# Node Mappings
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "GPTImage2_AspectRatioPrompt": AspectRatioPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage2_AspectRatioPrompt": "🔵BB GPT_比例提示词",
}
