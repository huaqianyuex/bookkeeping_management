"""登录接口 SQL 注入（SQLi）回归测试 — 传统注入载荷集

定位：**回归防线**，不是「发现漏洞」。当前 `crud/user.py` 用 SQLAlchemy 2.0
表达式语句（`select(User).where(User.username == username)`），用户名以绑定
参数下发，传统字符串拼接类注入在架构上不成立。本文件把「每次重构都别退化
成字符串拼接」这件事固化成可执行的断言。

⚠️ 未执行声明：本文件在编写会话中**未实跑**（沙箱 Python 缺 fastapi/sqlalchemy/
   pytest/aiomysql）。请在项目自身环境执行：
       cd fast_backend && python -m pytest tests/test_sqli_login.py -v

设计取舍：
1. 不连真实 MySQL。`app.dependency_overrides[get_db]` 注入假 Session，用
   `crud.user.get_user_by_username` 的**入参**作为观测点 —— 载荷若原样到达
   数据访问层，说明它被当作「数据」而非「SQL 结构」传递。
2. 凭据错误时出口必须统一为 401「用户名或密码错误」：任何差异化响应都是
   注入可探测信号（error-based / boolean-based 的观测面）。
3. 用 `/api/health` 预热应用（触发 lifespan），与 tests/test_app.py 同口径。
"""
import pytest
from fastapi.testclient import TestClient

from config.db_config import get_db
from crud import user as user_crud
from main import app
from utils import security

LOGIN_URL = "/api/user/login"

# bcrypt 成本较高，这里用直接比较替身；生产路径 utils.security.verify_password 已有单测覆盖
_FAKE_HASH = "fake-hash-for-sqli-test"

# ---------------------------------------------------------------------------
# 传统 SQL 注入载荷集（按注入类别分组）
# 说明：预期结果全部是「401 + 统一文案 / 422 长度超限」，没有任何一条应当 200
# ---------------------------------------------------------------------------
SQLI_PAYLOADS: dict[str, list[str]] = {
    # 1) 认证绕过（最经典：注释截断 + 恒真条件）
    "auth_bypass_classic": [
        "' OR '1'='1",
        "' OR '1'='1'--",
        "' OR '1'='1'#",
        "' OR '1'='1'/*",
        "admin'--",
        "admin'#",
        "admin'/*",
        "' OR 1=1--",
        "' OR 1=1#",
        "' OR 1=1 LIMIT 1--",
        "' OR 'x'='x",
        "') OR ('1'='1",
        "') OR ('1'='1'--",
        "1' OR '1'='1' /*",
        "' OR '1'='1' AND '1'='1",
    ],
    # 2) 布尔盲注（真/假条件应产生完全相同的响应）
    "boolean_blind": [
        "admin' AND '1'='1",
        "admin' AND '1'='2",
        "admin' AND SUBSTRING(username,1,1)='a'--",
        "admin' AND ASCII(SUBSTRING(username,1,1))>64--",
        "admin' AND LENGTH(password)>5--",
        "' AND (SELECT COUNT(*) FROM users)>0--",
    ],
    # 3) 时间盲注（MySQL：SLEEP/BENCHMARK；此处休眠会直接表现为响应变慢）
    "time_blind": [
        "' AND SLEEP(5)--",
        "' AND SLEEP(5)#",
        "'; SELECT SLEEP(5)--",
        "admin' AND (SELECT 1 FROM (SELECT SLEEP(5))x)--",
        "' OR IF(1=1,SLEEP(5),0)--",
        "admin' AND BENCHMARK(5000000,MD5('a'))--",
    ],
    # 4) 报错注入（探测 SQL 解析错误是否外泄到响应体）
    "error_based": [
        "' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--",
        "' AND UPDATEXML(1,CONCAT(0x7e,DATABASE()),1)--",
        "' AND (SELECT 1 FROM(SELECT COUNT(*),CONCAT(VERSION(),FLOOR(RAND(0)*2))x FROM users GROUP BY x)a)--",
        "' AND GTID_SUBSET(CONCAT(0x7e,VERSION()),1)--",
        "' AND JSON_KEYS((SELECT CONVERT((SELECT VERSION()) USING utf8)))--",
        "' AND EXP(~(SELECT * FROM(SELECT VERSION())a))--",
    ],
    # 5) UNION 联合查询（探测列数 / 拖库）
    "union_based": [
        "' UNION SELECT 1--",
        "' UNION SELECT 1,2--",
        "' UNION SELECT 1,2,3--",
        "' UNION SELECT NULL,NULL,NULL--",
        "' UNION SELECT username,password FROM users--",
        "' UNION ALL SELECT NULL,CONCAT(username,0x3a,password),NULL FROM users--",
        "' UNION SELECT 1,@@version,3--",
        "' UNION SELECT 1,LOAD_FILE('/etc/passwd'),3--",
    ],
    # 6) 堆叠查询（MySQL 驱动默认多语句关闭，用于验证这一点）
    "stacked_queries": [
        "'; DROP TABLE users--",
        "'; DELETE FROM users WHERE 1=1--",
        "'; UPDATE users SET password='x' WHERE 1=1--",
        "'; INSERT INTO users(username,password) VALUES('hack','x')--",
        "'; SELECT SLEEP(3)--",
    ],
    # 7) 元字符 / 引号闭合探针（看是否抛 500 或泄露 SQL 片段）
    "metachar_probe": [
        "'",
        "''",
        "'''",
        "\"",
        "\\",
        "\\'",
        "`)",
        "--",
        "#",
        "/*",
        "'\"",
        "\\' OR 1=1--",
        "%",
        "_",
        "100%",
        "a_b",
    ],
    # 8) 编码 / 过滤绕过（URL 编码、宽字节、大小写混淆、内联注释）
    "encoding_bypass": [
        "%27%20OR%20%271%27%3D%271",
        "' OR '1'='1' -- ",
        "'/**/OR/**/1=1--",
        "' oR '1'='1'--",
        "' Or 1=1#",
        "' OR 1=1;--",
        "%bf%27 OR 1=1--",              # GBK 宽字节场景（utf8mb4 下应无效）
        "admin%00' OR 1=1--",           # 空字节截断
        "' OR '1'='1' UNION SELECT 1,2,3--",
    ],
    # 9) NoSQL / 非 SQL 载荷（确认不会被误当结构解析）
    "nosql_style": [
        "{\"$ne\": null}",
        "admin' || '1'=='1",
        "admin' OR 1 --",
        "$gt",
    ],
}

