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
    """POST {base_url}/audio/transcriptions（OpenAI 兼容 multipart）"""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 30.0):
        self._url = base_url.rstrip("/") + "/audio/transcriptions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def transcribe(self, audio_bytes: bytes, filename: str) -> SttResult:
        files = {"file": (filename, audio_bytes, "application/octet-stream")}
        data = {"model": self._model, "response_format": "verbose_json"}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self._url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            payload = resp.json()
        return SttResult(
            text=(payload.get("text") or "").strip(),
            language=payload.get("language"),
            confidence=_confidence_from_segments(payload),
        )


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
