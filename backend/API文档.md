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
| password | String | 是 | 6-20 位 |

```json
{
  "username": "zhangsan",
  "password": "123456"
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
| 用户名长度不足 | 400 | 用户名长度2-20位 |
| 密码长度不足 | 400 | 密码长度6-20位 |

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
  "password": "123456"
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
| newPassword | String | 是 | 6-20 位 |

```json
{
  "oldPassword": "123456",
  "newPassword": "654321"
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
| 新密码格式错误 | 400 | 密码长度为6~20位 |

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

## 五、数据库设计

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
```

### 关系说明

- `category.user_id` → `user.id`（多对一，一个用户有多个分类）
- `record.user_id` → `user.id`（多对一，一个用户有多条记录）
- `record.category_id` → `category.id`（多对一，一个分类下有多条记录）
- 所有数据按 `user_id` 隔离，用户只能操作自己的数据

---

## 六、DTO / VO 汇总

### 请求 DTO

| DTO | 字段 | 类型 | 校验规则 |
|-----|------|------|----------|
| RegisterDTO | username | String | `@NotBlank` `@Size(min=2, max=20)` |
| RegisterDTO | password | String | `@NotBlank` `@Size(min=6, max=20)` |
| LoginDTO | username | String | `@NotBlank` |
| LoginDTO | password | String | `@NotBlank` |
| PasswordUpdateDTO | oldPassword | String | `@NotBlank` |
| PasswordUpdateDTO | newPassword | String | `@NotBlank` `@Size(min=6, max=20)` |
| CategoryDTO | name | String | `@NotBlank` |
| CategoryDTO | type | Integer | `@NotNull`（0=支出 / 1=收入） |
| RecordDTO | categoryId | Long | `@NotNull` |
| RecordDTO | amount | BigDecimal | `@NotNull` `@DecimalMin("0.01")` |
| RecordDTO | remark | String | 无校验（可选） |
| RecordDTO | recordDate | String | `@NotNull`（格式 `yyyy-MM-dd`） |

### 响应 VO

| VO | 字段 |
|----|------|
| UserVO | id, username, createTime, updateTime |
| RecordVO | id, userId, categoryId, categoryName, categoryType, amount, remark, recordDate, createTime, updateTime |
| MonthlyStatisticsVO | year, month, totalIncome, totalExpense, balance |
| CategoryStatisticsVO | categoryId, categoryName, amount, percentage |

---

## 七、JWT 认证说明

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

## 八、错误码汇总

| code | HTTP 状态码 | 说明 |
|------|-------------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 参数校验失败（`@Valid` 触发的验证错误） |
| 401 | 401 | 未登录或 Token 无效 |
| 500 | 500 | 业务异常（用户名重复、密码错误、数据不存在等） |

---

## 九、项目目录结构

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
