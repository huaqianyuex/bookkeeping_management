# 个人记账本 API 接口文档（基于实际代码生成）

## 项目信息

| 项目 | 说明 |
|------|------|
| 基础地址 | `http://localhost:8080` |
| 数据格式 | JSON |
| 认证方式 | JWT Token（请求头 `Authorization: Bearer {token}`） |
| 框架 | Spring Boot 3.3.0 + MyBatis-Plus + Spring Security |

## 统一响应格式

### 标准响应体 `Result<T>`

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 200 成功 / 400 参数校验失败 / 401 未登录 / 500 业务异常 |
| message | String | 提示信息 |
| data | T | 返回数据，可为 null |

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {}
}
```

### 分页响应体（data 字段内的结构）

| 字段 | 类型 | 说明 |
|------|------|------|
| records | Array | 当前页数据列表 |
| total | long | 总记录数 |
| pages | long | 总页数 |
| current | long | 当前页码 |
| size | long | 每页条数 |

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "records": [],
    "total": 0,
    "pages": 0,
    "current": 1,
    "size": 10
  }
}
```

---

## 接口总览

| # | 模块 | 接口 | 方法 | 路径 | 需登录 |
|---|------|------|------|------|--------|
| 1 | 用户 | 注册 | POST | `/api/user/register` | 否 |
| 2 | 用户 | 登录 | POST | `/api/user/login` | 否 |
| 3 | 用户 | 个人信息 | GET | `/api/user/info` | 是 |
| 4 | 用户 | 修改密码 | PUT | `/api/user/password` | 是 |
| 5 | 分类 | 查询列表 | GET | `/api/categories` | 是 |
| 6 | 分类 | 新增 | POST | `/api/categories` | 是 |
| 7 | 分类 | 修改 | PUT | `/api/categories/{id}` | 是 |
| 8 | 分类 | 删除 | DELETE | `/api/categories/{id}` | 是 |
| 9 | 账单 | 分页查询 | GET | `/api/records` | 是 |
| 10 | 账单 | 查看详情 | GET | `/api/records/{id}` | 是 |
| 11 | 账单 | 新增 | POST | `/api/records` | 是 |
| 12 | 账单 | 修改 | PUT | `/api/records/{id}` | 是 |
| 13 | 账单 | 删除 | DELETE | `/api/records/{id}` | 是 |
| 14 | 统计 | 月度汇总 | GET | `/api/statistics/monthly` | 是 |
| 15 | 统计 | 分类统计 | GET | `/api/statistics/category` | 是 |
| 16 | AI 记账 | 自然语言记账 | POST | `/api/ai/bookkeeping` | 是 |
| 17 | AI 记账 | 修改 AI 记账记录 | PATCH | `/api/ai/bookkeeping/{id}` | 是 |
| 18 | AI 记账 | 删除 AI 记账记录 | DELETE | `/api/ai/bookkeeping/{id}` | 是 |

---

## 一、用户模块 `/api/user`

### 1.1 用户注册

- **方法**: `POST`
- **路径**: `/api/user/register`
- **登录要求**: 否

#### 请求体 `RegisterDTO`

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| username | String | 是 | 2-20 位，不能重复 |
| password | String | 是 | 8-16 位，必须包含大写字母、小写字母和数字 |

```json
{
  "username": "zhangsan",
  "password": "Abc12345"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "zhangsan"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 用户名已存在 | 500 | 用户名已存在 |
| 用户名为空 | 400 | 用户名不能为空 |
| 密码为空 | 400 | 密码不能为空 |
| 用户名长度不足 | 400 | 用户名需为2-20位中英文或数字组合 |
| 密码格式错误 | 400 | 密码需为8-16位且包含大小写字母和数字 |

---

### 1.2 用户登录

- **方法**: `POST`
- **路径**: `/api/user/login`
- **登录要求**: 否

#### 请求体 `LoginDTO`

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| username | String | 是 | 不能为空 |
| password | String | 是 | 不能为空 |

```json
{
  "username": "zhangsan",
  "password": "Abc12345"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "登录成功",
  "data": "eyJhbGciOiJIUzI1NiJ9.xxxxx"
}
```

`data` 为 JWT Token 字符串，前端需存入 `localStorage`，后续请求在 `Authorization` 头中使用。

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 用户未注册 | 500 | 用户未注册，请注册后登录 |
| 密码错误 | 500 | 密码错误 |

---

### 1.3 查看个人信息

- **方法**: `GET`
- **路径**: `/api/user/info`
- **登录要求**: 是
- **请求头**: `Authorization: Bearer {token}`

#### 响应 `UserVO`

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "createTime": "2026-05-12T11:30:00",
    "updateTime": "2026-05-12T11:30:00"
  }
}
```

#### UserVO 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 用户ID |
| username | String | 用户名 |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |

#### 错误场景

| 场景 | HTTP 状态码 | code | message |
|------|-------------|------|---------|
| 未登录 | 401 | 401 | 未登录 |
| Token 无效/过期 | 401 | 401 | token无效或已过期 |

---

### 1.4 修改密码

- **方法**: `PUT`
- **路径**: `/api/user/password`
- **登录要求**: 是
- **请求头**: `Authorization: Bearer {token}`

#### 请求体 `PasswordUpdateDTO`

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| oldPassword | String | 是 | 不能为空 |
| newPassword | String | 是 | 8-16 位，必须包含大写字母、小写字母和数字 |

