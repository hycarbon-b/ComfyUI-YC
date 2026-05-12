# ComfyUI OpenAI Custom API Plugin - 快速开始指南

## 安装步骤

1. **将插件文件夹复制到 custom_nodes**
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/yourusername/ComfyUI_OpenAI_CustomBase.git
   ```

2. **安装依赖（如果需要）**
   ```bash
   pip install -r ComfyUI_OpenAI_CustomBase/requirements.txt
   ```

3. **重启 ComfyUI**
   ```bash
   # 重新启动 ComfyUI 服务
   ```

## 使用方法

### 在 ComfyUI 中找到节点

- 节点类别: `api node/image/OpenAI`
- 节点名称: `OpenAI GPT Image (Custom API)`

### 配置参数

#### 最小配置（使用默认值）
只需输入 prompt 即可：
- **prompt**: "A beautiful sunset"

其他参数将使用默认值：
- base_url: https://api.laozhang.ai/v1
- api_key: sk-yrUpeqcvBYBZpSubF2191b324a674a03920d08065300C60b
- model: gpt-image-2
- size: auto
- quality: low

#### 完整配置示例

| 参数 | 值 | 说明 |
|------|-----|------|
| prompt | "A cyborg warrior in a cyberpunk city" | 图像描述 |
| base_url | https://api.laozhang.ai/v1 | API 地址 |
| api_key | sk-yrUpeqcvBYBZpSubF2191... | API 密钥 |
| model | gpt-image-2 | 使用的模型 |
| quality | high | 图像质量 |
| size | 1024x1024 | 输出尺寸 |
| n | 2 | 生成 2 张图像 |
| background | opaque | 不透明背景 |

### 图像编辑模式

如果上传了 `image` 和 `mask`：
- 节点会进入图像编辑模式
- prompt 描述要进行的编辑
- mask 的白色区域会被替换

## 使用不同的 API 提供商

只需修改 `base_url` 和 `api_key` 参数：

### 示例 1: 使用 OpenAI 官方 API
```
base_url: https://api.openai.com/v1
api_key: sk-your-openai-key
```

### 示例 2: 使用阿里云 OpenAI 兼容 API
```
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
api_key: sk-your-aliyun-key
```

### 示例 3: 使用本地 API 服务
```
base_url: http://localhost:8000/v1
api_key: your-local-key
```

## 常见问题

### Q: 无法连接到 API
A: 
- 检查 base_url 是否正确
- 确认网络连接
- 尝试在浏览器中访问 base_url/models（如果支持）

### Q: 认证失败
A:
- 检查 api_key 是否正确
- 确保 api_key 未过期
- 验证 API 提供商的认证格式

### Q: 生成失败 "No images returned"
A:
- 检查账户额度
- 验证 model 参数是否被支持
- 查看 API 提供商的日志

## 高级配置

### 修改全局默认值

编辑 `nodes.py` 中的这些行：

```python
IO.String.Input(
    "base_url",
    default="https://your-default-api.com/v1",  # 修改默认 API
    ...
),
IO.String.Input(
    "api_key",
    default="sk-your-default-key",  # 修改默认密钥
    ...
),
```

然后重启 ComfyUI。

## API 兼容性

此插件支持任何与 OpenAI API 兼容的端点，包括：
- ✅ OpenAI 官方 API
- ✅ 阿里云 DashScope
- ✅ Azure OpenAI
- ✅ 自建 API 服务
- ✅ 代理服务（如 api.laozhang.ai）

## 性能建议

- **batch_size**: 生成多张图像时，考虑 API 的速率限制
- **seed**: 使用相同的 seed 会生成相同的图像（用于测试）
- **size**: 更大的尺寸会消耗更多配额和时间

## 安全建议

⚠️ **重要**: 
- 不要在公开工作流中暴露 API 密钥
- 使用环境变量或配置文件管理敏感信息
- 定期更换 API 密钥
- 监控 API 使用情况

## 获取帮助

- 查看 [完整文档](README.md)
- 提交 Issue: https://github.com/yourusername/ComfyUI_OpenAI_CustomBase/issues
- 检查 ComfyUI 日志获取详细错误信息

---

**最后更新**: 2026-05-08
