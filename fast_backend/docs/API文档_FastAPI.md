# API 接口文档

## 概述

本文档详细描述了记账管理系统的 API 接口，包括用户管理、分类管理、记账、统计、管理后台和 AI 助手等功能模块。

文档基于 FastAPI 重写实现（`fast_backend`），业务规则对齐原 Spring Boot 版契约；接口实现状态、决策点及 Spring 版端点映射见文末[附录](#附录)。

## 基础URL

```
http://localhost:8080
```

## 认证方式

大部分接口需要认证，认证通过在请求头中添加 `Authorization` 字段实现：

```
Authorization: Bearer <token>
```

`token` 为登录接口返回的 JWT，有效期 24 小时。未登录或令牌失效时返回 HTTP 401。

## 响应格式

所有接口返回 JSON 格式数据，通用响应结构如下：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- 成功时 `code` 恒为 `200`；失败时 `code` 与 HTTP 状态码一致（400 / 401 / 403 / 404 / 422 / 500），`data` 为 `null`。
- 唯一例外：`POST /api/ai/chat` 为 SSE 流式响应，不遵循本结构。

## 接口详情

### 用户管理模块

#### 1. 用户注册

- **接口地址**: `POST /api/user/register`
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名，2-20 位中英文或数字组合 |
| password | string | 是 | 密码，6 位数字 |
| nickname | string | 否 | 昵称，最长 50 字符 |

- **请求示例**:

```json
{
  "username": "zhangsan",
  "password": "123456",
  "nickname": "张三"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "注册成功",
  "data": null
}
```

- **业务规则**: 用户名重复时返回 400 `用户名已存在`；密码使用 bcrypt 加密存储（兼容 Spring 存量数据）。

#### 2. 用户登录

- **接口地址**: `POST /api/user/login`
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

- **请求示例**:

```json
{
  "username": "zhangsan",
  "password": "123456"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

- **业务规则**: 用户不存在返回 400 `用户未注册，请注册后登录`；密码错误返回 400 `密码错误`。

#### 3. 获取用户信息

- **接口地址**: `GET /api/user/info`
- **请求头**: 需要认证
- **请求示例**:

```
GET /api/user/info
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "nickname": "张三",
    "avatar": "/uploads/avatars/3f2a9c8e1b4d5f6a7c8d9e0f1a2b3c4d.png",
    "email": null,
    "phone": "13800000000",
    "role": 0,
    "created_at": "2026-06-12T10:31:00",
    "updated_at": "2026-06-12T10:31:00"
  }
}
```

- **业务规则**: 用户不存在返回 404 `用户不存在`。

#### 4. 更新用户信息

- **接口地址**: `PUT /api/user/update`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| nickname | string | 否 | 昵称，最长 50 字符 |
| email | string | 否 | 邮箱，最长 100 字符 |
| phone | string | 否 | 手机号，最长 20 字符，唯一 |

- **请求示例**:

```json
{
  "nickname": "张三丰"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "更新成功",
  "data": null
}
```

#### 5. 修改用户密码

- **接口地址**: `PUT /api/user/password`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| oldPassword | string | 是 | 当前密码 |
| newPassword | string | 是 | 新密码，6 位数字 |

- **请求示例**:

```json
{
  "oldPassword": "123456",
  "newPassword": "654321"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "密码修改成功",
  "data": null
}
```

- **业务规则**: 旧密码错误返回 400 `原密码错误`。

#### 6. 上传头像

- **接口地址**: `POST /api/user/avatar`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file | file | 是 | 头像图片，仅支持 JPG/PNG，大小不超过 2MB |

- **请求示例**:

```
POST /api/user/avatar
Content-Type: multipart/form-data

