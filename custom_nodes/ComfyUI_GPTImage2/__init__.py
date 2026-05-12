"""
ComfyUI Custom Node: GPTImage2 API Integration
Provides text-to-image, image-to-image, and image editing nodes using gpt-image-2.
"""
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .prompt_nodes import NODE_CLASS_MAPPINGS as _PROMPT_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _PROMPT_NAMES

NODE_CLASS_MAPPINGS = {**NODE_CLASS_MAPPINGS, **_PROMPT_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**NODE_DISPLAY_NAME_MAPPINGS, **_PROMPT_NAMES}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
