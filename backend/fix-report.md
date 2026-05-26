# 后端接口修复报告

## 修复清单（共修复 15 处）

---

### 1. UserVO 缺少字段

**问题**：`UserVO.java` 只包含 `id`、`username`，缺少 API 文档要求的 `createTime`、`updateTime`

**修复**：添加 `createTime`、`updateTime` 字段，并在 `UserServicesImpl.getUserInfo()` 中赋值

**涉及文件**：
- `entity/Vo/UserVO.java`
- `Service/impl/UserServicesImpl.java`

---

### 2. PageResult 缺少分页字段

**问题**：`PageResult.java` 只有 `records`、`total`，缺少 API 文档要求的 `pages`、`current`、`size`

**修复**：添加三个字段及完整构造函数，并在 `RecordsServiceImpl.getRecordsById()` 中填充

**涉及文件**：
- `common/PageResult.java`
- `Service/impl/RecordsServiceImpl.java`

---

### 3. 修改密码返回值 message 不匹配

**问题**：返回 `"修改密码成功"`，API 文档要求 `"修改成功"`

**修复**：改为 `"修改成功"`，且 `data` 返回 `null`

**涉及文件**：
- `Controller/UserController.java`

---

### 4. POST /api/categories 缺少参数校验

**问题**：使用 `Category` 实体接收请求而非 `CategoryDTO`，无 `@Valid` 校验

**修复**：改用 `@Valid @RequestBody CategoryDTO`，保留已有 `CategoryDTO`（已含 `@NotBlank`、`@NotNull` 注解）

**涉及文件**：
- `Controller/CategoryController.java`

---

### 5. PUT /api/categories/{id} 逻辑错误（严重 Bug）

**问题**：
- 未使用路径参数 `{id}`
- DTO 使用 `oldCategoryName`/`newCategoryName`，API 文档要求 `name`/`type`
- Service 中 `selectById(userId)` 误将 userId 当 categoryId 传参

**修复**：
- 使用 `@PathVariable Long id`
- 使用 `CategoryDTO`（含 `name`/`type`）作为请求体
- 先按 categoryId 查询，校验归属后更新 `name`、`type` 两个字段

**涉及文件**：
- `Controller/CategoryController.java`
- `Service/CategoryService.java`
- `Service/impl/CategoryServiceImpl.java`

---

### 6. DELETE /api/categories/{id} 缺少归属校验

**问题**：直接根据 `{id}` 删除，未校验分类是否属于当前用户

**修复**：先按 categoryId 查询分类，校验 `userId` 匹配后再删除

**涉及文件**：
- `Controller/CategoryController.java`
- `Service/CategoryService.java`
- `Service/impl/CategoryServiceImpl.java`

---

### 7. GET /api/records/{id} 未使用路径参数（严重 Bug）

**问题**：方法签名没有 `@PathVariable Long id`，实际调用 `selectRecordsBy_UserId(userId)` 返回该用户所有记录

**修复**：添加 `@PathVariable Long id`，使用 JOIN 查询单条记录并校验归属

**涉及文件**：
- `Controller/RecordsController.java`
- `Service/RecordsService.java`
- `Service/impl/RecordsServiceImpl.java`
- `Mapper/RecordMapper.java`
- `resources/mapper/RecordMapper.xml`

---

### 8. POST /api/records 使用 RecordVO 而非 RecordDTO

**问题**：用 `RecordVO` 接收请求体（含 service 层不该暴露的字段），缺少 `categoryId` 存在性校验、`amount>0` 校验

**修复**：改用 `@Valid @RequestBody RecordDTO`（已含 `@NotNull`、`@DecimalMin` 注解），新增 `categoryId` 归属校验，使用 MyBatis-Plus `insert()` 而非自定义 XML

**涉及文件**：
- `Controller/RecordsController.java`
- `Service/RecordsService.java`
- `Service/impl/RecordsServiceImpl.java`

---