```json
{
  "oldPassword": "Abc12345",
  "newPassword": "Xyz78901"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "修改成功",
  "data": null
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 原密码错误 | 500 | 密码错误 |
| 新密码格式错误 | 400 | 密码需为8-16位且包含大小写字母和数字 |

---

## 二、分类模块 `/api/categories`

> 所有分类接口需要 JWT 登录。数据按用户隔离。

### 2.1 查询分类列表

- **方法**: `GET`
- **路径**: `/api/categories`
- **登录要求**: 是

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | Integer | 否 | 0=支出 / 1=收入，不传查全部 |

#### 响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": [
    {
      "id": 1,
      "name": "餐饮",
      "type": 0,
      "userId": 1,
      "createTime": "2026-05-12T11:30:00",
      "updateTime": "2026-05-12T11:30:00"
    }
  ]
}
```

#### Category 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 分类ID |
| name | String | 分类名称 |
| type | Integer | 0=支出 / 1=收入 |
| userId | Long | 所属用户ID |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |

---

### 2.2 新增分类

- **方法**: `POST`
- **路径**: `/api/categories`
- **登录要求**: 是

#### 请求体 `CategoryDTO`

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| name | String | 是 | 不能为空 |
| type | Integer | 是 | 不能为空，0=支出 / 1=收入 |

```json
{
  "name": "餐饮",
  "type": 0
}
```

#### 响应

```json
{
  "code": 200,
  "message": "新增成功",
  "data": {
    "id": 13,
    "name": "餐饮",
    "type": 0,
    "userId": 1,
    "createTime": "2026-05-12T11:30:00",
    "updateTime": "2026-05-12T11:30:00"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 名称为空 | 400 | 分类名称不能为空 |
| 类型为空 | 400 | 分类类型不能为空 |

---

### 2.3 修改分类

- **方法**: `PUT`
- **路径**: `/api/categories/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 分类ID |

#### 请求体 `CategoryDTO`

```json
{
  "name": "吃饭",
  "type": 0
}
```

#### 响应

```json
{
  "code": 200,
  "message": "修改成功",
  "data": {
    "id": 1,
    "name": "吃饭",
    "type": 0,
    "userId": 1,
    "createTime": "2026-05-12T11:30:00",
    "updateTime": "2026-05-12T11:35:00"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 分类不存在或不属于当前用户 | 500 | 分类不存在 |

---

### 2.4 删除分类

- **方法**: `DELETE`
- **路径**: `/api/categories/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 分类ID |

#### 响应

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 分类不存在或不属于当前用户 | 500 | 分类不存在 |

> 删除分类时，关联的账单记录不会被删除（外键未设置级联删除，账单的 `category_id` 会保留原值）。

---

## 三、账单模块 `/api/records`

### 3.1 分页查询账单

- **方法**: `GET`
- **路径**: `/api/records`
- **登录要求**: 是

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | Integer | 否 | 页码，默认 1 |
| size | Integer | 否 | 每页条数，默认 10 |
| categoryId | Long | 否 | 按分类筛选 |
| month | String | 否 | 按月份筛选，格式 `"2026-05"` |

#### 响应（分页格式）

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "records": [
      {
        "id": 1,
        "userId": 1,
        "categoryId": 1,
        "categoryName": "餐饮",
        "categoryType": 0,
        "amount": 35.50,
        "remark": "午饭",
        "recordDate": "2026-05-12",
        "createTime": "2026-05-12T12:00:00",
        "updateTime": "2026-05-12T12:00:00"
      }
    ],
    "total": 50,
    "pages": 5,
    "current": 1,
    "size": 10
  }
}
```

#### RecordVO 结构

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| id | Long | record 表 | 记录ID |
| userId | Long | record 表 | 用户ID |
| categoryId | Long | record 表 | 分类ID |
| categoryName | String | category 表（联表） | 分类名称 |
| categoryType | Integer | category 表（联表） | 0=支出 / 1=收入 |
| amount | BigDecimal | record 表 | 金额 |
| remark | String | record 表 | 备注，可为 null |
| recordDate | LocalDate | record 表 | 记录日期 |
| createTime | LocalDateTime | record 表 | 创建时间 |
| updateTime | LocalDateTime | record 表 | 更新时间 |

---

### 3.2 查看账单详情

- **方法**: `GET`
- **路径**: `/api/records/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 记录ID |

#### 响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "userId": 1,
    "categoryId": 1,
    "categoryName": "餐饮",
    "categoryType": 0,
    "amount": 35.50,
    "remark": "午饭",
    "recordDate": "2026-05-12",
    "createTime": "2026-05-12T12:00:00",
    "updateTime": "2026-05-12T12:00:00"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 记录不存在或不属于当前用户 | 500 | 记录不存在 |

---

### 3.3 新增账单

- **方法**: `POST`
- **路径**: `/api/records`
- **登录要求**: 是

#### 请求体 `RecordDTO`

| 字段 | 类型 | 必填 | 校验规则 |
|------|------|------|----------|
| categoryId | Long | 是 | 必须存在且属于当前用户 |
| amount | BigDecimal | 是 | 必须大于 0 |
| remark | String | 否 | 无限制 |
| recordDate | String | 是 | 格式 `yyyy-MM-dd` |