file: avatar.png
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "avatarUrl": "/uploads/avatars/3f2a9c8e1b4d5f6a7c8d9e0f1a2b3c4d.png"
  }
}
```

### 分类管理模块

#### 1. 获取分类列表

- **接口地址**: `GET /api/categories`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| type | integer | 否 | 分类类型，0=支出 1=收入，不传返回全部 |

- **请求示例**:

```
GET /api/categories
GET /api/categories?type=1
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 12,
      "userId": 0,
      "name": "餐饮",
      "type": 1,
      "icon": "🍜",
      "sortOrder": 1
    }
  ]
}
```

- **业务规则**: 返回当前用户的分类及系统预设分类（`userId=0`）。

#### 2. 新增分类

- **接口地址**: `POST /api/categories`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 分类名称，最长 50 字符 |
| type | integer | 是 | 分类类型，0=支出 1=收入 |
| icon | string | 否 | 图标，最长 50 字符 |
| sortOrder | integer | 否 | 排序值，默认为 0 |

- **请求示例**:

```json
{
  "name": "交通",
  "type": 1,
  "icon": "🚌",
  "sortOrder": 2
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "创建成功",
  "data": null
}
```

#### 3. 修改分类

- **接口地址**: `PUT /api/categories/{category_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category_id | integer | 是 | 分类ID |

- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 否 | 分类名称 |
| type | integer | 否 | 分类类型，0=支出 1=收入 |
| icon | string | 否 | 图标 |
| sortOrder | integer | 否 | 排序值 |

- **请求示例**:

```json
{
  "name": "通勤"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "更新成功",
  "data": null
}
```

- **业务规则**: 分类不存在或无权操作时返回 404 `分类不存在`（不区分两种情况）。

#### 4. 删除分类

- **接口地址**: `DELETE /api/categories/{category_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category_id | integer | 是 | 分类ID |

- **请求示例**:

```
DELETE /api/categories/12
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

- **业务规则**: 归属校验同修改分类；删除后引用该分类的历史账单 `categoryName` 显示为 null。

### 记账模块

#### 1. 获取账单列表

- **接口地址**: `GET /api/records`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page | integer | 否 | 页码，默认为 1 |
| size | integer | 否 | 每页条数，默认为 10 |
| categoryId | integer | 否 | 按分类筛选 |
| type | integer | 否 | 按类型筛选，0=支出 1=收入 |
| month | string | 否 | 按月份筛选，格式 `yyyy-MM`，如 `2026-06` |

- **请求示例**:

```
GET /api/records
GET /api/records?page=2&size=20&categoryId=12&month=2026-06
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 45,
        "userId": 3,
        "categoryId": 12,
        "type": 1,
        "amount": 12.5,
        "date": "2026-06-12",
        "remark": "午餐",
        "categoryName": "餐饮"
      }
    ],
    "total": 128
  }
}
```

#### 2. 新增账单

- **接口地址**: `POST /api/records`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| categoryId | integer | 是 | 分类ID |
| type | integer | 是 | 类型，0=支出 1=收入 |
| amount | number | 是 | 金额，必须大于 0 |
| date | string | 是 | 记账日期，格式 `yyyy-MM-dd` |
| remark | string | 否 | 备注，最长 200 字符 |

- **请求示例**:

```json
{
  "categoryId": 12,
  "type": 1,
  "amount": 12.5,
  "date": "2026-06-12",
  "remark": "午餐"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "记账成功",
  "data": null
}
```

- **业务规则**: 分类不存在或无权使用返回 404 `分类不存在`；日期格式非法返回 422。

#### 3. 修改账单

- **接口地址**: `PUT /api/records/{record_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| record_id | integer | 是 | 账单ID |

- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| categoryId | integer | 否 | 分类ID |
| type | integer | 否 | 类型，0=支出 1=收入 |
| amount | number | 否 | 金额，必须大于 0 |
| date | string | 否 | 记账日期，格式 `yyyy-MM-dd` |
| remark | string | 否 | 备注 |

- **请求示例**:

```json
{
  "amount": 15.0,
  "remark": "午餐（加蛋）"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "更新成功",
  "data": null
}
```

- **业务规则**: 账单不存在或无权操作返回 404 `记录不存在`；仅更新传入的字段，未传字段保留原值。

#### 4. 删除账单

- **接口地址**: `DELETE /api/records/{record_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| record_id | integer | 是 | 账单ID |

- **请求示例**:

```
DELETE /api/records/45
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

- **业务规则**: 归属校验同修改账单；采用软删除（`status=0`），删除后列表与统计中不再出现。

#### 5. 获取账单详情（建议补充）

- **接口地址**: `GET /api/records/{record_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| record_id | integer | 是 | 账单ID |

- **请求示例**:

```
GET /api/records/45
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 45,
    "userId": 3,
    "categoryId": 12,
    "type": 1,
    "amount": 12.5,
    "date": "2026-06-12",
    "remark": "午餐",
    "categoryName": "餐饮"
  }
}
```

### 统计模块

#### 1. 收支汇总

- **接口地址**: `GET /api/statistics/summary`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| year | integer | 否 | 年份，与 month 同时传入时按月统计，否则统计全部 |
| month | integer | 否 | 月份，1-12 |

- **请求示例**:

```
GET /api/statistics/summary
GET /api/statistics/summary?year=2026&month=6
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totalIncome": 12500.0,
    "totalExpense": 8300.5,
    "balance": 4199.5,
    "recordCount": 156
  }
}
```

- **业务规则**: `balance = totalIncome - totalExpense`；无数据时各值均为 0。

#### 2. 收支趋势

- **接口地址**: `GET /api/statistics/trend`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| days | integer | 否 | 统计最近 N 天的每日收支，默认为 30 |

- **请求示例**:

```
GET /api/statistics/trend?days=30
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "date": "2026-06-11",
      "income": 0.0,
      "expense": 86.5
    },
    {
      "date": "2026-06-12",
      "income": 5000.0,
      "expense": 12.5
    }
  ]
}
```

#### 3. 分类统计

- **接口地址**: `GET /api/statistics/category`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| year | integer | 否 | 年份，与 month 同时传入时按月统计，否则统计全部 |
| month | integer | 否 | 月份，1-12 |
| type | integer | 否 | 分类类型，默认 0（支出） |

- **请求示例**:

```
GET /api/statistics/category?year=2026&month=6&type=1
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "categoryId": 12,
      "categoryName": "餐饮",
      "total": 2100.5,
      "count": 38,
      "percentage": 41.2
    }
  ]
}
```

- **业务规则**: 按分类金额降序返回；`percentage = total / 汇总金额 * 100`，保留 1 位小数，无数据时全为 0。

### 管理后台模块

> 本模块全部接口需要管理员权限，非管理员返回 HTTP 403。

#### 1. 获取用户列表

- **接口地址**: `GET /api/admin/users`
- **请求头**: 需要认证（管理员）
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| page | integer | 否 | 页码，默认为 1 |
| size | integer | 否 | 每页条数，默认为 10 |
| keyword | string | 否 | 用户名模糊搜索 |

- **请求示例**:

```
GET /api/admin/users?page=1&size=10&keyword=张
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [
      {
        "id": 1,
        "username": "zhangsan",
        "nickname": "张三",
        "avatar": "/uploads/avatars/xxx.png",
        "email": null,
        "phone": "13800000000",
        "role": 0
      }
    ],
    "total": 5
  }
}
```

#### 2. 启用/禁用用户

- **接口地址**: `PUT /api/admin/users/{user_id}/status`
- **请求头**: 需要认证（管理员）
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | integer | 是 | 用户ID |

- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | integer | 是 | 用户状态，0=禁用 1=启用 |

- **请求示例**:

```json
{
  "status": 0
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "操作成功",
  "data": null
}
```

- **业务规则**: 用户不存在返回 404 `用户不存在`。

#### 3. 获取全部分类

- **接口地址**: `GET /api/admin/categories`
- **请求头**: 需要认证（管理员）
- **请求示例**:

```
GET /api/admin/categories
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "userId": 0,
      "name": "餐饮",
      "type": 1,
      "icon": "🍜",
      "sortOrder": 1
    }
  ]
}
```

#### 4. 获取 FAQ 列表

- **接口地址**: `GET /api/admin/faq`
- **请求头**: 需要认证（管理员）
- **请求示例**:

```
GET /api/admin/faq
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "question": "如何导出账单？",
      "answer": "前往设置页选择导出即可。",
      "category": "使用帮助"
    }
  ]
}
```

#### 5. 新增 FAQ

- **接口地址**: `POST /api/admin/faq`
- **请求头**: 需要认证（管理员）
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| question | string | 是 | 问题内容 |
| answer | string | 是 | 回答内容 |
| category | string | 否 | 分类标签 |

- **请求示例**:

```json
{
  "question": "如何导出账单？",
  "answer": "前往设置页选择导出即可。",
  "category": "使用帮助"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "创建成功",
  "data": null
}
```

#### 6. 修改 FAQ

- **接口地址**: `PUT /api/admin/faq/{faq_id}`
- **请求头**: 需要认证（管理员）
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| faq_id | integer | 是 | FAQ ID |

- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| question | string | 否 | 问题内容 |
| answer | string | 否 | 回答内容 |
| category | string | 否 | 分类标签 |

- **请求示例**:

```json
{
  "answer": "前往「我的-设置」页选择导出即可。"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "更新成功",
  "data": null
}
```

#### 7. 删除 FAQ

- **接口地址**: `DELETE /api/admin/faq/{faq_id}`
- **请求头**: 需要认证（管理员）
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| faq_id | integer | 是 | FAQ ID |

- **请求示例**:

```
DELETE /api/admin/faq/1
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

### AI 助手模块

#### 1. 获取会话列表

- **接口地址**: `GET /api/ai/sessions`
- **请求头**: 需要认证
- **请求示例**:

```
GET /api/ai/sessions
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 7,
      "title": "新对话",
      "created_at": "2026-06-12T10:30:00"
    }
  ]
}
```

#### 2. 新建会话

- **接口地址**: `POST /api/ai/sessions`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 否 | 会话标题，不传默认为「新对话」，最长 100 字符 |

- **请求示例**:

```json
{
  "title": "六月账单咨询"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 7,
    "title": "六月账单咨询",
    "created_at": "2026-06-12T10:30:00"
  }
}
```

#### 3. 删除会话

- **接口地址**: `DELETE /api/ai/sessions/{session_id}`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | integer | 是 | 会话ID |

- **请求示例**:

```
DELETE /api/ai/sessions/7
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

