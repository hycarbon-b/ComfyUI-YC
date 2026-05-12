# ComfyUI OpenAI Custom API Plugin

为 ComfyUI 提供支持自定义 API 端点和认证的 OpenAI GPT Image 节点。

## 功能

- **自定义 API 端点支持**: 支持使用私有或第三方 OpenAI 兼容 API 提供商
- **灵活的认证**: 每个节点可以配置不同的 API 密钥
- **完整的图像生成**: 支持文本生成图像、图像编辑等功能
- **预配置默认值**: 开箱即用，默认配置为 `https://api.laozhang.ai/v1/`

## 安装

### 自动安装
1. 将此文件夹复制到 `ComfyUI/custom_nodes/` 目录
2. 重启 ComfyUI

### 手动安装
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yourusername/ComfyUI_OpenAI_CustomBase.git
cd ComfyUI_OpenAI_CustomBase
pip install -r requirements.txt
```

## 节点说明

### OpenAI GPT Image (Custom API)

为 OpenAI GPT Image 模型生成图像，支持自定义 API 端点和认证。

#### 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| prompt | 字符串 | — | 图像生成的文本描述 |
| base_url | 字符串 | https://api.laozhang.ai/v1 | API 基础 URL |
| api_key | 字符串 | sk-yrUpeqcvBYBZpSubF2191... | API 认证密钥 |
| seed | 整数 | 0 | 随机种子（0-2^31-1） |
| quality | 选择 | low | 图像质量 (low/medium/high) |
| background | 选择 | auto | 背景模式 (auto/opaque/transparent) |
| size | 选择 | auto | 输出尺寸 |
| n | 整数 | 1 | 生成图像数量（1-8） |
| image | 图像 | 可选 | 参考图像（用于图像编辑） |
| mask | 掩码 | 可选 | 修复掩码（白色区域将被替换） |
| model | 选择 | gpt-image-2 | 使用的模型 |

#### 支持的模型

- `gpt-image-1`: 基础模型
- `gpt-image-1.5`: 改进版本
- `gpt-image-2`: 最新版本（推荐）

#### 支持的图像尺寸

- auto
- 1024x1024
- 1024x1536
- 1536x1024
- 2048x2048
- 2048x1152
- 1152x2048
- 3840x2160
- 2160x3840

## 使用示例

### 基础文本生成图像

```
prompt: "A beautiful sunset over the ocean"
base_url: "https://api.laozhang.ai/v1"
api_key: "sk-your-api-key"
model: "gpt-image-2"
size: "1024x1024"
```

### 自定义 OpenAI API

```
prompt: "A futuristic city"
base_url: "https://your-custom-api.com/v1"
api_key: "your-custom-api-key"
quality: "high"
n: 4
```

## 配置默认值

要更改插件的默认 API 端点和密钥，编辑 `nodes.py` 文件中的：

```python
IO.String.Input(
    "base_url",
    default="https://api.laozhang.ai/v1",  # 修改此处
    ...
),
IO.String.Input(
    "api_key",
    default="sk-yrUpeqcvBYBZpSubF2191...",  # 修改此处
    ...
),
```

## 注意事项

- 确保提供的 API 密钥有效且具有足够的额度
- 不要在公开的工作流中泄露 API 密钥
- 某些 API 提供商可能有特定的速率限制和配额

## 故障排除

### "No images returned from API endpoint"
- 检查 API 密钥是否正确
- 验证账户是否有足够的额度
- 确保 base_url 格式正确

### 连接错误
- 验证 base_url 是否可访问
- 检查网络连接
- 确认 API 提供商的服务状态

### 认证失败
- 确保 api_key 未过期
- 检查 API 提供商的认证要求
- 验证密钥格式是否正确

## 许可证

MIT

## 支持

如有问题或建议，请提交 Issue 或 Pull Request。

---

**最后更新**: 2026-05-08
**版本**: 1.0.0