```json
{
  "categoryId": 1,
  "amount": 35.50,
  "remark": "午饭",
  "recordDate": "2026-05-12"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "新增成功",
  "data": {
    "id": 51,
    "userId": 1,
    "categoryId": 1,
    "categoryName": "餐饮",
    "categoryType": 0,
    "amount": 35.50,
    "remark": "午饭",
    "recordDate": "2026-05-12",
    "createTime": "2026-05-12T12:00:00",
    "updateTime": "2026-05-12T12:00:00"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 分类不存在或不属于当前用户 | 500 | 分类不存在 |
| 分类为空 | 400 | 分类不能为空 |
| 金额为空 | 400 | 金额不能为空 |
| 金额不大于0 | 400 | 金额必须大于0 |
| 日期为空 | 400 | 日期不能为空 |

---

### 3.4 修改账单

- **方法**: `PUT`
- **路径**: `/api/records/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 记录ID |

#### 请求体

同 3.3 RecordDTO。

```json
{
  "categoryId": 1,
  "amount": 40.00,
  "remark": "午饭加饮料",
  "recordDate": "2026-05-12"
}
```

#### 响应

```json
{
  "code": 200,
  "message": "修改成功",
  "data": {
    "id": 1,
    "userId": 1,
    "categoryId": 1,
    "categoryName": "餐饮",
    "categoryType": 0,
    "amount": 40.00,
    "remark": "午饭加饮料",
    "recordDate": "2026-05-12",
    "createTime": "2026-05-12T12:00:00",
    "updateTime": "2026-05-12T12:05:00"
  }
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 记录不存在或不属于当前用户 | 500 | 记录不存在 |
| 分类不存在或不属于当前用户 | 500 | 分类不存在 |

---

### 3.5 删除账单

- **方法**: `DELETE`
- **路径**: `/api/records/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 记录ID |

#### 响应

```json
{
  "code": 200,
  "message": "删除成功",
  "data": null
}
```

#### 错误场景

| 场景 | code | message |
|------|------|---------|
| 记录不存在或不属于当前用户 | 500 | 记录不存在 |

---

## 四、统计模块 `/api/statistics`

### 4.1 月度收支汇总

- **方法**: `GET`
- **路径**: `/api/statistics/monthly`
- **登录要求**: 是

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| year | Integer | 是 | 年份，如 2026 |
| month | Integer | 是 | 月份，如 5 |

#### SQL 逻辑

```sql
SELECT
    #{year} AS year,
    #{month} AS month,
    COALESCE(SUM(CASE WHEN c.type = 1 THEN r.amount ELSE 0 END), 0) AS totalIncome,
    COALESCE(SUM(CASE WHEN c.type = 0 THEN r.amount ELSE 0 END), 0) AS totalExpense
FROM record r
LEFT JOIN category c ON r.category_id = c.id
WHERE r.user_id = #{userId}
  AND YEAR(r.record_date) = #{year}
  AND MONTH(r.record_date) = #{month}
```

#### 响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "year": 2026,
    "month": 5,
    "totalIncome": 8000.00,
    "totalExpense": 3500.00,
    "balance": 4500.00
  }
}
```

`balance` = `totalIncome - totalExpense`，在 Java 层计算。

#### MonthlyStatisticsVO 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| year | Integer | 年份 |
| month | Integer | 月份 |
| totalIncome | BigDecimal | 总收入 |
| totalExpense | BigDecimal | 总支出 |
| balance | BigDecimal | 结余 |

---

### 4.2 分类统计

- **方法**: `GET`
- **路径**: `/api/statistics/category`
- **登录要求**: 是

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| year | Integer | 是 | 年份 |
| month | Integer | 是 | 月份 |
| type | Integer | 否 | 0=支出 / 1=收入，默认 0 |

#### SQL 逻辑

```sql
SELECT
    c.id AS categoryId,
    c.name AS categoryName,
    COALESCE(SUM(r.amount), 0) AS amount
FROM record r
LEFT JOIN category c ON r.category_id = c.id
WHERE r.user_id = #{userId}
  AND YEAR(r.record_date) = #{year}
  AND MONTH(r.record_date) = #{month}
  AND c.type = #{type}