### 9. PUT /api/records/{id} 误覆盖 createTime

**问题**：更新时设置了 `recordVO.setCreateTime(LocalDateTime.now())`，将创建时间覆盖为当前时间

**修复**：创建新的 `Record` 对象，仅设置更新字段，调用 `updateById()`（由 `MyMetaObjectHandler` 自动填充 `updateTime`）

**涉及文件**：
- `Service/impl/RecordsServiceImpl.java`

---

### 10. DELETE /api/records/{id} 无归属校验

**问题**：直接根据 `recordId` 删除，未校验记录是否属于当前用户

**修复**：先查询记录，校验 `userId` 匹配后再删除

**涉及文件**：
- `Service/impl/RecordsServiceImpl.java`

---

### 11. GlobalExceptionHandler 缺少正确 HTTP 状态码

**问题**：参数校验异常和业务异常都返回 HTTP 500，且 code 均为 500

**修复**：
- `MethodArgumentNotValidException` → HTTP 400，`code: 400`
- `RuntimeException` → HTTP 500，`code: 500`

**涉及文件**：
- `common/GlobalExceptionHandler.java`

---

### 12. CategoryController 注释错误

**问题**：POST 方法注释写的是 `"查询分类列表"`（应为 `"新增分类"`）

**修复**：移除错误注释

---

### 13. CategoryController 方法名拼写错误

**问题**：`unpdate_Category` → 应为 `updateCategory`

**修复**：重命名为 `updateCategory`

---

### 14. RecordsServiceImpl 未返回 updateTime

**问题**：分页查询转换 RecordVO 时未设置 `updateTime`

**修复**：添加 `vo.setUpdateTime(record.getUpdateTime())`

---

### 15. UserController 未使用的 userMapper 注入

**问题**：`UserMapper userMapper` 字段被 `@RequiredArgsConstructor` 注入但从未使用

**修复**：移除该字段及对应 import

---

## 修改文件汇总

| # | 文件 | 改动类型 |
|---|------|----------|
| 1 | `entity/Vo/UserVO.java` | 新增字段 |
| 2 | `common/PageResult.java` | 新增字段+构造函数 |
| 3 | `common/GlobalExceptionHandler.java` | 修复状态码 |
| 4 | `Controller/UserController.java` | 修复返回值+清理未使用字段 |
| 5 | `Controller/CategoryController.java` | 重写全部方法 |
| 6 | `Controller/RecordsController.java` | 重写全部方法 |
| 7 | `Service/CategoryService.java` | 更新接口签名 |
| 8 | `Service/RecordsService.java` | 更新接口签名 |
| 9 | `Service/impl/UserServicesImpl.java` | 补充字段赋值 |
| 10 | `Service/impl/CategoryServiceImpl.java` | 重写更新/删除逻辑 |
| 11 | `Service/impl/RecordsServiceImpl.java` | 重写全部实现 |
| 12 | `Mapper/RecordMapper.java` | 替换自定义方法 |
| 13 | `resources/mapper/RecordMapper.xml` | 替换为 JOIN 查询 |

## 接口完成状态（修复后）

```
阶段一（基础 CRUD）
  ✅ 1. 项目初始化 + 数据库建表
  ✅ 2. 用户注册（密码加密）
  ✅ 3. 用户登录（JWT 生成）
  ✅ 4. JWT 拦截器（校验 + 提取用户）
  ✅ 5. 查看个人信息
  ✅ 6. 修改密码
  ✅ 7. 分类 CRUD（含归属校验）

阶段二（账单管理）
  ✅ 8. 账单新增（含外键校验）
  ✅ 9. 账单修改 + 删除（含归属校验）
  ✅ 10. 账单分页查询（多条件 + 联表）
  ✅ 11. 账单详情查询（联表）

阶段三（统计分析）
  ✅ 12. 月度收支汇总（SQL 聚合）
  ✅ 13. 分类统计（GROUP BY + 百分比）
```
