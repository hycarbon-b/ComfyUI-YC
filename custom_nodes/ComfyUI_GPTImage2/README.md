# ComfyUI_GPTImage2

通过云端 API 集成 gpt-image-2 图像生成模型的 ComfyUI 节点。
<img width="759" height="732" alt="ScreenShot_2026-04-23_083105_787" src="https://github.com/user-attachments/assets/71da69ea-e199-4568-970e-86dd62590d84" />

## 安装

1. 将文件夹复制到 `ComfyUI/custom_nodes/` 目录
2. 安装依赖：`pip install -r requirements.txt`
3. 编辑 `config.json` 填入 API 地址和密钥
4. 重启 ComfyUI

## 节点

### 文生图 (Text2Img)

根据文本提示词生成图像。

**参数：**

| 参数 | 选项 | 默认值 | 说明 |
|------|------|--------|------|
| prompt | 字符串 | — | 图像描述 |
| model | gpt-image-2, gpt-image-1.5, gpt-image-1 | gpt-image-2 | 模型 |
| quality | low, medium, high, auto | medium | 质量 |
| size | auto
| n | 1-10 | 1 | 生成数量 |
| seed | 整数 | -1 | 随机种子 |
| output_format | png, jpeg, webp | png | 输出格式 |

### 图生图 (Img2Img)

在文本引导下转换输入图像。

说明：多张参考图会按 OpenAI 官方 Image Edits 语义逐张上传，不再在本地拼接成一张宽图。对于 `gpt-image-2`，插件也不会再发送 `input_fidelity`，因为该模型固定以高保真处理输入图像。

网关兼容说明：如果网关拒绝 `multipart/form-data` 的 `/images/edits`（例如只允许 `application/json`），插件会自动回退到 `/images/generations` 的 JSON 参考图模式，并自动附加一张透明空 `mask` 来实现图生图流程。

**参数：**

| 参数 | 选项 | 默认值 | 说明 |
|------|------|--------|------|
| image1 | IMAGE | — | 输入图像（必填） |
| prompt | 字符串 | — | 转换指令（必填） |
| model | gpt-image-2, gpt-image-1.5, gpt-image-1 | gpt-image-2 | 模型 |
| input_fidelity | low, high | high | 保持原图程度 |
| quality | low, medium, high, auto | medium | 质量 |
| size |  auto 
| n | 1-10 | 1 | 生成数量 |
| seed | 整数 | -1 | 随机种子 |
| output_format | png, jpeg, webp | png | 输出格式 |
| image2-image5 | IMAGE | — | 可选附加图像 |

## 配置

编辑 `config.json`：

```json
{
  "base_url": "https://api.bltcy.ai/v1",
  "api_key": "你的_api_key"
}
```

KEY地址：
https://api.bltcy.ai/

如果你使用的是第三方 OpenAI 兼容网关，图生图接口必须支持标准 `multipart/form-data` 的 `POST /images/edits`。如果网关只接受 `application/json`，文生图可能还能工作，但图生图会失败。

## 常见问题

- **生成慢**：降低 quality 或减小 size，网络不稳定也会影响速度
- **无图像返回**：检查 api_key 和账户额度
- **超时**：可调高 nodes.py 中的 timeout 参数（默认 120 秒）