GROUP BY c.id, c.name
ORDER BY amount DESC
```

`percentage` 在 Java 层计算：`amount / 分类总金额 * 100`，保留一位小数。

#### 响应

```json
{
  "code": 200,
  "message": "操作成功",
  "data": [
    {
      "categoryId": 1,
      "categoryName": "餐饮",
      "amount": 1200.00,
      "percentage": 34.2
    },
    {
      "categoryId": 2,
      "categoryName": "交通",
      "amount": 800.00,
      "percentage": 22.8
    }
  ]
}
```

#### CategoryStatisticsVO 结构

| 字段 | 类型 | 说明 |
|------|------|------|
| categoryId | Long | 分类ID |
| categoryName | String | 分类名称 |
| amount | BigDecimal | 该分类下总金额 |
| percentage | Double | 占比（%） |

---

## 五、AI 自然语言记账模块 `/api/ai/bookkeeping`

> **新增模块**：本文第一～四章为存量 Spring Boot 接口，本章为新增能力（FastAPI 侧实现）。
> 用户发一条口语化消息（"我今天花79块吃了一顿烤肉"），服务端做语义解析 → 字段归一化与校验 → 写入 `record` 表 → 回显确认信息；缺金额时追问，非消费类消息不处理。
>
> ⚠️ **响应格式例外（重要）**：本模块挂在 `/api/ai/**` 下，返回**裸 JSON，不套 `code / message / data`**；业务错误统一为 **HTTP 200 + `{"error":"中文提示"}`**。这与本文其他接口的 `Result` 包装不同，原因是前端对 `/api/ai/**` 的响应不读 `code` 字段（沿用既有 AI 网关逻辑）。详见「十、错误码汇总」的补充说明。
>
> 更细的契约与解析算法见 `docs/fastapi-backend/05-AI接口规范.md` §6 与 `06-AI模块设计.md` §11；本章可独立阅读。

### 5.0 处理流程与 `action` 枚举

```
用户消息
  → LLM 语义解析（intent + items[]）
  → 归一化 + 逐条校验（金额 / 日期 / 分类）
  → 分支：created（写 record） / clarify（追问） / ignored（不处理） / duplicate（幂等）
  → created 时回显：金额、类别、日期、备注、记录 ID
```

响应顶层 `action` 字段决定前端如何渲染：

| action | 含义 | 是否写 `record` 表 | 是否写 `ai_bookkeeping_logs` |
|--------|------|-------------------|------------------------------|
| `created` | 已入账（可能多笔） | 是 | 是（`action='created'`） |
| `clarify` | 信息不全，需要追问 | 否 | 是（`status=0` 草稿） |
| `ignored` | 非消费类消息 | 否 | 是（`action='ignored'`） |
| `duplicate` | 命中幂等，未重复入账 | 否 | 是（`action='duplicate'`） |

公共约定：

| 项 | 取值 |
|------|------|
| 时区 | 固定 `Asia/Shanghai`，不依赖服务器本地时区 |
| 单条上限 | 一条消息最多识别 **10 笔**，超出报错 |
| 文本上限 | `message` 1–500 字 |
| 事务 | 多笔记录在同一事务内写入，任一项异常整体回滚 |
| 审计 | 每次调用（含 clarify / ignored / duplicate）都写一条 `ai_bookkeeping_logs` |

---

### 5.1 自然语言记账

- **方法**: `POST`
- **路径**: `/api/ai/bookkeeping`
- **登录要求**: 是

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | String | 是 | 原始口语化文本，1–500 字 |
| sessionId | String | 否 | AI 会话 ID；传入时把消息写入会话，并维护「最近一笔」上下文 |
| clientMsgId | String | 否 | 客户端生成的 UUID，**强幂等键**；重发同一条消息必须带同一个值 |
| draftId | Long | 否 | 追问续写：把本次内容补进指定草稿 |
| dryRun | Boolean | 否（默认 false） | true = 只解析不入账，返回预览 |
| force | Boolean | 否（默认 false） | true = 跳过 5 分钟去重窗口，强制再记一笔 |
| now | String | 否 | ISO datetime，覆盖服务端"今天"，仅联调用 |

```json
{
  "sessionId": "session_1725969000000_ab12cd34x",
  "message": "我今天花79块吃了一顿烤肉",
  "clientMsgId": "8f2c1a10-4c7e-4a52-9f3b-2d6e0c9a7b41"
}
```

#### 响应（`action=created`）

```json
{
  "action": "created",
  "requestId": "bk_1725969000123_x1y2z3",
  "records": [
    {
      "id": 128,
      "amount": 79.00,
      "type": 1,
      "categoryId": 3,
      "categoryName": "餐饮",
      "recordDate": "2026-09-10",
      "remark": "烤肉"
    }
  ],
  "totalAmount": 79.00,
  "echo": "已记下：餐饮 ¥79.00 · 今天(2026-09-10) · 备注「烤肉」· 记录 #128\n回复「改成45块」可修改，回复「删掉」可撤销。",
  "warnings": [],
  "errors": [],
  "sessionId": "session_1725969000000_ab12cd34x",
  "messageId": "msg_1725969000456_q8w7e6"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| records[].type | Integer | 1=支出 / 2=收入（对应 `record.type`） |
| records[].amount | BigDecimal | 已四舍五入到 2 位小数 |
| warnings | Array | 兜底提示，如「未识别到明确分类，已归入「其他」」 |
| errors | Array | 本次未入账的条目及原因；部分成功时非空 |
| echo | String | 服务端格式化好的回显文案，前端可直接渲染 |

#### 响应（`action=clarify`，缺金额或金额无法识别）

```json
{
  "action": "clarify",
  "requestId": "bk_1725969000789_a1b2c3",
  "draftId": 1291,
  "question": "这笔消费的金额是多少？比如「35元」。",
  "missing": ["amount"],
  "preview": {
    "items": [
      {
        "amount": null,
        "categoryName": "餐饮",
        "categoryId": 3,
        "date": "2026-09-10",
        "dateExpr": "今天",
        "remark": "吃了顿烤肉",
        "confidence": 0.58
      }
    ]
  },
  "records": []
}
```

客户端下一步：携带 `draftId` + 用户补充内容再次调用本接口。草稿有效期 **30 分钟**，过期返回错误。

#### 响应（`action=ignored`，非消费类）

```json
{
  "action": "ignored",
  "requestId": "bk_1725969000999_m4n5p6",
  "reason": "not_expense",
  "echo": "这不像一笔消费记录，我没有记账。想记账可以说「今天打车花了18块」。",
  "records": []
}
```

| reason | 场景 |
|--------|------|
| `not_expense` | 闲聊、问候等与消费无关 |
| `query` | 查询类（"这个月花了多少"），前端应转统计/分析接口 |
| `income_unsupported` | 识别为收入但用户未开启收入记账 |
| `too_ambiguous` | 语义过于模糊，且提炼不出可追问的点 |
| `no_recent_record` | 说"删掉刚那笔"但找不到最近记录 |

#### 响应（`action=duplicate`，命中幂等）

```json
{
  "action": "duplicate",
  "requestId": "bk_1725969000123_x1y2z3",
  "originRequestId": "bk_1725968999000_p0o9i8",
  "records": [
    { "id": 128, "amount": 79.00, "categoryName": "餐饮", "recordDate": "2026-09-10", "remark": "烤肉" }
  ],
  "echo": "这条我已经记过啦（#128 · 餐饮 ¥79.00），没有重复记账。",
  "hint": "如果确实要再记一笔，请重新发送并带上 force=true。"
}
```

#### 语义解析规则

**金额归一化**（支持中文数字、小数、"块/元"等写法）：

| 输入片段 | 归一化结果 |
|----------|-----------|
| `79` / `79块` / `79元` / `79块钱` / `¥79` | `79.00` |
| `79.5` / `79.50元` | `79.50` |
| `1,299` | `1299.00` |
| `七十九块` | `79.00` |
| `三十五块五` / `35块5` | `35.50` |
| `两百` / `二百` | `200.00` |
| `1万2` / `1万2千` | `12000.00` |
| `柒拾玖元整` | `79.00` |
| `0` / `-5` / `100000000` | 非法，不入账 |
| `花了点钱` / `没多少` | 无法识别 → 触发 `clarify` |

金额必须 `> 0` 且 `≤ 99999999.99`（`DECIMAL(10,2)`），保留两位小数（四舍五入）。**无法识别时不猜测、不取默认值，一律追问。**

**日期归一化**（相对时间转具体日期，基准 `today = 2026-09-10` 周四）：

| 表达 | 结果 |
|------|------|
| 今天 / 今日 | `2026-09-10` |
| 昨天 / 前天 / 大前天 | `2026-09-09` / `09-08` / `09-07` |
| 本周三 / 这周三 | `2026-09-09` |
| 上周三 | `2026-09-02`（上一自然周） |
| 上个月 / 上月 | `2026-08-01` |
| 3月5号 | `2026-03-05`（未指定年份且晚于今天 → 年份 -1） |
| 12月25号 | `2025-12-25`（晚于今天 → 去年） |
| 5号（无月份） | 本月 5 号；晚于今天则上月同日 |
| 3天前 / N天前 | `today - N` |
| 无时间词 / 无法识别 | `today` + warning |

**分类解析**（按序匹配，首次命中即返回）：

1. 归一化：去空格、繁转简、大写转小写；
2. 精确匹配：用户自定义分类（`user_id = 当前用户`）优先于系统预设（`user_id = 0`），且 `type` 必须一致；
3. 别名表匹配：吃饭/午饭/外卖/烤肉 → 餐饮；打车/地铁/加油 → 交通；买衣服/淘宝/超市 → 购物；电影/KTV/旅游 → 娱乐；房租/水电/物业 → 住房；看病/买药 → 医疗；学费/买书 → 教育；话费/会员 → 通讯；
4. 模糊包含匹配（唯一命中才采用）；
5. 历史行为：该用户近 90 天相同备注用过 ≥3 次的分类；
6. **兜底「其他」**：以上都失败时归入系统分类「其他」，并**必须**在 `warnings` 中说明。

> ⚠️ 注意两个 `type` 语义不同：`category.type` 是 **0=支出 / 1=收入**，`record.type` 是 **1=支出 / 2=收入**，转换时勿混淆。

#### 幂等规则

1. **强幂等**：`clientMsgId` 非空 → 查唯一键 `(user_id, client_msg_id)`，命中直接返回首次结果（`duplicate`），永不过期。
2. **弱幂等**：无 `clientMsgId` 时用 `SHA256(user_id + "|" + 归一化(message))` 在 **5 分钟窗口**内查重，命中返回 `duplicate`。归一化 = 去首尾空白、全角转半角、统一小写、压缩连续空白（**不动数字**）。
3. **并发安全**：先 INSERT 日志（唯一键），再写 `record`；捕获唯一键冲突后回查首次结果。**禁止"先 SELECT 判断再 INSERT"**。
4. `force=true` 只跳过第 2 条，不跳过第 1 条。
5. `dryRun=true` 不参与去重判定，也不产生可被去重的日志。

#### 错误场景

| 场景 | 响应（`error` 字段） |
|------|---------------------|
| 缺少 `message` 或为空 | `缺少参数: message` |
| `message` 超过 500 字 | `消息过长，最多 500 字` |
| `sessionId` 不存在 / 不属于当前用户 / 已删除 | `会话不存在` |
| `draftId` 不存在、已处理或超过 30 分钟 | `草稿已过期，请重新描述这笔消费` |
| 解析出的条目超过 10 笔 | `一次最多识别 10 笔消费，请分开发送` |
| LLM 调用失败或输出无法校验 | `记账解析失败，请换个说法再试` |

---

### 5.2 修改刚记下的记录

- **方法**: `PATCH`
- **路径**: `/api/ai/bookkeeping/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 记录ID（`record.id`） |

#### 请求体

至少一项非空。**显式字段与 `message` 都给时，以显式字段为准。**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| amount | BigDecimal | 否 | 大于 0，≤ 99999999.99 |
| categoryId | Long | 否 | 必须属于当前用户或系统预设，且 `type` 与原记录一致 |
| recordDate | String | 否 | `yyyy-MM-dd` |
| remark | String | 否 | ≤ 200 字，超出截断 |
| message | String | 否 | 自然语言修指令，如"改成45块5，备注AA" |

```json
{ "message": "改成45块5" }
```

#### 响应

```json
{
  "success": true,
  "record": {
    "id": 128,
    "amount": 45.50,
    "type": 1,
    "categoryId": 3,
    "categoryName": "餐饮",
    "recordDate": "2026-09-10",
    "remark": "烤肉"
  },
  "changes": { "amount": { "from": 79.00, "to": 45.50 } },
  "echo": "已更新 #128：餐饮 ¥45.50（原 ¥79.00）· 2026-09-10 · 备注「烤肉」"
}
```

#### 错误场景

| 场景 | 响应 |
|------|------|
| 记录不存在、不属于当前用户或已删除 | `{"error":"记录不存在"}` |
| 字段非法（金额非正、分类不存在等） | `{"error":"<具体中文提示>"}` |

每次修改在 `ai_bookkeeping_logs` 追加一条 `action='amend'`，`parent_id` 指向原记账日志，用于回溯"AI 记错 → 用户改对"的纠错样本。

---

### 5.3 删除刚记下的记录

- **方法**: `DELETE`
- **路径**: `/api/ai/bookkeeping/{id}`
- **登录要求**: 是

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| id | Long | 记录ID |

#### 响应

```json
{
  "success": true,
  "echo": "已删除 #128（餐饮 ¥79.00 · 2026-09-10）"
}
```

语义与 `DELETE /api/records/{id}` 一致：**软删除**（`record.status = 0`）。同时在 `ai_bookkeeping_logs` 追加 `action='delete'` 日志，原日志 `status` 置为 2（已回滚）。

#### 错误场景

| 场景 | 响应 |
|------|------|
| 记录不存在、不属于当前用户或已删除 | `{"error":"记录不存在"}` |

---

### 5.4 「最近一笔」的解析规则

用户说"改成45块""删掉刚那笔""刚才记错了"时，按下表优先级定位目标记录：

| 优先级 | 来源 | 规则 |
|--------|------|------|
| 1 | 显式 ID | 文本中出现 `#128` 或"编号128" → 直接定位 |
| 2 | 当前会话最近一笔 | 该会话内最近一条 `action='created'` 且未回滚的日志 |
| 3 | 用户级最近一笔 | 不限会话，但限定 **30 分钟内** |
| 4 | 无 | 返回 `action=ignored`、`reason=no_recent_record`，提示用户带编号 |

> 不需要给 `sessions` 表加字段，全部通过 `ai_bookkeeping_logs` 反查。

---

### 5.5 回显文案模板

单笔：

```
已记下：餐饮 ¥79.00 · 今天(2026-09-10) · 备注「烤肉」· 记录 #128
```

多笔：

```
已记下 2 笔：
1) 餐饮 ¥32.00 · 2026-09-10 · 买菜（#128）
2) 交通 ¥18.00 · 2026-09-10 · 打车（#129）
合计 ¥50.00
```

尾部固定追加：`回复「改成45块」可修改，回复「删掉」可撤销。`

存在 `warnings` 时首行后插入：`⚠️ 未识别到明确分类，已归入「其他」，可回复「改成餐饮」调整。`

金额格式由服务端统一输出为 `¥` + 千分位 + 两位小数，前端不做二次处理。

---

### 5.6 边界用例清单（联调必测）

| # | 输入 | 期望 |
|---|------|------|
| 1 | "我今天花79块吃了一顿烤肉" | created，餐饮 ¥79.00，日期=今天，备注=烤肉 |
| 2 | "昨天打车18，买菜32块5" | created ×2，按原文顺序，日期=昨天 |
| 3 | "花了点钱吃饭" | clarify，`missing=["amount"]`，不做任何猜测 |
| 4 | "你好啊" | ignored，`reason=not_expense` |
| 5 | "这个月花了多少" | ignored，`reason=query` |
| 6 | 同一条消息 5 秒内重发两次 | 第二次 duplicate，`record` 不新增 |
| 7 | 带同一 `clientMsgId` 隔天重发 | duplicate（强幂等不过期） |
| 8 | "七十九块"/"79元"/"79.5"/"1,299"/"1万2" | 分别归一化为 79.00 / 79.00 / 79.50 / 1299.00 / 12000.00 |
| 9 | 无时间词 | 日期 = 今天 |
| 10 | "上周三买的鞋320" | 日期 = 上一个自然周的周三 |
| 11 | "3月5号买了本书89"（今天 2026-09-10） | 日期 = 2026-03-05 |
| 12 | "买了个奇怪的东西 45" | created，分类「其他」+ warning |
| 13 | 金额为 0 或负数 | 该条进 `errors`，不落库；全部非法 → clarify |
| 14 | 金额 > 99999999.99 | 该条进 `errors`，不落库 |
| 15 | "工资到账8000" | 按 `type=2`（收入）入账；无收入分类时 clarify |
| 16 | 一条消息含 11 笔 | `一次最多识别 10 笔消费，请分开发送` |

---

## 六、数据库设计

### 建表语句

```sql
CREATE TABLE user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(100) NOT NULL COMMENT '密码（BCrypt 加密）',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username)
) COMMENT '用户表';

CREATE TABLE category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '分类ID',
    name VARCHAR(50) NOT NULL COMMENT '分类名称',
    type TINYINT NOT NULL COMMENT '类型：0=支出，1=收入',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id)
) COMMENT '分类表';

CREATE TABLE record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    category_id BIGINT NOT NULL COMMENT '分类ID',
    amount DECIMAL(10, 2) NOT NULL COMMENT '金额',
    remark VARCHAR(200) DEFAULT NULL COMMENT '备注',
    record_date DATE NOT NULL COMMENT '记录日期',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_date (user_id, record_date),
    INDEX idx_category (category_id)
) COMMENT '账单记录表';

-- 自然语言记账日志（第五章 AI 记账模块使用）
CREATE TABLE ai_bookkeeping_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    request_id VARCHAR(64) NOT NULL COMMENT 'bk_{毫秒}_{随机}，对外 requestId',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(64) DEFAULT NULL COMMENT 'AI 会话ID',
    message_id VARCHAR(64) DEFAULT NULL COMMENT '关联消息ID',
    client_msg_id VARCHAR(64) DEFAULT NULL COMMENT '客户端幂等键（UUID）',
    dedup_hash CHAR(64) NOT NULL COMMENT 'SHA256(user_id|归一化message)，弱幂等',
    raw_text VARCHAR(500) NOT NULL COMMENT '用户原始消息',
    intent VARCHAR(20) NOT NULL COMMENT 'bookkeeping/amend/delete/query/chitchat',
    action VARCHAR(20) NOT NULL COMMENT 'created/clarify/ignored/duplicate/preview/amend/delete/error',
    parse_json JSON DEFAULT NULL COMMENT 'LLM 原始解析结果',
    record_ids JSON DEFAULT NULL COMMENT '入账的 record.id 数组，如 [128,129]',
    error_msg VARCHAR(200) DEFAULT NULL COMMENT '失败原因（不回显给前端）',
    status TINYINT NOT NULL DEFAULT 1 COMMENT '0=草稿待追问 1=已处理 2=已回滚',
    parent_id BIGINT DEFAULT NULL COMMENT '追问续写/修改删除时指向的原日志ID',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_request_id (request_id),
    UNIQUE KEY uk_client_msg (user_id, client_msg_id),
    INDEX idx_dedup (user_id, dedup_hash, create_time),
    INDEX idx_user_recent (user_id, create_time),
    INDEX idx_session (session_id, id)
) COMMENT 'AI自然语言记账日志（幂等/草稿/审计）';
```

> `client_msg_id` 允许为 NULL，MySQL 唯一索引对多行 NULL 不冲突 —— 这正是"未传幂等键时不触发强幂等"的预期行为，勿改为 NOT NULL。

### 关系说明

- `category.user_id` → `user.id`（多对一，一个用户有多个分类）
- `record.user_id` → `user.id`（多对一，一个用户有多条记录）
- `record.category_id` → `category.id`（多对一，一个分类下有多条记录）
- `ai_bookkeeping_logs.user_id` → `user.id`（多对一，记录每次 AI 记账请求）
- `ai_bookkeeping_logs.record_ids` → `record.id`（JSON 数组，一笔请求可对应多条记录）
- `ai_bookkeeping_logs.parent_id` → `ai_bookkeeping_logs.id`（自关联，追问续写与修改/删除回溯）
- 所有数据按 `user_id` 隔离，用户只能操作自己的数据

---

## 七、DTO / VO 汇总

### 请求 DTO

| DTO | 字段 | 类型 | 校验规则 |
|-----|------|------|----------|
| RegisterDTO | username | String | `@NotBlank` `@Size(min=2, max=20)` |
| RegisterDTO | password | String | `@NotBlank` `@Pattern(8-16位，含大小写+数字)` |
| LoginDTO | username | String | `@NotBlank` |
| LoginDTO | password | String | `@NotBlank` |
| PasswordUpdateDTO | oldPassword | String | `@NotBlank` |
| PasswordUpdateDTO | newPassword | String | `@NotBlank` `@Pattern(8-16位，含大小写+数字)` |
| CategoryDTO | name | String | `@NotBlank` |
| CategoryDTO | type | Integer | `@NotNull`（0=支出 / 1=收入） |
| RecordDTO | categoryId | Long | `@NotNull` |
| RecordDTO | amount | BigDecimal | `@NotNull` `@DecimalMin("0.01")` |
| RecordDTO | remark | String | 无校验（可选） |
| RecordDTO | recordDate | String | `@NotNull`（格式 `yyyy-MM-dd`） |
| BookkeepingRequest | message | String | `@NotBlank` `@Size(max=500)` |
| BookkeepingRequest | sessionId | String | 可选，需归属当前用户 |
| BookkeepingRequest | clientMsgId | String | 可选，强幂等键 |
| BookkeepingRequest | draftId | Long | 可选，追问续写 |
| BookkeepingRequest | dryRun | Boolean | 可选，默认 false |
| BookkeepingRequest | force | Boolean | 可选，默认 false |
| BookkeepingAmendRequest | amount | BigDecimal | 可选，`@DecimalMin("0.01")` |
| BookkeepingAmendRequest | categoryId | Long | 可选，需归属当前用户 |
| BookkeepingAmendRequest | recordDate | String | 可选，`yyyy-MM-dd` |
| BookkeepingAmendRequest | remark | String | 可选，`@Size(max=200)` |
| BookkeepingAmendRequest | message | String | 可选，自然语言修指令 |

### 响应 VO

| VO | 字段 |
|----|------|
| UserVO | id, username, createTime, updateTime |
| RecordVO | id, userId, categoryId, categoryName, categoryType, amount, remark, recordDate, createTime, updateTime |
| MonthlyStatisticsVO | year, month, totalIncome, totalExpense, balance |
| CategoryStatisticsVO | categoryId, categoryName, amount, percentage |
| BookkeepingResult | action, requestId, records[], totalAmount, echo, warnings, errors |
| BookkeepingRecordVO | id, amount, type, categoryId, categoryName, recordDate, remark |
| BookkeepingAmendResult | success, record, changes, echo |

---

## 八、JWT 认证说明

1. 登录成功后返回 Token，格式为 JWT 字符串
2. 前端将 Token 存入 `localStorage`
3. 后续请求在 `Authorization` 请求头中携带：`Bearer {token}`
4. Token 有效期：24 小时
5. 拦截器拦截 `/api/**` 路径（登录和注册接口除外）
6. 拦截器将解析出的 `userId` 存入 `UserContext` 线程变量，供 Controller 和 Service 使用

### 未登录 / Token 无效时的响应

```json
{
  "code": 401,
  "message": "未登录",
  "data": null
}
```

```json
{
  "code": 401,
  "message": "token无效或已过期",
  "data": null
}
```

---

## 九、密码安全机制

### 加密算法

使用 Spring Security 的 `BCryptPasswordEncoder`（strength = 10，即约 2^10 = 1024 轮迭代哈希），配置类位于 `config/PasswordConfig.java`。

### 盐值策略

BCrypt **内置随机盐值**机制，无需单独的 `salt` 字段：

1. 注册/修改密码时，`passwordEncoder.encode(明文)` 自动生成随机盐值
2. 每个密码 hash 自动包含独立 salt，存储格式为 `$2a$10$<salt><hash>`
3. 验证时，`passwordEncoder.matches(明文, 数据库hash)` 自动从 hash 中提取 salt 进行比对
4. 相同明文密码每次加密结果不同（因为 salt 随机生成），有效防止彩虹表攻击

### 存储格式

| 项目 | 说明 |
|------|------|
| 数据库字段 | `user.password VARCHAR(100)` |
| hash 长度 | 60 字符（`$2a$10$` 前缀 7 位 + salt 22 位 + hash 31 位） |
| 存储内容 | 仅存储 BCrypt hash，不单独存储 salt |

### 密码复杂度要求

| 规则 | 说明 |
|------|------|
| 长度 | 8-16 位 |
| 必须包含 | 大写字母、小写字母、数字 |
| 正则表达式 | `^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)[A-Za-z\\d]{8,16}$` |

### 认证流程

```
注册: 明文密码 → BCrypt.encode(明文) → 生成含salt的hash → 存入数据库
登录: 明文密码 + 数据库hash → BCrypt.matches(明文, hash) → 验证通过/失败
修改: 旧密码验证 → 新密码 encode → 更新数据库hash
```

---

## 十、错误码汇总

| code | HTTP 状态码 | 说明 |
|------|-------------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 参数校验失败（`@Valid` 触发的验证错误） |
| 401 | 401 | 未登录或 Token 无效 |
| 500 | 500 | 业务异常（用户名重复、密码错误、数据不存在等） |

### AI 记账模块的错误形态（例外）

第五章的 `/api/ai/bookkeeping/**` **不遵循上表**：一律 **HTTP 200 + 裸 JSON**，业务错误放在响应体的 `error` 字段中，不套 `code / message / data`。

```json
{ "error": "会话不存在" }
```

| HTTP | 说明 |
|------|------|
| 401 | 未登录或 Token 无效（仍由统一鉴权拦截，同第八章） |
| 200 | 其余全部情况；成功看 `action`，失败看 `error` |

幂等命中不算错误，以 `action=duplicate` 返回（见 5.1）。

---

## 十一、项目目录结构

```
backend/
├── pom.xml
└── src/main/java/com/example/test_backend/
    ├── TestBackendApplication.java
    ├── common/
    │   ├── Result.java                # 统一响应封装
    │   ├── PageResult.java            # 分页结果封装
    │   └── GlobalExceptionHandler.java # 全局异常处理
    ├── config/
    │   ├── WebConfig.java             # CORS + 拦截器注册
    │   ├── SecurityConfig.java        # Spring Security 配置
    │   ├── PasswordConfig.java        # BCrypt 密码编码器
    │   ├── MybatisPlusConfig.java     # 分页插件
    │   └── MyMetaObjectHandler.java   # 自动填充时间
    ├── interceptor/
    │   ├── LoginInterceptor.java      # JWT 登录校验拦截器
    │   └── UserContext.java           # 线程变量存储用户ID
    ├── util/
    │   └── JwtUtil.java               # JWT 生成与解析工具
    ├── entity/
    │   ├── User.java
    │   ├── Category.java
    │   ├── Record.java
    │   ├── dto/
    │   │   ├── RegisterDTO.java
    │   │   ├── LoginDTO.java
    │   │   ├── PasswordUpdateDTO.java
    │   │   ├── CategoryDTO.java
    │   │   └── RecordDTO.java
    │   └── Vo/
    │       ├── UserVO.java
    │       ├── RecordVO.java
    │       ├── MonthlyStatisticsVO.java
    │       └── CategoryStatisticsVO.java
    ├── Mapper/
    │   ├── UserMapper.java
    │   ├── CategoryMapper.java
    │   ├── RecordMapper.java
    │   └── StatisticsMapper.java
    ├── Service/
    │   ├── UserService.java
    │   ├── CategoryService.java
    │   ├── RecordsService.java
    │   ├── StatisticsService.java
    │   └── impl/
    │       ├── UserServicesImpl.java
    │       ├── CategoryServiceImpl.java
    │       ├── RecordsServiceImpl.java
    │       └── StatisticsServiceImpl.java
    └── resources/
        ├── application.yml
        └── mapper/
            ├── RecordMapper.xml
            └── StatisticsMapper.xml
```