_ALL_PAYLOADS = [(g, p) for g, ps in SQLI_PAYLOADS.items() for p in ps]

# 长度限制边界：LoginRequest.username 限长 100（见 schemas/user.py:46）
_OVERLONG_PAYLOAD = "' OR '1'='1' UNION SELECT " + "NULL," * 30 + "1--"


@pytest.fixture()
def fake_db():
    """假 AsyncSession：登录路径只用到 commit()，查询已被 crud 层打桩。"""
    class _FakeDB:
        async def commit(self):
            return None

    return _FakeDB()


@pytest.fixture()
def client(fake_db):
    async def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:          # with 触发 lifespan，与 test_app.py 一致
        c.get("/api/health")
        yield c
    app.dependency_overrides.clear()


def _install_stub(monkeypatch, captured: list[str], user_obj=None):
    """打桩 get_user_by_username，并记录到达数据访问层的原始用户名。"""
    async def _stub(db, username):
        captured.append(username)
        return user_obj

    monkeypatch.setattr(user_crud, "get_user_by_username", _stub)


# ---------------------------------------------------------------------------
# 1. 传统载荷：一律不得认证成功，且出口必须统一
# ---------------------------------------------------------------------------
class TestLoginInjectionPayloads:
    @pytest.mark.parametrize(
        "case,payload",
        _ALL_PAYLOADS,
        ids=[f"{g}::{p}" for g, p in _ALL_PAYLOADS],
    )
    def test_payload_never_authenticates(self, client, monkeypatch, case, payload):
        """核心断言：无有效凭据时，任何载荷都拿不到 token。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)   # 模拟「用户不存在」

        res = client.post(LOGIN_URL, json={"username": payload, "password": payload})

        assert res.status_code != 200, f"{case} 载荷意外通过认证: {payload!r}"
        body = res.json()
        assert "token" not in str(body), f"{case} 响应中不应出现 token: {body}"

    @pytest.mark.parametrize(
        "case,payload",
        _ALL_PAYLOADS,
        ids=[f"{g}::{p}" for g, p in _ALL_PAYLOADS],
    )
    def test_no_sql_error_leaks(self, client, monkeypatch, case, payload):
        """不得 500：SQL 解析错误若外泄，就是 error-based 注入的观测面。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        res = client.post(LOGIN_URL, json={"username": payload, "password": "x"})

        assert res.status_code != 500, f"{case} 触发 500: {res.text[:300]}"
        assert "SQL" not in res.text and "sqlalchemy" not in res.text.lower()

    @pytest.mark.parametrize(
        "case,payload",
        _ALL_PAYLOADS,
        ids=[f"{g}::{p}" for g, p in _ALL_PAYLOADS],
    )
    def test_unified_error_message(self, client, monkeypatch, case, payload):
        """用户不存在与密码错误的出口必须一致，否则可布尔盲注枚举用户。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        res = client.post(LOGIN_URL, json={"username": payload, "password": "x"})
        if res.status_code == 401:
            # 全局异常处理器把 HTTPException 包装成 {code, message, data} 信封
            assert res.json()["message"] == "用户名或密码错误"

    def test_payload_reaches_dal_as_plain_data(self, client, monkeypatch):
        """参数化证据：载荷原样到达数据访问层，未被拼接/截断成 SQL 结构。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        payload = "' OR '1'='1'--"
        client.post(LOGIN_URL, json={"username": payload, "password": "x"})

        assert captured, "未走到数据访问层（前置校验拦截了？）"
        assert captured[0] == payload, (
            "载荷应作为完整字符串下传；若被改写说明存在字符串加工/拼接"
        )

    def test_overlong_payload_rejected_by_schema(self, client, monkeypatch):
        """超长载荷由 Pydantic 限长（max_length=100）挡住，返回 422。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        res = client.post(LOGIN_URL, json={"username": _OVERLONG_PAYLOAD, "password": "x"})

        assert res.status_code == 422
        assert captured == [], "限长校验应在触达数据访问层之前生效"


# ---------------------------------------------------------------------------
# 2. 盲注观测面：响应不可区分
# ---------------------------------------------------------------------------
class TestBlindInjectionOracle:
    TRUE_FALSE_PAIRS = [
        ("' OR '1'='1", "' OR '1'='2"),
        ("admin' AND '1'='1", "admin' AND '1'='2"),
        ("' AND (SELECT 1)=1--", "' AND (SELECT 1)=2--"),
    ]

    @pytest.mark.parametrize("true_payload,false_payload", TRUE_FALSE_PAIRS)
    def test_true_false_indistinguishable(self, client, monkeypatch, true_payload, false_payload):
        """恒真与恒假载荷的响应必须完全一致，否则构成布尔盲注 oracle。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        r_true = client.post(LOGIN_URL, json={"username": true_payload, "password": "x"})
        r_false = client.post(LOGIN_URL, json={"username": false_payload, "password": "x"})

        assert r_true.status_code == r_false.status_code, (
            f"状态码可区分: {r_true.status_code} vs {r_false.status_code}"
        )
        assert r_true.json() == r_false.json(), (
            f"响应体可区分: {r_true.json()} vs {r_false.json()}"
        )

    def test_time_blind_no_delay(self, client, monkeypatch):
        """时间盲注：响应耗时不应随载荷变化（SLEEP/BENCHMARK 未被求值）。"""
        import time

        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        t0 = time.perf_counter()
        client.post(LOGIN_URL, json={"username": "' AND SLEEP(5)--", "password": "x"})
        elapsed = time.perf_counter() - t0

        assert elapsed < 2.0, f"疑似时间盲注生效，耗时 {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# 3. 用户名规范化边界：绕过 or 放大攻击面
