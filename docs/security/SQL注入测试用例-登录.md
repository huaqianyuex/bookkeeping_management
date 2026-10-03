# 登录接口 SQL 注入测试用例（传统载荷集）

> 适用对象：`POST /api/user/login`（`fast_backend/routers/user.py:44`）
> 配套自动化用例：[fast_backend/tests/test_sqli_login.py](../fast_backend/tests/test_sqli_login.py)

## 0. 先看结论：这版登录功能在架构上不满足经典注入前提

传统 SQL 注入的成立条件是**用户输入被字符串拼接进 SQL 语句**。本项目该条件不成立：

| 环节 | 位置 | 实际写法 | 结论 |
|---|---|---|---|
| 查询 | `crud/user.py:20` | `select(User).where(User.username == username)` | SQLAlchemy 2.0 表达式语句，`==` 编译为绑定参数 `:username` |
| 驱动 | `docker-compose.yml` | `mysql+aiomysql` | 绑定参数由驱动侧走 prepared statement 路径 |
| 密码 | `routers/user.py:59` | `security.verify_password(...)` | 密码只做 bcrypt 校验，**从不参与 SQL** |
| 鉴权 | `utils/auth.py:24-32` | 解码 JWT 后**回查** `get_user_by_id`（同样参数化） | 与登录查询同一条参数化路径；token 伪造属于 JWT 攻击面，与 SQLi 正交 |
| 出参 | `routers/user.py:79` | 固定 `{token}` | 无查询结果回显，UNION 无法取数 |

所以下表的用例**预期结果全部是「拦截」**。它们的作用有两层：

1. **回归防线** —— 锁死「查询层不许退化成 f-string / `text()` 拼接」；
2. **毕设/答辩材料** —— 用可复现的用例证明已做过的验证，而不是口头声明「用了 ORM 所以安全」。

⚠️ 本文与配套 pytest 文件**未在本机实跑**：当前环境 Python 缺 `fastapi`/`sqlalchemy`/`pytest`/`aiomysql`。
请在你自己的后端环境执行文末命令后，把真实输出作为结论依据。

## 1. 环境准备

```bash
# 起 MySQL + 后端（后端暴露 8000）
docker compose up -d mysql backend

# 准备一个已知账号（用户名 2-20 位中英文或数字，密码 6 位数字）
curl -s -X POST http://localhost:8000/api/user/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"123456"}'
```

## 2. 交互式复现脚本（逐条打靶，肉眼可读）

```bash
#!/usr/bin/env bash
# sqli_login_probe.sh —— 登录接口传统 SQLi 载荷探测
# 用法：bash sqli_login_probe.sh http://localhost:8000
TARGET="${1:-http://localhost:8000}/api/user/login"

probe() {   # probe <用例名> <username> <password>
  local name="$1" u="$2" p="$3"
  local t0 t1 ms code body
  t0=$(date +%s%N)
  body=$(curl -s -m 20 -o /tmp/sqli_body -w '%{http_code}' \
    -X POST "$TARGET" -H 'Content-Type: application/json' \
    --data-binary "$(printf '{"username":%s,"password":%s}' \
      "$(printf '%s' "$u" | jq -Rs .)" "$(printf '%s' "$p" | jq -Rs .)")")
  t1=$(date +%s%N)
  ms=$(( (t1 - t0) / 1000000 ))
  printf '%-34s HTTP=%s  %5sms  %s\n' "$name" "$body" "$ms" "$(head -c 120 /tmp/sqli_body)"
}

echo '--- 1. 认证绕过 ---'
probe "or-1=1"            "' OR '1'='1"        "' OR '1'='1"
probe "comment--"         "admin'--"           "x"
probe "comment#"          "admin'#"            "x"
probe "or-1=1-limit"      "' OR 1=1 LIMIT 1--" "x"
echo '--- 2. 布尔盲注（真/假必须同响应） ---'
probe "bool-true"         "admin' AND '1'='1"  "x"
probe "bool-false"        "admin' AND '1'='2"  "x"
echo '--- 3. 时间盲注（耗时必须不明显抬升） ---'
probe "sleep5"            "' AND SLEEP(5)--"   "x"
probe "benchmark"         "admin' AND BENCHMARK(5000000,MD5('a'))--" "x"
echo '--- 4. 报错注入（不得 500 / 不得回显 SQL） ---'
probe "extractvalue"      "' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--" "x"
probe "updatexml"         "' AND UPDATEXML(1,CONCAT(0x7e,DATABASE()),1)--" "x"
echo '--- 5. UNION ---'
probe "union-3col"        "' UNION SELECT 1,2,3--" "x"
probe "union-dump"        "' UNION SELECT username,password FROM users--" "x"
echo '--- 6. 堆叠 ---'
probe "drop-table"        "'; DROP TABLE users--" "x"
echo '--- 7. 引号探针（不得 500） ---'
probe "single-quote"      "'"                  "x"
probe "backslash"         "\\"                 "x"
echo '--- 8. 编码/过滤绕过 ---'
probe "url-encoded"       "%27 OR %271%27=%271" "x"
probe "inline-comment"    "'/**/OR/**/1=1--"   "x"
probe "mixed-case"        "' oR '1'='1'--"     "x"
probe "gbk-wide-byte"     "%bf%27 OR 1=1--"    "x"
echo '--- 9. 阴性对照：真凭据必须成功 ---'
probe "valid-login"       "alice"              "123456"
```

