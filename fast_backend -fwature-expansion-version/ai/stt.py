"""语音转写（STT）— Provider 抽象 + OpenAI 兼容 Whisper 实现

口径（docs/语音记账实施指南.md §2.3）：
- 只做「音频 → 文本」，不做任何记账语义解析（解析走 ai/bookkeeping_chain）；
- provider 可替换：实现 SttProvider + 在 _REGISTRY 注册一行，前端与路由零改动；
- 音频只在内存中流转，**不落磁盘、不入库**；
- 复用项目既有的 OpenAI 兼容网关模式（与 ai/llm.py 同构）。

关于临时文件：不写。transcribe() 收 bytes，直接交给 httpx——
少一个失败面（无 finally 漏删、无并发文件名冲突、不怕容器只读文件系统）。
若未来接入必须读文件路径的 provider（如本地 funasr CLI），由该 provider
自己落临时文件，抽象层保持不变。
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import Protocol

import httpx
from pydantic import BaseModel

from config.settings import (
    AGNES_API_KEY,
    OPENAI_BASE_URL,
    STT_API_KEY,
    STT_BASE_URL,
    STT_ENABLED,
    STT_MODEL,
    STT_PROVIDER,
    STT_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

# 瞬时故障重试前的退避：语音是低频调用，短等待足以跨过一次网关抖动
_RETRY_BACKOFF_SECONDS = 0.3


class ProviderNotConfigured(RuntimeError):
    """provider 未启用 / 配置缺失 —— 路由据此返回 ai_error"""


class SttResult(BaseModel):
    text: str
    language: str | None = None
    confidence: float | None = None


class SttProvider(Protocol):
    async def transcribe(self, audio_bytes: bytes, filename: str) -> SttResult: ...


def _confidence_from_segments(payload: dict) -> float | None:
    """Whisper 不直接给置信度，用 segments[].avg_logprob 换算代理值。

    avg_logprob 是对数概率（通常 -1.0 ~ 0），exp() 后映射到 0~1；
    同时用 no_speech_prob 压低「整段是静音/噪声」的可信度。
    """
    segs = payload.get("segments") or []
    if not segs:
        return None
    probs = [math.exp(s.get("avg_logprob", 0.0)) for s in segs]
    base = sum(probs) / len(probs)
    no_speech = max((s.get("no_speech_prob", 0.0) for s in segs), default=0.0)
    return round(max(0.0, min(1.0, base * (1.0 - no_speech))), 4)


class OpenAIWhisperProvider:
    """POST {base_url}/audio/transcriptions（OpenAI 兼容 multipart）

    连接池（审查报告 P1-7）：client 为**成员级懒初始化单例**，随 provider
    （模块级单例，见 :func:`get_stt_provider`）存活整个进程，复用 TCP/TLS 连接。
    此前每次 transcribe 都 `async with httpx.AsyncClient(...)` 新建客户端，
    连接无法复用；语音转写本身延迟高、频率低，握手开销占比可观。client 与事件
    循环绑定，跨 loop 会重建（见 :meth:`_get_client`），关闭走 :meth:`aclose`。

    重试（审查报告 P1-7）：5xx 与连接层异常（超时/断连）视为上游瞬时故障，
    重试 1 次；4xx 是请求自身的问题（鉴权/格式/参数），重试只会白付一次外部
    计费，因此立即上抛。重试只发生在本层，路由层不再重试。

    ⚠️ 单事件循环前提：与本项目护栏（配额/并发/限流）同一约束——单 worker
    单 loop 下安全；多 loop 场景已由 _get_client 的 loop 身份检查兜住。
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0):
        self._url = base_url.rstrip("/") + "/audio/transcriptions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """取与**当前事件循环**绑定的共享 client。

        httpx.AsyncClient 的连接池与传输对象同创建它的 loop 绑定，跨 loop 复用
        会抛 RuntimeError（Event loop is closed / attached to a different loop）。
        单 worker 生产环境只有一个 loop，无碍；但测试里 pytest-asyncio 默认每个
        async 用例新建 loop，若不做隔离就会在第二个用例炸掉——故按 loop 身份重建。
        """
        loop: asyncio.AbstractEventLoop | None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None      # 同步上下文（如直接调用 _get_client 的单测）没有运行中的 loop
        if self._client is None or (loop is not None and self._client_loop is not loop):
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._client_loop = loop
        return self._client

    async def aclose(self) -> None:
        """关闭共享 client（由应用 lifespan shutdown 调用，见 main.lifespan）。"""
        client, self._client, self._client_loop = self._client, None, None
        if client is not None:
            await client.aclose()

    async def transcribe(self, audio_bytes: bytes, filename: str) -> SttResult:
        files = {"file": (filename, audio_bytes, "application/octet-stream")}
        data = {"model": self._model, "response_format": "verbose_json"}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client = self._get_client()

        for attempt in range(2):          # 首次 + 至多 1 次重试
            try:
                resp = await client.post(self._url, headers=headers, files=files, data=data)
            except httpx.TransportError:
                # 连接层瞬时故障：重试一次，仍失败则上抛由路由兜底为通用文案
                if attempt == 0:
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                raise
            if resp.status_code >= 500 and attempt == 0:
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
                continue
            resp.raise_for_status()
            payload = resp.json()
            return SttResult(
                text=(payload.get("text") or "").strip(),
                language=payload.get("language"),
                confidence=_confidence_from_segments(payload),
            )
        # 循环体每条路径都已 return / raise，此处仅为静态检查兜底
        raise RuntimeError("STT 重试后仍未成功")   # pragma: no cover


_REGISTRY: dict[str, object] = {}


def register(name: str):
    def deco(factory):
        _REGISTRY[name] = factory
        return factory
    return deco


@register("openai_whisper")
def _build_openai_whisper() -> SttProvider:
    if not STT_API_KEY:
        raise ProviderNotConfigured("STT_API_KEY 未配置")
    return OpenAIWhisperProvider(
        base_url=STT_BASE_URL or OPENAI_BASE_URL,
        api_key=STT_API_KEY or AGNES_API_KEY,
        model=STT_MODEL,
        timeout=STT_TIMEOUT_SECONDS,
    )


_provider: SttProvider | None = None


def get_stt_provider() -> SttProvider:
    """按 STT_PROVIDER 取 provider；未启用/未注册 → ProviderNotConfigured"""
    global _provider
    if _provider is None:
        if not STT_ENABLED:
            raise ProviderNotConfigured("语音识别未启用")
        factory = _REGISTRY.get(STT_PROVIDER)
        if factory is None:
            raise ProviderNotConfigured(f"未知的 STT provider: {STT_PROVIDER}")
        _provider = factory()          # type: ignore[operator]
    return _provider


async def aclose_stt_provider() -> None:
    """释放进程级 provider 持有的 HTTP 连接（应用 shutdown 调用，见 main.lifespan）。

    只对实现了 aclose 的 provider 生效；provider 尚未创建（从未调用过转写）
    或为自定义实现时静默跳过——连接池是可选优化，关闭失败不应阻断停机。
    """
    provider = _provider
    aclose = getattr(provider, "aclose", None)
    if aclose is not None:
        try:
            await aclose()
        except Exception:
            logger.warning("关闭 STT provider 连接失败（不影响停机）", exc_info=True)
