# ComfyUI OpenAI Custom API Plugin - 技术文档

## 概述

ComfyUI_OpenAI_CustomBase 是一个独立的外部插件，基于官方 ComfyUI OpenAI API 节点进行定制和扩展。它为用户提供了：

1. **自定义 API 端点支持**: 支持任何 OpenAI 兼容的 API 提供商
2. **灵活的认证机制**: 每个节点可独立配置 API 密钥
3. **预配置默认值**: 开箱即用，默认指向特定的 API 端点

## 架构设计

### 插件结构

```
ComfyUI_OpenAI_CustomBase/
├── __init__.py              # 包初始化，导出节点映射
├── nodes.py                 # 主节点实现
├── requirements.txt         # Python 依赖
├── pyproject.toml          # 项目配置
├── README.md               # 项目文档
├── QUICKSTART.md           # 快速开始指南
├── LICENSE                 # MIT 许可证
├── example_workflow.json   # 示例工作流
└── .gitignore              # Git 忽略文件
```

### 核心组件

#### 1. OpenAIGPTImageCustom 节点

这是主要的图像生成节点，具有以下特性：

- **完整的图像生成支持**: 文本生成图像、图像编辑、图像修复
- **自定义 API 配置**: base_url 和 api_key 作为输入参数
- **多模型支持**: gpt-image-1, gpt-image-1.5, gpt-image-2
- **灵活的输出尺寸**: 支持 8 种不同的尺寸选项
- **批量生成**: 一次调用生成多张图像

#### 2. 辅助函数

```python
# 价格计算函数
calculate_tokens_price_image_1()    # gpt-image-1 价格
calculate_tokens_price_image_1_5()  # gpt-image-1.5 价格
calculate_tokens_price_image_2_0()  # gpt-image-2 价格

# 验证和转换函数
validate_and_cast_response()        # 将 API 响应转换为图像张量
```

## 集成指南

### 从官方插件迁移

如果你已经在使用官方的 OpenAI 节点，可以通过以下方式集成此插件：

1. **保留现有工作流**: 官方节点继续可用
2. **添加自定义选项**: 同时使用此插件获得更灵活的配置
3. **无冲突共存**: 两个插件可以同时安装

### 修改默认值

编辑 `nodes.py` 中的默认参数：

```python
# 第 95-98 行
IO.String.Input(
    "base_url",
    default="https://api.laozhang.ai/v1",  # 修改此处
    tooltip="OpenAI-compatible API base URL",
),
IO.String.Input(
    "api_key",
    default="sk-yrUpeqcvBYBZpSubF2191b324a674a03920d08065300C60b",  # 修改此处
    tooltip="API key for authentication",
),
```

## API 兼容性

### 支持的 OpenAI 兼容 API

此插件使用标准的 OpenAI API 格式，支持以下端点：

```
POST {base_url}/images/generations
POST {base_url}/images/edits
```

**支持的提供商**：
- ✅ OpenAI 官方 API (api.openai.com)
- ✅ Azure OpenAI (azure.microsoft.com)
- ✅ 阿里云 DashScope (dashscope.aliyuncs.com)
- ✅ api.laozhang.ai（默认配置）
- ✅ 任何 OpenAI 兼容的自建 API 服务

### 认证机制

插件使用 Bearer Token 认证：

```
Authorization: Bearer {api_key}
```

如果需要其他认证方式，请修改 `execute()` 方法中的 headers 部分：

```python
# 当前实现（第 225 行）
headers: dict[str, str] = {
    "Authorization": f"Bearer {api_key.strip()}",
}

# 可修改为其他格式，如：
# headers["X-API-Key"] = api_key.strip()
# headers["Authorization"] = f"Bearer {api_key.strip()}"
```

## 扩展开发

### 添加新的节点

要添加新的节点类，遵循以下模板：

