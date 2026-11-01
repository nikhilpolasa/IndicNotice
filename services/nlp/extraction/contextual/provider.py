"""HTTP chat-completion provider with no vendor SDK dependency."""

from __future__ import annotations

import json
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ProviderTimeout, ProviderUnavailable
from .types import ModelRequest, ModelResponse


class HTTPChatProvider:
    """OpenAI-style JSON chat adapter suitable for local or remote providers."""

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        api_key: str | None = None,
        temperature: float = 0.2,
        top_p: float = 0.8,
        presence_penalty: float = 0.0,
        seed: int = 42,
        max_tokens: int = 4096,
        enable_thinking: bool | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._model_id = model_id
        self.api_key = api_key
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.seed = seed
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking

    @property
    def model_id(self) -> str:
        return self._model_id

    def complete(self, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": self.model_id,
            "messages": list(request.messages),
            "temperature": self.temperature,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "indicnotice_chunk_v1",
                    "strict": True,
                    "schema": request.response_schema,
                },
            },
        }
        if self.enable_thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": self.enable_thinking}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        http_request = Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(http_request, timeout=request.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise ProviderTimeout(
                f"Provider {self.base_url!r} timed out after {request.timeout_seconds}s."
            ) from exc
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise ProviderUnavailable(f"Provider returned HTTP {exc.code}: {detail}") from exc
        except (URLError, OSError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable(f"Provider request failed: {exc}") from exc
        latency = time.perf_counter() - started
        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderUnavailable("Provider response did not contain chat completion content.") from exc
        usage = body.get("usage") or {}
        return ModelResponse(
            text=content,
            latency_seconds=latency,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
        )