- **业务规则**: 会话不存在或无权操作返回 404 `会话不存在`；采用软删除。

#### 4. 获取会话消息列表

- **接口地址**: `GET /api/ai/sessions/{session_id}/messages`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | integer | 是 | 会话ID |

- **请求示例**:

```
GET /api/ai/sessions/7/messages
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 90,
      "role": "user",
      "content": "这个月花了多少？",
      "created_at": "2026-06-12T10:31:00"
    },
    {
      "id": 91,
      "role": "assistant",
      "content": "本月支出 8300.50 元……",
      "created_at": "2026-06-12T10:31:03"
    }
  ]
}
```

#### 5. 发送消息

- **接口地址**: `POST /api/ai/chat`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | integer | 是 | 会话ID |
| message | string | 是 | 用户消息内容 |

- **请求示例**:

```json
{
  "session_id": 7,
  "message": "这个月哪类花费最多？"
}
```

- **响应示例**（SSE 流式，`Content-Type: text/event-stream`）:

```
data: {"type": "content", "data": "本月支出最多的是"}

data: {"type": "content", "data": "「餐饮」类，共 2100.50 元，建议适当控制"}

data: {"type": "done"}
```

- **事件说明**:

| 事件类型 | 说明 |
|----------|------|
| content | 增量生成内容，可多次出现，前端按文本流拼接 |
| done | 生成结束 |
| error | 生成失败，data 为错误原因 |