## 3. 用例矩阵

「期望」列的判定口径统一为：**不得 200 且不得带 token、不得 500、不得回显 SQL 片段或版本信息**。
唯二例外是长度超限（422）与真凭据对照（200）。

| # | 类别 | 载荷 | 期望 | 不通过意味着 |
|---|---|---|---|---|
| 1 | 认证绕过 | `' OR '1'='1` | 401 统一文案 | 输入进入了 SQL 结构 |
| 2 | 认证绕过 | `' OR '1'='1'--` / `#` / `/*` | 401 | 注释截断了原查询 |
| 3 | 认证绕过 | `admin'--` / `admin'#` | 401 | 可无密码登录任意已知用户 |
| 4 | 认证绕过 | `') OR ('1'='1` | 401 | 括号闭合后恒真 |
| 5 | 布尔盲注 | `admin' AND '1'='1` vs `'1'='2` | 两者状态码与响应体**完全相同** | 存在布尔 oracle，可逐字符拖库 |
| 6 | 布尔盲注 | `admin' AND SUBSTRING(username,1,1)='a'--` | 401 且与假条件无差异 | 可枚举用户名 |
| 7 | 时间盲注 | `' AND SLEEP(5)--` | 耗时 < 2s | 存在时间 oracle |
| 8 | 时间盲注 | `BENCHMARK(5000000,MD5('a'))` | 耗时不明显抬升 | 同上 |
| 9 | 报错注入 | `EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))` | 401，响应无 SQL 报错 | 库版本外泄 |
| 10 | 报错注入 | `UPDATEXML(...DATABASE()...)` | 401 | 库名外泄 |
| 11 | UNION | `' UNION SELECT 1,2,3--` | 401，响应无查询结果 | 存在回显点 |
| 12 | UNION | `' UNION SELECT username,password FROM users--` | 401 | 可拖凭据表 |
| 13 | 堆叠 | `'; DROP TABLE users--` | 401，表仍存在 | 驱动允许多语句且查询层可拼接 |
| 14 | 堆叠 | `'; UPDATE users SET password='x' WHERE 1=1--` | 401，原密码仍可登录 | 数据被篡改 |
| 15 | 元字符 | `'` / `"` / `\` / ``` ` | 401，不得 500 | 500 = error-based 观测面 |
| 16 | 编码绕过 | `%27 OR %271%27=%271` | 401 | 过滤被编码绕过 |
| 17 | 编码绕过 | `'/**/OR/**/1=1--` | 401 | 内联注释绕过过滤 |
| 18 | 编码绕过 | `' oR '1'='1'--` | 401 | 大小写过滤被绕过 |
| 19 | 宽字节 | `%bf%27 OR 1=1--` | 401 | 库为 utf8mb4（见下），本条预期无效 |
| 20 | 空字节 | `admin%00' OR 1=1--` | 401 | 截断绕过 |
| 21 | 长度边界 | 101+ 字符载荷 | 422（`max_length=100`） | 未在入口限长 |
| 22 | 阴性对照 | `alice` / `123456` | 200 且返回 token | **若此条失败，前面所有 401 都是假绿** |

### 字段级补充断言

| # | 目标 | 输入 | 期望 | 依据 |
|---|---|---|---|---|
| 23 | 用户枚举 | 不存在用户 vs 存在用户+错密码 | 两者均 401「用户名或密码错误」 | `routers/user.py:57-64` 已统一文案 |
| 24 | 用户名规范化 | `"␣␣admin␣␣"`、`\t`、`\n`、`\u3000`（全角）、`\u00a0` | `strip()` 后为 `admin` | `schemas/user.py:49-53` 只 strip 不校验格式 |
| 25 | 同形字符 | 全角单引号 `＇`、无点 `ı`、零宽空格 | 原样下传，不被折成 ASCII | 上游若静默折叠会放大等价类 |
| 26 | LIKE 元字符 | 用户名含 `%` / `_` | 登录路径不做 LIKE，无影响 | 登录无模糊查询 |
| 27 | 限流绕过 | 同 IP 同用户名连续失败 5 次 | 第 6 次 429，锁 15 分钟 | `utils/throttle.py`，key = `IP｜用户名` |