```python
class MyNewNode(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="MyNodeId",
            display_name="My Node Display Name",
            category="api node/image/OpenAI",
            description="Node description",
            inputs=[...],
            outputs=[...],
            hidden=[IO.Hidden.unique_id],
            is_api_node=True,
        )

    @classmethod
    async def execute(cls, **kwargs) -> IO.NodeOutput:
        # 实现节点逻辑
        pass

# 更新节点映射
NODE_CLASS_MAPPINGS = {
    "OpenAIGPTImageCustom": OpenAIGPTImageCustom,
    "MyNewNode": MyNewNode,  # 添加新节点
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenAIGPTImageCustom": "OpenAI GPT Image (Custom API)",
    "MyNewNode": "My Node Display Name",  # 添加显示名称
}
```

### 添加新的模型支持

修改 `execute()` 方法中的模型列表：

```python
IO.Combo.Input(
    "model",
    options=["gpt-image-1", "gpt-image-1.5", "gpt-image-2", "gpt-image-3"],  # 添加新模型
    default="gpt-image-2",
    optional=True,
),
```

## 性能优化

### 图像处理优化

- 自动缩放图像到最大 2048x2048 像素以优化 API 调用
- 支持批量处理多张图像
- 异步处理确保 ComfyUI 响应性

### API 调用优化

```python
# 支持自动重试（在 sync_op 中）
sync_op(
    cls,
    endpoint,
    max_retries=3,           # 最多重试 3 次
    retry_delay=1.0,         # 初始延迟 1 秒
    retry_backoff=2.0,       # 指数退避因子
    ...
)
```

## 错误处理

插件包含以下错误处理机制：

1. **输入验证**: 
   ```python
   validate_string(prompt, strip_whitespace=False)
   validate_string(base_url, strip_whitespace=True, min_length=1)
   validate_string(api_key, strip_whitespace=True, min_length=1)
   ```

2. **API 错误处理**: 自动重试机制（由 sync_op 提供）

3. **图像处理错误**: 
   ```python
   if mask is not None and image is None:
       raise ValueError("Cannot use a mask without an input image")
   ```

## 依赖管理

### 必需依赖

- `requests>=2.28.0`: HTTP 请求库
- `Pillow>=9.0.0`: 图像处理
- `numpy>=1.23.0`: 数值计算
- `torch>=2.0.0`: 深度学习框架
- `pydantic>=2.0.0`: 数据验证
- `aiohttp>=3.8.0`: 异步 HTTP 客户端

### 可选依赖

开发环境依赖（在 pyproject.toml 中定义）：
- `black`: 代码格式化
- `isort`: 导入排序
- `flake8`: 代码检查
- `mypy`: 类型检查

## 调试指南

### 启用详细日志

ComfyUI 会自动记录 API 调用。查看以下文件：
- 标准输出：终端窗口
- ComfyUI 日志：`ComfyUI/logs/` 目录

### 常见问题排查

**问题**: API 连接失败
```
调试步骤:
1. 验证 base_url 格式: 应包含 "https://" 或 "http://"
2. 检查网络连接: ping {base_url}
3. 验证 API 可用性: curl -H "Authorization: Bearer {api_key}" {base_url}/models
```

**问题**: 认证失败
```
调试步骤:
1. 确认 api_key 未过期
2. 验证 API 提供商的认证格式
3. 检查请求头: Authorization: Bearer {api_key}
```

**问题**: 图像生成失败
```
调试步骤:
1. 检查 API 返回的错误信息
2. 验证 model 参数是否被支持
3. 检查账户余额和速率限制
```

## 版本更新

### v1.0.0 (2026-05-08)
- 初始版本
- 完整的 GPT Image 支持
- 自定义 API 端点配置
- 默认配置为 api.laozhang.ai

## 许可证

MIT License - 详见 LICENSE 文件

## 贡献指南

欢迎提交 Pull Request 和 Issue！

## 联系方式

- GitHub: https://github.com/yourusername/ComfyUI_OpenAI_CustomBase
- Issues: https://github.com/yourusername/ComfyUI_OpenAI_CustomBase/issues

---

**最后更新**: 2026-05-08
