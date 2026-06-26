# 轻量级语音问答服务 API 文档

## 1. 概述

本文档描述轻量级语音问答服务的所有 REST API 接口。服务基于 FastAPI 构建，提供统一的问答入口，支持文本和语音两种输入方式，可返回文本和语音合成结果。

**基础访问地址**：`http://127.0.0.1:8000`

**交互式文档**：服务启动后可访问 `http://127.0.0.1:8000/docs` 查看 Swagger UI 并在线调试接口。

---

## 2. 统一响应格式

所有接口均采用统一的 JSON 响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 业务状态码，0 表示成功，非 0 表示失败 |
| message | string | 状态描述信息 |
| data | object | 响应数据，成功时返回业务数据，失败时可能为 null |

> **注意**：HTTP 状态码始终为 200，业务错误通过 body 中的 `code` 字段区分。

---

## 3. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数错误（缺少必填参数或参数格式不正确） |
| 1002 | 会话不存在（session_id 无效） |
| 2001 | 语音识别失败（ASR 服务调用出错） |
| 2002 | AI 对话失败（LLM 服务调用出错） |
| 2003 | 语音合成失败（TTS 服务调用出错） |
| 3001 | 用户档案不存在 |
| 5000 | 服务器内部错误 |

---

## 4. 接口列表

### 4.1 健康检查

#### GET /api/health

检查服务是否正常运行。

**请求示例**：
```bash
curl http://127.0.0.1:8000/api/health
```

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "status": "ok",
    "version": "1.0.0",
    "message": "语音交互服务运行中"
  }
}
```

---

### 4.2 会话管理

#### POST /api/session/create

创建一个新的对话会话，返回 session_id。

**请求示例**：
```bash
curl -X POST http://127.0.0.1:8000/api/session/create
```

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

#### POST /api/session/clear

清空指定会话的对话历史（保留会话本身）。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

**请求示例**：
```bash
curl -X POST "http://127.0.0.1:8000/api/session/clear?session_id=xxx"
```

**响应示例**：
```json
{
  "code": 0,
  "message": "对话历史已清空",
  "data": null
}
```

---

#### DELETE /api/session/delete

删除指定的会话。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

**请求示例**：
```bash
curl -X DELETE "http://127.0.0.1:8000/api/session/delete?session_id=xxx"
```

**响应示例**：
```json
{
  "code": 0,
  "message": "会话已删除",
  "data": null
}
```

---

### 4.3 核心问答接口 ⭐

#### POST /api/ask

**统一问答接口**，支持文本和语音两种输入方式，自动完成 ASR → LLM → TTS 完整链路。

**请求格式**：`multipart/form-data`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| text | string | 二选一 | 纯文字提问，使用音频时留空 |
| audio | file | 二选一 | 音频文件，支持 mp3、wav 格式 |
| session_id | string | 否 | 对话会话 ID，传入可保留多轮上下文；不传则自动创建新会话 |
| return_audio | bool | 否 | 是否返回语音合成音频，默认 `true` |

> **注意**：`text` 和 `audio` 至少传一个，都传的话优先使用语音。

**请求示例 1：纯文本提问**
```bash
curl -X POST "http://127.0.0.1:8000/api/ask" \
  -F "text=你好，介绍一下这个语音助手" \
  -F "return_audio=false"
```

**请求示例 2：语音提问并返回语音**
```bash
curl -X POST "http://127.0.0.1:8000/api/ask" \
  -F "audio=@question.mp3" \
  -F "return_audio=true"
```

**请求示例 3：带会话 ID 的多轮对话**
```bash
curl -X POST "http://127.0.0.1:8000/api/ask" \
  -F "text=刚才的回答再详细说说" \
  -F "session_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "return_audio=false"
```

**响应示例（成功）**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_text": "你好，介绍一下这个语音助手",
    "reply_text": "你好！我是一个轻量级语音问答助手，支持语音和文字两种交互方式...",
    "audio_url": "/api/audio/output_xxx.mp3"
  }
}
```

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| session_id | string | 会话 ID，可用于后续多轮对话 |
| user_text | string | 用户的提问文本（语音输入时为 ASR 识别结果） |
| reply_text | string | AI 回答的文本内容 |
| audio_url | string | 语音合成音频的访问路径，`return_audio=false` 时为 null |

**响应示例（参数错误）**：
```json
{
  "code": 1001,
  "message": "请提供 text 或 audio 参数",
  "data": null
}
```

---

### 4.4 兼容旧接口

以下接口为兼容旧版本保留，新业务建议使用 `/api/ask` 统一接口。

#### POST /api/chat/text

文字对话接口。

**请求体**（JSON）：
```json
{
  "message": "你好",
  "session_id": "可选"
}
```

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "reply": "你好！有什么可以帮你的？",
    "session_id": "xxx"
  }
}
```

---

#### POST /api/chat/voice

语音对话接口。

**请求格式**：`multipart/form-data`

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio | file | 是 | 音频文件 |
| session_id | string | 否 | 会话 ID |

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_text": "你好",
    "reply_text": "你好！",
    "audio_url": "/api/audio/output_xxx.mp3",
    "session_id": "xxx"
  }
}
```

---

### 4.5 音频文件

#### GET /api/audio/{filename}

获取生成的语音合成音频文件。

**请求参数**（Path）：

| 参数名 | 类型 | 说明 |
|--------|------|------|
| filename | string | 音频文件名 |

**响应**：返回 `audio/mpeg` 类型的音频文件流。

---

### 4.6 CRM 用户信息

#### GET /api/crm/profile

获取指定会话的用户信息档案。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "session_id": "xxx",
    "name": "张三",
    "age": 28,
    "gender": "男",
    "phone": null,
    "email": null,
    "location": "北京",
    "interests": "[\"科技\", \"音乐\"]",
    "requirements": "[\"了解产品\"]",
    "notes": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

---

#### PUT /api/crm/profile

手动更新用户信息。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

**请求体**（JSON）：
```json
{
  "name": "张三",
  "age": 28,
  "gender": "男",
  "phone": "13800138000",
  "email": "zhangsan@example.com",
  "location": "北京",
  "interests": ["科技", "音乐"],
  "requirements": ["了解产品"],
  "notes": "备注信息"
}
```

> 所有字段均为选填，只更新传入的字段。

---

#### GET /api/crm/profiles

获取所有用户档案列表。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| limit | int | 否 | 50 | 返回数量限制 |

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 2,
    "profiles": [
      { ... },
      { ... }
    ]
  }
}
```

---

#### DELETE /api/crm/profile

删除指定用户的档案。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

---

#### POST /api/crm/extract

手动触发从对话历史中提取用户信息。

**请求参数**（Query）：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话 ID |

**响应示例**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "extracted": {
      "location": "北京"
    },
    "profile": { ... }
  }
}
```

---

## 5. 调用建议

1. **首次调用**：不传 `session_id`，服务会自动创建新会话并返回，后续调用传入该 ID 即可保持多轮上下文。
2. **语音输入**：建议使用 mp3 格式，采样率 16kHz 以上效果最佳。
3. **语音输出**：`return_audio=true` 时会返回音频 URL，通过 GET 请求访问即可播放。
4. **会话清理**：会话历史保存在内存中，服务重启会丢失。长期使用建议自行持久化。