- **业务规则**: 回复内容基于当前用户当月统计、支出/收入分类 Top5 及最近 10 条账单自动组装上下文；消息将写入会话历史。

#### 6. 获取会话消费分析

- **接口地址**: `GET /api/ai/sessions/{session_id}/analysis`
- **请求头**: 需要认证
- **路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | integer | 是 | 会话ID |

- **请求示例**:

```
GET /api/ai/sessions/7/analysis
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "expense": {
      "total_expense": 8300.5,
      "top_categories": [
        {
          "name": "餐饮",
          "amount": 2100.5,
          "percentage": 25.3
        }
      ],
      "suggestions": [
        "餐饮类支出占比偏高，建议适当控制"
      ]
    },
    "budget": {
      "monthly_budget": 5000.0,
      "category_budgets": [
        {
          "name": "餐饮",
          "budget": 1500.0
        }
      ],
      "tips": [
        "按当前支出节奏，月底可能超支"
      ]
    }
  }
}
```

#### 7. 提交反馈

- **接口地址**: `POST /api/ai/feedback`
- **请求头**: 需要认证
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| message_id | integer | 是 | 关联消息ID |
| type | string | 是 | 反馈类型，like / dislike |
| content | string | 否 | 补充说明 |

- **请求示例**:

```json
{
  "message_id": 91,
  "type": "like",
  "content": "分析很准"
}
```

