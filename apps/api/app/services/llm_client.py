"""
LLM Client with fallback strategy and retry logic.

Priority:
1. Local Ollama (fastest, free, private)
2. Gemini free API
3. Cached response fallback (rule-based)

Each provider has timeout + retry. If all fail, returns a cached/rule-based response.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import AsyncGenerator

import httpx
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    provider: str  # "ollama" | "gemini" | "openai" | "cache"
    tool_calls: list[dict] | None = None
    latency_ms: int = 0


@dataclass
class ProviderConfig:
    name: str
    timeout_s: float
    max_retries: int
    retry_delay_s: float


OLLAMA_CONFIG = ProviderConfig(name="ollama", timeout_s=15, max_retries=2, retry_delay_s=0.5)
GEMINI_CONFIG = ProviderConfig(name="gemini", timeout_s=20, max_retries=2, retry_delay_s=1.0)
OPENAI_CONFIG = ProviderConfig(name="openai", timeout_s=30, max_retries=1, retry_delay_s=1.0)

CACHE_TTL = 3600  # 1 hour
CACHE_PREFIX = "llm_cache:"


class LLMClient:
    """Unified LLM client with provider fallback chain."""

    def __init__(self, redis: Redis | None = None):
        self.redis = redis
        self._http = httpx.AsyncClient(timeout=30)

    async def close(self):
        await self._http.aclose()

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        stream: bool = False,
        max_tokens: int = 1000,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Try providers in priority order. Returns LLMResponse or async generator if streaming."""

        if stream:
            return self._stream_with_fallback(messages, tools, max_tokens)

        # Non-streaming: try each provider
        providers = self._get_provider_chain()

        for provider in providers:
            try:
                result = await self._call_provider(provider, messages, tools, max_tokens)
                if result:
                    # Cache successful response
                    await self._cache_response(messages, result)
                    return result
            except Exception as e:
                logger.warning("Provider %s failed: %s", provider.name, str(e)[:100])
                continue

        # All providers failed — try cache
        cached = await self._get_cached_response(messages)
        if cached:
            return cached

        # Final fallback: rule-based
        return LLMResponse(
            content="Xin lỗi, hệ thống đang bận. Bạn có thể thử lại sau giây lát nhé!",
            provider="fallback",
        )

    async def _stream_with_fallback(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Streaming with fallback. Yields SSE-formatted chunks."""
        providers = self._get_provider_chain()

        for provider in providers:
            try:
                if provider.name == "ollama":
                    async for chunk in self._stream_ollama(messages, tools, max_tokens, provider):
                        yield chunk
                    return
                elif provider.name == "gemini":
                    async for chunk in self._stream_gemini(messages, tools, max_tokens, provider):
                        yield chunk
                    return
                elif provider.name == "openai":
                    async for chunk in self._stream_openai(messages, tools, max_tokens, provider):
                        yield chunk
                    return
            except Exception as e:
                logger.warning("Stream provider %s failed: %s", provider.name, str(e)[:100])
                continue

        # All failed
        yield json.dumps({"type": "text", "content": "Hệ thống đang bận, bạn thử lại nhé!"})

    def _get_provider_chain(self) -> list[ProviderConfig]:
        """Build provider chain based on available config."""
        chain = []
        if settings.OLLAMA_URL:
            chain.append(OLLAMA_CONFIG)
        if settings.GEMINI_API_KEY:
            chain.append(GEMINI_CONFIG)
        if settings.OPENAI_API_KEY:
            chain.append(OPENAI_CONFIG)
        return chain

    # ── Provider implementations ──

    async def _call_provider(
        self, config: ProviderConfig, messages: list[dict], tools: list[dict] | None, max_tokens: int
    ) -> LLMResponse | None:
        """Call a single provider with retries."""
        for attempt in range(config.max_retries + 1):
            try:
                start = time.monotonic()
                if config.name == "ollama":
                    result = await self._call_ollama(messages, tools, max_tokens, config)
                elif config.name == "gemini":
                    result = await self._call_gemini(messages, tools, max_tokens, config)
                elif config.name == "openai":
                    result = await self._call_openai(messages, tools, max_tokens, config)
                else:
                    return None
                elapsed = int((time.monotonic() - start) * 1000)
                if result:
                    result.latency_ms = elapsed
                return result
            except (httpx.TimeoutException, httpx.ConnectError, asyncio.TimeoutError) as e:
                if attempt < config.max_retries:
                    logger.info("Retry %d for %s: %s", attempt + 1, config.name, type(e).__name__)
                    await asyncio.sleep(config.retry_delay_s * (attempt + 1))
                else:
                    raise
        return None

    async def _call_ollama(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> LLMResponse | None:
        """Call local Ollama instance."""
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools

        resp = await self._http.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
            timeout=config.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()

        content = data.get("message", {}).get("content", "")
        tool_calls = data.get("message", {}).get("tool_calls")

        return LLMResponse(content=content, provider="ollama", tool_calls=tool_calls)

    async def _call_gemini(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> LLMResponse | None:
        """Call Google Gemini API."""
        contents = self._messages_to_gemini_format(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if tools:
            payload["tools"] = [{"functionDeclarations": self._tools_to_gemini(tools)}]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}"
            f":generateContent?key={settings.GEMINI_API_KEY}"
        )
        resp = await self._http.post(url, json=payload, timeout=config.timeout_s)
        resp.raise_for_status()
        data = resp.json()

        # Parse response
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        content = ""
        tool_calls = []
        for part in parts:
            if "text" in part:
                content += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": f"call_{hashlib.md5(fc['name'].encode()).hexdigest()[:8]}",
                    "type": "function",
                    "function": {"name": fc["name"], "arguments": json.dumps(fc.get("args", {}))}
                })

        return LLMResponse(
            content=content,
            provider="gemini",
            tool_calls=tool_calls if tool_calls else None,
        )

    async def _call_openai(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> LLMResponse | None:
        """Call OpenAI API (non-streaming)."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=config.timeout_s)
        kwargs = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=config.timeout_s,
        )
        choice = response.choices[0]
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in choice.message.tool_calls
            ]
        return LLMResponse(
            content=choice.message.content or "",
            provider="openai",
            tool_calls=tool_calls,
        )

    # ── Streaming implementations ──

    async def _stream_ollama(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools

        async with self._http.stream(
            "POST", f"{settings.OLLAMA_URL}/api/chat", json=payload, timeout=config.timeout_s
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield json.dumps({"type": "text", "content": content})
                if data.get("done"):
                    break

    async def _stream_gemini(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> AsyncGenerator[str, None]:
        contents = self._messages_to_gemini_format(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if tools:
            payload["tools"] = [{"functionDeclarations": self._tools_to_gemini(tools)}]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}"
            f":streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
        )
        async with self._http.stream("POST", url, json=payload, timeout=config.timeout_s) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        yield json.dumps({"type": "text", "content": part["text"]})

    async def _stream_openai(
        self, messages: list[dict], tools: list[dict] | None, max_tokens: int, config: ProviderConfig
    ) -> AsyncGenerator[str, None]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=config.timeout_s)
        kwargs = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await asyncio.wait_for(
            client.chat.completions.create(**kwargs),
            timeout=config.timeout_s,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield json.dumps({"type": "text", "content": delta.content})
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield json.dumps({"type": "tool_call_delta", "data": {
                        "index": tc.index,
                        "id": tc.id,
                        "name": tc.function.name if tc.function else None,
                        "arguments": tc.function.arguments if tc.function else None,
                    }})

    # ── Cache ──

    async def _cache_response(self, messages: list[dict], response: LLMResponse):
        if not self.redis or not response.content:
            return
        key = CACHE_PREFIX + self._cache_key(messages)
        value = json.dumps({"content": response.content, "provider": response.provider})
        try:
            await self.redis.setex(key, CACHE_TTL, value)
        except Exception:
            pass

    async def _get_cached_response(self, messages: list[dict]) -> LLMResponse | None:
        if not self.redis:
            return None
        key = CACHE_PREFIX + self._cache_key(messages)
        try:
            data = await self.redis.get(key)
            if data:
                parsed = json.loads(data)
                return LLMResponse(content=parsed["content"], provider="cache")
        except Exception:
            pass
        return None

    def _cache_key(self, messages: list[dict]) -> str:
        # Hash last user message + system prompt hash for cache key
        user_msgs = [m["content"] for m in messages if m.get("role") == "user" and m.get("content")]
        key_source = user_msgs[-1] if user_msgs else ""
        return hashlib.sha256(key_source.encode()).hexdigest()[:16]

    # ── Format converters ──

    def _messages_to_gemini_format(self, messages: list[dict]) -> list[dict]:
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if not content:
                continue
            if role == "system":
                contents.append({"role": "user", "parts": [{"text": f"[System]: {content}"}]})
                contents.append({"role": "model", "parts": [{"text": "Understood."}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})
        return contents

    def _tools_to_gemini(self, tools: list[dict]) -> list[dict]:
        declarations = []
        for tool in tools:
            fn = tool.get("function", {})
            declarations.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
        return declarations
