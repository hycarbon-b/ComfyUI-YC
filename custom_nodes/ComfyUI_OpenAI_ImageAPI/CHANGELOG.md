# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] – 2026-05-18

### Added
- `OpenAIImageGeneration` node – text-to-image via `/images/generations`
- `OpenAIImageEdit` node – image editing / inpainting via `/images/edits`
- Custom base URL and API key inputs on every node
- Support for `gpt-image-1`, `gpt-image-1.5`, `gpt-image-2`, `dall-e-3`, `dall-e-2`
- Batch image input for the Edit node (`image[]` multipart upload)
- Automatic RGBA mask conversion matching the OpenAI API convention
- Image downscaling to 2048×2048 max before upload
