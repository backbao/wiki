---
layout: doc
---

# 📡 API 接口总览

> [!TIP]
> 此文档由 `generate-api-docs` 脚本自动生成，与后端代码实时同步。请勿手动编辑。

**API 版本：** `1.0.0` &nbsp; | &nbsp; **标题：** AI Chat API

## 分组列表

- [接口变更清单](/api/changelog)

### ChatService

AI 聊天相关接口

| 方法 | 路径 | 描述 |
| --- | --- | --- |
| 🔵 POST | [`/api/chat/`](/api/chatservice#post-api-chat) | 发送聊天消息 |
| 🟢 GET | [`/api/chat/end`](/api/chatservice#get-api-chat-end) | 结束当前对话 |
| 🟢 GET | [`/api/chat/history`](/api/chatservice#get-api-chat-history) | 获取聊天历史 |

[查看完整文档 →](/api/chatservice)

### ImageService

AI 绘图相关接口

| 方法 | 路径 | 描述 |
| --- | --- | --- |
| 🔵 POST | [`/api/image/generate`](/api/imageservice#post-api-image-generate) | 根据提示词生成图片 |

[查看完整文档 →](/api/imageservice)