- **响应示例**:

```json
{
  "code": 200,
  "message": "反馈成功",
  "data": null
}
```

### 公共接口

#### 1. 健康检查

- **接口地址**: `GET /api/health`
- **响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "version": "2.0.0"
  }
}
```

---

## 附录

### A. 错误码说明

| HTTP 状态码 | code | message | 触发场景 |
|---|---|---|---|
| 400 | 400 | 业务错误具体文案 | 用户名已存在、密码错误、原密码错误、头像校验失败、数据约束冲突等 |
| 401 | 401 | 无效令牌 | 未携带或携带无效/过期令牌 |
| 403 | 403 | 无管理员权限 | 非管理员访问 `/api/admin/**` |
| 404 | 404 | 用户不存在 / 分类不存在 / 记录不存在 / 会话不存在 | 资源不存在或无权操作（不区分两种情况） |
| 422 | 422 | 字段校验失败详情 | 参数缺失、类型错误、格式非法（如日期非 `yyyy-MM-dd`） |
| 500 | 500 | 数据库操作失败，请稍后重试 / 服务器内部错误 | 数据库异常或其他未捕获异常 |

### B. Spring → FastAPI 端点映射总表

| Spring 端点 | FastAPI 对应 | 状态 | 差异摘要 |
|---|---|---|---|
| POST /api/user/register | POST /api/user/register | ✅ | 入参多 nickname；出参 data 形态待定（见 C 决策 D12） |
| POST /api/user/login | POST /api/user/login | ✅ | data 为 `{"token"}` 对象（Spring 为裸 token 字符串） |
| GET /api/user/info | GET /api/user/info | ✅ | 出参为 UserOut（id/username/nickname/avatar/email/phone/role/created_at/updated_at）；role 用 0/1 数字而非 `"user"/"admin"` 字符串 |
| PUT /api/user/info（改用户名） | PUT /api/user/update | ⚠️ | 路径不同；改用户名能力缺失（D18） |
| POST /api/user/avatar | POST /api/user/avatar | ✅ | File 参数待补充 |
| PUT /api/user/password | PUT /api/user/password | ✅ | 新密码 6 位数字约束待补充（D3） |
| POST /api/categories | POST /api/categories | ✅ | type 枚举 0/1 → 1/2；多 icon/sortOrder |
| GET /api/categories | GET /api/categories | ✅ | 并入系统预设分类（userId=0） |
| PUT /api/categories/{id} | PUT /api/categories/{category_id} | ✅ | 全量覆盖 → 部分更新 |
| DELETE /api/categories/{id} | DELETE /api/categories/{category_id} | ✅ | 删除方式待定（D22） |
| GET /api/records | GET /api/records | ✅ | 参数待定稿（D4/D20）；软删过滤 |
| GET /api/records/{id} | （缺失，建议补充） | ⚠️ | D7 |
| POST /api/records | POST /api/records | ✅ | 入参多 type；日期校验 422（改进） |
| PUT /api/records/{id} | PUT /api/records/{record_id} | ✅ | 部分更新语义一致 |
| DELETE /api/records/{id} | DELETE /api/records/{record_id} | ✅ | 物理删除 → 软删除 |
| GET /api/statistics/monthly | GET /api/statistics/summary | ✅ | 缺省全量，可选 year/month（D25） |
| — | GET /api/statistics/trend | ➕ | 新增 |
| GET /api/statistics/category | GET /api/statistics/category | ✅ | type 默认 1 |
| GET /api/admin/users | GET /api/admin/users | ✅ | 参数待补充 |
| GET /api/admin/users/{id} | — | ❌ | D33 |
| DELETE /api/admin/users/{id} | — | ❌ | 以禁用替代（D33） |
| POST /api/admin/users/batch-delete | — | ❌ | D33 |
| GET /api/admin/records | — | ❌ | D33 |
| POST /api/admin/records/batch-delete | — | ❌ | D33 |
| GET /api/admin/statistics/overview | — | ❌ | D33 |
| — | PUT /api/admin/users/{user_id}/status | ➕ | 新增 |
| — | GET /api/admin/categories | ➕ | 新增 |
| — | GET/POST/PUT/DELETE /api/admin/faq[...] | ➕ | 新增 |
| POST /api/ai/sessions | POST /api/ai/sessions | ✅ | 请求体待补充（D34） |
| GET /api/ai/sessions | GET /api/ai/sessions | ✅ | 参数简化（D13） |
| PATCH /api/ai/sessions/{id} | — | ❌ | 重命名（D39） |
| DELETE /api/ai/sessions/{id} | DELETE /api/ai/sessions/{session_id} | ✅ | 软删除 |
| POST /api/ai/sessions/batch-delete | — | ❌ | D39 |
| GET /api/ai/sessions/{id}/messages | GET /api/ai/sessions/{session_id}/messages | ✅ | — |
| POST /api/ai/chat / chat/stream | POST /api/ai/chat（SSE 单端点） | ✅ | 端点合并（D36）；不再依赖外部 chatbot-server |
| POST /api/ai/analyze/expenses、budget | GET /api/ai/sessions/{id}/analysis | ✅ | POST 带参 → GET 会话维度（D37/D38） |
| GET /api/ai/faq/search、POST /api/ai/faq/rebuild | —（内部 faq_retriever + 管理端 CRUD） | ❌ | D39 |
| POST /api/ai/feedback | POST /api/ai/feedback | ✅ | rating 1-5 → like/dislike（D14） |
| GET /api/ai/admin/stats | — | ❌ | D39（若补须管理员权限） |
| — | GET /api/health | ➕ | 新增 |

> ✅ 对应；➕ FastAPI 新增；❌ Spring 有、FastAPI 无；⚠️ 需决策。

### C. 决策点清单

| # | 决策点 | 现状（桩） | Spring 行为 | 建议 |
|---|---|---|---|---|
| D1 | 表结构 | 复数新表 + 新列 | 单数旧表 | 建新表 + 存量数据平移（type 0/1→1/2，补 status=1） |
| D2 | 管理员校验 | `get_current_admin` TODO 直通 | 拦截器 403 | 查 `role=="admin"`，否则 403（**必做**） |
| D3 | 用户名/密码格式约束 | 无 | 2-20 中英文数字；6 位数字 | 补 pattern 校验 |
| D4 | 分页参数名/默认值 | 注释 pageSize、crud 默认 20 | page/size 默认 1/10 | 统一 page/size，默认 1/10 |
| D5 | 分页出参字段 | 仅 {records,total} | 另含 pages/current | 可补 pages |
| D6 | FAQ schema | 缺失 | 无对应 | 补 FaqCreate/FaqUpdate/FaqOut |
| D7 | 账单详情端点 | 缺失 | 有 | 建议补充（本文档已列） |
| D8 | 401 文案/用户存在性 | 统一「无效令牌」，不查库 | 三态文案 + 查库 | 保持现状，按状态码处理 |
| D9 | 禁用用户登录 | status 列新增 | 无 | 登录/接口校验 status=1，否则 403 |
| D10 | 金额类型 | float + gt=0 | Decimal + ≥0.01 | 可保持 float |
| D11 | 出参时间戳 | *Out 无时间戳 | VO 含时间戳 | 需要则补字段 |
| D12 | 写操作出参 | data=null | 回查 VO 返回 | 注册/登录/资料/头像/分类增改/账单增改统一回出对象 |
| D13 | AI 会话列表参数 | 无 | keyword/sort/order/page/size | 至少补 updated_at DESC 排序 |
| D14 | 反馈语义 | like/dislike | rating 1-5 | 保持新语义，前端同步 |
| D15 | AI 请求体 JSON 键名 | snake_case | camelCase | 补 camelCase 别名（双收） |
| D16 | OpenAPI 完整性 | 无 response_model | — | 补 response_model + query 声明 |
| D17 | 禁用用户调 🔐 接口 | 无校验 | 无 | get_current_user 后查 status，403 |
| D18 | 改用户名 | /update 无 username 字段 | PUT /info 改 username | 并入 UserUpdateRequest |
| D19 | 头像出参 | {"avatarUrl":""} | UserVO | {"avatarUrl": 新路径} |
| D20 | 分类列表参数/排序 | 无参数 | type 过滤 + create_time DESC | 补 type?；排序确认 |
| D21 | 系统预设分类权限 | userId=0 预设 | 无预设 | 预设仅管理员可改/删 |
| D22 | 删分类方式 | status 列可用 | 物理删除 | 物理删除对齐 Spring |
| D23 | 账单 type 与分类一致性 | 无校验 | type 由分类推断 | 校验 type == 分类.type |
| D24 | 删账单 | 软删 status=0 | 物理删除 | 保持软删 |
| D25 | summary 月度参数 | 无 | /monthly 必填 year/month | 可选 year/month |
| D26 | trend 参数/补零 | 无 | 无对应 | days=30 + 空日补 0 |
| D27 | 分类统计参数 | 无 | year/month 必填 | 可选 year/month，type 默认 1 |
| D28 | admin 用户列表出参 | UserOut 全量 | 列表 VO 恒不填 avatar | 保持全量 |
| D29 | 禁用管理员保护 | 无 | 不能删除管理员 | 禁用前校验目标非 admin |
| D30 | admin 分类含禁用项 | 全表 | 无 | 含 status=0 |
| D31 | admin FAQ 状态过滤 | status=1 | 无 | 管理端返回全部 |
| D32 | FAQ 删除方式 | 物理 | 无 | 软删 status=0 |
| D33 | Spring 管理端 6 个缺失端点 | 无 | 详情/删用户/批量删/全账单/批量删/概览 | 默认不补，如需对齐按需实现 |
| D34 | 新建会话请求体 | 无 | {"title"?} | 补可选 body {title?} |
| D35 | 消息列表异常行为 | 建议 404 | 兜底 [] | 404 会话不存在 |
| D36 | chat 单/双端点 | 仅 SSE | 非流式+流式 | 保持单 SSE |
| D37 | analysis 出参结构 | data={} | 两 POST 分列 | {"expense": ..., "budget": ...} |
| D38 | analysis 口径 | GET 会话维度 | POST 带参；expenses 含环比 | 环比保留 |
| D39 | AI 缺失能力 | 无 | 会话改名/批量删/FAQ API/管理统计 | 按需补 |
| D40 | LLM 未配置行为 | AGNES_API_KEY 空 | 无对应 | AI 端点 500 AI 服务未配置 |

### D. 实现清单与开发顺序

1. **基础设施**：执行建表/迁移 DDL；实现 `get_current_admin` 角色校验；`.env` 配置 `AGNES_API_KEY`。
2. **用户模块**（鉴权前置）：注册/登录业务；头像端点补 `file` 参数及校验链；资料/改密。
3. **分类模块**：列表（含预设）/增/改/删 + 归属校验。
4. **记账模块**：列表（参数定稿）/增/改/删（软删）/补详情；分类 JOIN 补 categoryName。
5. **统计模块**：summary / trend / category 聚合 SQL（范围查询走索引）。
6. **管理后台模块**：用户列表/状态切换/全量分类/FAQ CRUD。
7. **AI 模块**：`build_user_context`（当月统计+Top5 分类+近 10 条账单）→ LLM 客户端 → chat SSE / analysis / feedback → 会话消息落库。
8. **联调收尾**：全端点补 `response_model` 使 `/docs` 可作联调面板；前端拦截器按错误码表改造。
