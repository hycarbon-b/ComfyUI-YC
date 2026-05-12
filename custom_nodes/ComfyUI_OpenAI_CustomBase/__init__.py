"""
ComfyUI OpenAI Custom API Plugin
Provides GPT Image generation with custom OpenAI-compatible API endpoints.
Supports configurable base URLs and API keys for private or alternative API providers.
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
