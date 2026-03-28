---
layout: doc
---

# ChatService

> AI 聊天相关接口

<div class="api-badge-bar">
  <span class="api-badge">3 个接口</span>
</div>

### 🔵 POST `/api/chat/`

**发送聊天消息**

#### 请求体

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
| --- | --- | --- | --- | --- |
| `is_stream` | `boolean` |  | 是否开启流式传输模式 | `true` |
| `message` | `string` | ✅ | 用户输入的聊天内容 (示例: `你好`) | - |
| `model_id` | `string` |  | 使用的模型ID | `"gpt-4"` |

**请求示例：**

```json
{
  "is_stream": true,
  "message": "你好",
  "model_id": "gpt-4"
}
```

#### 响应

**200** - OK

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
| --- | --- | --- | --- | --- |
| `reply` | `string` | ✅ | AI 的回复内容 | - |
| `success` | `boolean` | ✅ |  | - |

---

### 🟢 GET `/api/chat/end`

**结束当前对话**

#### 响应

---

### 🟢 GET `/api/chat/history`

**获取聊天历史**

#### 响应

---
