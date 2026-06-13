# 智能记账聊天机器人 — 接口文档

> 基础地址：`http://localhost:3001`  
> 所有请求/响应均使用 JSON 格式，字符编码为 UTF-8。

---

## 目录

1. [会话管理](#1-会话管理)
2. [消息管理](#2-消息管理)
3. [AI 对话](#3-ai-对话)
4. [FAQ 知识库检索](#4-faq-知识库检索)
5. [满意度反馈](#5-满意度反馈)
6. [管理后台 API](#6-管理后台-api)
7. [健康检查](#7-健康检查)

---

## 1. 会话管理

### 1.1 创建新会话

```
POST /api/sessions
```

**请求体**

| 字段    | 类型   | 必填 | 说明                         |
| ------- | ------ | ---- | ---------------------------- |
| `title` | string | 否   | 会话标题，默认为「新对话」 |

**请求示例**

```json
{
  "title": "本月账单查询"
}
```

**响应示例**

```json
{
  "id": "session_1750100000000_abc123def",
  "title": "本月账单查询"
}
```

---

### 1.2 获取所有会话

```
GET /api/sessions
```

**响应示例**

```json
[
  {
    "id": "session_1750100000000_abc123def",
    "title": "本月账单查询",
    "createdAt": 1750100000000,
    "updatedAt": 1750100100000
  }
]
```

> 列表按 `updatedAt` 降序排列。

---

### 1.3 获取单个会话

```
GET /api/sessions/:id
```

---

### 1.4 删除会话

```
DELETE /api/sessions/:id
```

> 删除会话会同时删除该会话下的所有消息。

---

## 2. 消息管理

### 2.1 获取会话消息

```
GET /api/sessions/:id/messages
```

消息按 `timestamp` 升序排列。

---

## 3. AI 对话

### 3.1 非流式对话（uni-app 移动端专用）

```
POST /api/chat
```

**请求体**

| 字段        | 类型   | 必填 | 说明                              |
| ----------- | ------ | ---- | --------------------------------- |
| `sessionId` | string | 是   | 会话ID                            |
| `message`   | string | 是   | 用户消息                          |
| `context`   | object | 否   | 用户记账数据上下文（动态注入提示词）|

**响应示例**

```json
{
  "answer": "好的，已为您记录：餐饮消费 ¥50.00"
}
```

---

### 3.2 流式对话（SSE）

```
GET /api/chat/stream
```

**查询参数**

| 参数        | 类型   | 必填 | 说明     |
| ----------- | ------ | ---- | -------- |
| `sessionId` | string | 是   | 会话ID   |
| `message`   | string | 是   | 用户消息 |
| `context`   | string | 否   | 上下文JSON |

**SSE 事件类型**

| type          | 说明                   |
| ------------- | ---------------------- |
| `user_msg_id` | 用户消息已保存         |
| `content`     | AI 回复增量文本        |
| `done`        | 回复完成               |
| `error`       | 出错                   |

---

## 4. FAQ 知识库检索

```
GET /api/faq/search?query=关键词
```

最多返回 5 条匹配结果。

---

## 5. 满意度反馈

```
POST /api/feedback
```

**请求体**

| 字段        | 类型   | 必填 | 说明        |
| ----------- | ------ | ---- | ----------- |
| `messageId` | string | 是   | 消息ID      |
| `rating`    | number | 是   | 评分（1-5） |
| `comment`   | string | 否   | 评语        |

---

## 6. 管理后台 API

### 6.1 全局统计

```
GET /api/admin/stats
```

### 6.2 对话列表（分页）

```
GET /api/admin/conversations?page=1&limit=20
```

### 6.3 满意度统计

```
GET /api/admin/satisfaction
```

---

## 7. 健康检查

```
GET /api/health
```

**响应示例**

```json
{
  "status": "ok",
  "timestamp": "2026-06-10T10:30:00.000Z"
}
```

---

## 技术栈

- **后端**: Node.js + Express + TypeScript
- **数据库**: SQLite (sql.js)
- **AI 对话**: Agnes AI API（SSE 流式）
