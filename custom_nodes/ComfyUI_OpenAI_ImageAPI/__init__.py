"""
ComfyUI OpenAI Image API Plugin
Provides two nodes:
  - OpenAI Image Generation  →  /images/generations
  - OpenAI Image Edit        →  /images/edits
Both nodes accept a custom base URL and API key so they work with
OpenAI, Azure OpenAI, and any OpenAI-compatible proxy or gateway.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