## 4. 载荷集归类说明（为什么选这些）

- **认证绕过类**是登录注入的核心目标：攻击者不关心拖库，只要 `WHERE` 恒真。
  构造手法三种 —— 恒真条件、注释截断（`--` `#` `/*`）、括号闭合并列齐全即覆盖。
- **布尔/时间盲注**用于无回显场景，本项目正是无回显（响应固定 `{token}`），
  所以判定重点不是「是否报错」而是**响应可分性**：真/假载荷必须不可区分、耗时必须一致。
- **报错注入**针对「异常是否穿透到响应」。`main.py` 若无全局异常兜底，
  SQLAlchemy 异常可能以 500 形式外泄堆栈 —— 这是本类唯一需要重点观察的地方。
- **堆叠查询**验证的是驱动能力：`aiomysql` 默认不允许多语句，这条是确认而非假设。
- **编码/宽字节类**针对 WAF 绕过。宽字节注入（`%bf%27`）只在 GBK 连接字符集下成立；
  本项目 `utf8mb4`（`docker-compose.yml` 已指定 `character-set-server=utf8mb4`），
  此条预期无效，但保留以证明做过该项检查。

## 5. 关于长度限制的一个真实发现

`schemas/user.py:46-47` 把 `username`/`password` 限长 100，但：

```python
username: str = Field(min_length=1, max_length=100, ...)   # 限长
@field_validator("username")
def _check_username(cls, v: str) -> str:
    return normalize_username(v)                            # 仅 strip，不校验字符集
```

对比 `RegisterRequest`（`schemas/user.py:12`）有 `USERNAME_PATTERN` 白名单
`^[A-Za-z0-9\u4e00-\u9fa5]{2,20}$`，**登录接口刻意不做格式校验**（注释说明是为了避免探测用户名）。

这是个有意的权衡，不是 bug；但要意识到其后果：登录入口的输入字符集是**敞开的**，
长度上限就是唯一约束。安全责任因此完全落在查询层的参数化上。
所以配套用例里 `test_payload_reaches_dal_as_plain_data` 是**最关键的回归断言** ——
它直接锁定「载荷原样下传、未被加工成 SQL 结构」这一性质。

## 6. 执行命令

```bash
# 自动化回归（推荐；不依赖真实 MySQL）
cd fast_backend && python -m pytest tests/test_sqli_login.py -v

# 补上原有的安全单测，确认无回归
cd fast_backend && python -m pytest tests/ -q
```

## 7. 若"传统注入"未命中的话，登录功能更值得测的方向

传统 SQLi 在这套 ORM + 无状态 JWT 架构上命中率极低。同样的时间投到下面几项产出更高：

1. **限流绕过**：`login_throttle` 是单进程内存字典（`utils/throttle.py:47`）。
   多 worker 部署时各进程独立计数；key 含 IP，换 IP 即绕过。可用
   `X-Forwarded-For` 试探是否被用于 `request.client.host`。
   ```bash
   curl -X POST http://localhost:8000/api/user/login -H 'X-Forwarded-For: 1.2.3.4' \
     -H 'Content-Type: application/json' -d '{"username":"alice","password":"000000"}'
   ```
2. **JWT 攻击面**：`utils/auth.py:24-32` 解码后会回查 users 表并校验 `status`，
   所以「伪造 sub 直接过鉴权」不成立；但仍有两点可测：
   ① `JWT_SECRET` 若沿用 `.env.example` 的默认值即可离线签发任意用户令牌（**最高优先级**）；
   ② `sub` 由 `int(user_id)` 转型（`utils/auth.py:30`），测 `"sub":"abc"`、`"sub":null`、
   `"sub":1.9` 是否被 `except Exception` 干净兜成 401 而非 500。
   另外**没有令牌吊销机制**（`crud/user.py:77-88` 明确说 `user_token` 表未启用），
   改密码/禁用后旧 token 在有效期内依然可用 —— 值得单独立项。
3. **6 位纯数字密码**：`PASSWORD_PATTERN = ^\d{6}$`，空间仅 100 万。
   真正的风险是**离线爆破**而非 SQLi；配合限流实现评估。
4. **注册→登录链路**：用户名规范化前后的等价类（`" alice"` 与 `"alice"` 是否撞库）。
5. **`PUT /api/user/info` 改用户名**：唯一性校验是否漏了排除自身（`docs/.../04` §1.4 提到该规则）。