# ---------------------------------------------------------------------------
class TestUsernameNormalizationBoundary:
    """LoginRequest 只 strip 首尾空白、不校验字符集（schemas/user.py:49-53），
    因此这些输入会原样进入查询 —— 需要确认不会造成等价绕过或响应差异。"""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("  admin  ", "admin"),            # 普通空格
            ("\tadmin\t", "admin"),            # 制表符
            ("\nadmin\n", "admin"),            # 换行
            ("\u3000admin\u3000", "admin"),    # 全角空格（中文输入法常见）
            ("\u00a0admin\u00a0", "admin"),    # 不换行空格
        ],
    )
    def test_strip_variants(self, client, monkeypatch, raw, expected):
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        client.post(LOGIN_URL, json={"username": raw, "password": "x"})

        assert captured[0] == expected, f"规范化结果不符：{raw!r} -> {captured[0]!r}"

    @pytest.mark.parametrize(
        "raw",
        [
            "admin\u0000",          # 尾部空字节
            "ad\u200bmin",          # 零宽空格：仅 strip 首尾，中间原样保留
            "admin\uff07",          # 全角单引号：不应折叠为 ASCII 单引号
            "admın",                # 无点 i（土耳其字符）：不应折叠为 ASCII i
            "ADMIN",                # 大小写：交由 DB collation 处理
        ],
    )
    def test_homoglyph_and_null_byte_not_folded(self, client, monkeypatch, raw):
        """这些字符若被上游静默折成 ASCII，等价类会被放大；此处断言原样下传。"""
        captured: list[str] = []
        _install_stub(monkeypatch, captured, user_obj=None)

        client.post(LOGIN_URL, json={"username": raw, "password": "x"})

        assert captured[0] == raw, f"{raw!r} 被改写为 {captured[0]!r}"


# ---------------------------------------------------------------------------
# 4. 正确性对照：真凭据必须能登录（防止「全部 401」的假绿）
# ---------------------------------------------------------------------------
class TestValidLoginStillWorks:
    def test_valid_credentials_get_token(self, client, monkeypatch):
        """阴性对照：若把拦截逻辑写死成 401，本用例会失败。"""
        captured: list[str] = []

        class _U:
            id = 1
            username = "alice"
            password = _FAKE_HASH
            status = 1
            last_login_at = None

        _install_stub(monkeypatch, captured, user_obj=_U())
        monkeypatch.setattr(security, "verify_password", lambda p, h: h == _FAKE_HASH)

        async def _fake_token(db, uid):
            return "jwt.token.for.test"

        monkeypatch.setattr(user_crud, "create_token", _fake_token)

        res = client.post(LOGIN_URL, json={"username": "alice", "password": "123456"})

        assert res.status_code == 200, res.text
        assert res.json()["data"]["token"] == "jwt.token.for.test"
