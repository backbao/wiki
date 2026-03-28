---
layout: doc
---

# ImageService

> AI 绘图相关接口

<div class="api-badge-bar">
  <span class="api-badge">1 个接口</span>
</div>

### 🔵 POST `/api/image/generate`

**根据提示词生成图片**

#### 请求体

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
| --- | --- | --- | --- | --- |
| `prompt` | `string` | ✅ | 画图的提示词 (示例: `一只有翅膀的猫`) | - |
| `size` | `string` |  | 图片分辨率 | `"1024x1024"` |

**请求示例：**

```json
{
  "prompt": "一只有翅膀的猫",
  "size": "1024x1024"
}
```

#### 响应

**200** - OK

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
| --- | --- | --- | --- | --- |
| `image_url` | `string` | ✅ | 生成好的图片地址 | - |

---
