# Changelog

所有对此项目的重要更改都将记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
并遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [1.0.0] - 2026-05-08

### Added
- 初始版本发布
- `OpenAIGPTImageCustom` 节点：支持自定义 API 端点和认证的 GPT Image 生成
- 支持文本生成图像 (text-to-image) 模式
- 支持图像编辑 (image-to-image) 和修复 (inpainting) 模式
- 支持三个 GPT Image 模型：gpt-image-1, gpt-image-1.5, gpt-image-2
- 8 种不同的输出尺寸选项
- 批量图像生成（支持生成 1-8 张图像）
- 配置化的 base URL 和 API 密钥
- 默认配置指向 api.laozhang.ai
- 完整的文档和快速开始指南
- 示例工作流文件
- 价格计算支持

### Features
- ✅ 自定义 OpenAI 兼容 API 端点支持
- ✅ 灵活的认证机制（Bearer Token）
- ✅ 图像批处理和缩放
- ✅ 异步 API 调用
- ✅ 自动重试机制
- ✅ 详细的输入验证
- ✅ 支持参考图像和修复掩码

### Documentation
- README.md - 项目说明和功能介绍
- QUICKSTART.md - 快速开始指南
- TECHNICAL.md - 技术文档和扩展指南
- 示例工作流 (example_workflow.json)
- LICENSE (MIT)

### Supported APIs
- OpenAI 官方 API (api.openai.com)
- Azure OpenAI
- 阿里云 DashScope
- api.laozhang.ai（默认）
- 任何兼容的自建 API 服务

## 计划中的功能

### [未来版本]
- [ ] 支持更多 OpenAI 端点（Chat API, Embeddings 等）
- [ ] 缓存支持（加快重复请求）
- [ ] 高级配置 UI
- [ ] 本地模型支持
- [ ] WebUI 中的实时预览
- [ ] 更详细的错误日志
- [ ] 性能监控和统计

---

## 升级指南

### 从 v0.x 升级到 v1.0.0
此版本是首个稳定版本，无升级需求。

---

## 已知问题

### v1.0.0
- 某些 API 提供商可能不支持所有尺寸选项
- 透明背景仅在 gpt-image-2 中不被支持
- 掩码修复仅支持单张图像

---

## 提交历史

详见 [GitHub 提交日志](https://github.com/yourusername/ComfyUI_OpenAI_CustomBase/commits/main)

---

**最后更新**: 2026-05-08
