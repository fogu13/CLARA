from __future__ import annotations

import json
from typing import Any

import pytest

_TEST_TOOL = {"type": "function", "function": {"name": "t"}}


def _call(ai, **kw):
    """Shorthand to call_tool with the default test tool."""
    defaults = dict(system="s", user="u", tool=_TEST_TOOL, tool_name="t")
    defaults.update(kw)
    return ai.call_tool(**defaults)


def _ai_response(tool_arguments: dict[str, Any], model: str = "test-model") -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "test_tool",
                                "arguments": json.dumps(tool_arguments),
                            }
                        }
                    ]
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _embeddings_response(vectors: list[list[float]]) -> dict[str, Any]:
    return {
        "data": [{"embedding": v, "index": i} for i, v in enumerate(vectors)],
        "usage": {"prompt_tokens": 8, "total_tokens": 8},
    }


@pytest.fixture
def _clean_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure predictable AI config + no Langfuse tracing during tests."""
    monkeypatch.setenv("AI_BASE_URL", "http://test-ai.local/v1")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_EMBED_MODEL", "test-embed")
    monkeypatch.setenv("AI_EMBED_DIM", "768")
    # Must be set, not merely absent: the reload below re-runs load_dotenv, and
    # anything missing from os.environ gets filled in from the developer's real
    # apps/api/.env — which would silently point embed tests at a live provider.
    monkeypatch.setenv("AI_EMBED_BASE_URL", "")
    monkeypatch.setenv("AI_EMBED_API_KEY", "")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    import importlib

    import app.services.ai as ai_mod

    importlib.reload(ai_mod)


class TestCallTool:
    def test_returns_parsed_tool_arguments(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_response({"sentiment": "negative", "urgency": "high"}),
        )

        result = ai.call_tool(
            system="You are a classifier.",
            user="The app crashed again.",
            tool={
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            tool_name="test_tool",
        )

        assert result == {"sentiment": "negative", "urgency": "high"}

    def test_sends_forced_tool_choice(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_response({"result": "ok"}),
        )

        _call(ai)

        request = httpx_mock.get_requests()[-1]
        body = json.loads(request.read())
        assert body["tool_choice"] == {"type": "function", "function": {"name": "t"}}
        assert body["tools"] == [{"type": "function", "function": {"name": "t"}}]
        assert body["model"] == "test-model"

    def test_raises_no_structured_response_when_missing(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"tool_calls": []}}]},
        )

        with pytest.raises(ai.NoStructuredResponseError):
            _call(ai)

    def test_rate_limit_error_on_429(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services import ai

        monkeypatch.setattr("time.sleep", lambda _: None)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            status_code=429,
            text="rate limited",
            is_reusable=True,
        )

        with pytest.raises(ai.RateLimitError) as exc_info:
            _call(ai)

        assert exc_info.value.status == 429
        # a persistent 429 is retried to exhaustion before it surfaces
        assert len(httpx_mock.get_requests()) == 3

    def test_transient_429_is_retried_then_succeeds(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services import ai

        monkeypatch.setattr("time.sleep", lambda _: None)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            status_code=429,
            text="rate limited",
        )
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_response({"sentiment": "negative"}),
        )

        assert _call(ai) == {"sentiment": "negative"}
        assert len(httpx_mock.get_requests()) == 2

    def test_empty_choices_raises_no_structured_response(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json={"choices": []},
        )

        with pytest.raises(ai.NoStructuredResponseError):
            _call(ai)

    def test_quota_error_on_402(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            status_code=402,
            text="payment required",
        )

        with pytest.raises(ai.QuotaError) as exc_info:
            _call(ai)

        assert exc_info.value.status == 402

    def test_generic_error_on_500(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services import ai

        monkeypatch.setattr("time.sleep", lambda _: None)
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            status_code=500,
            text="internal server error",
            is_reusable=True,
        )

        with pytest.raises(ai.AIProviderError) as exc_info:
            _call(ai)

        assert exc_info.value.status == 500
        assert not isinstance(exc_info.value, (ai.RateLimitError, ai.QuotaError))


class TestEmbed:
    def test_returns_embeddings_for_single_string(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/embeddings",
            method="POST",
            json=_embeddings_response([[0.1, 0.2, 0.3]]),
        )

        result = ai.embed("hello world")

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]

    def test_returns_embeddings_for_multiple_strings(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/embeddings",
            method="POST",
            json=_embeddings_response([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]),
        )

        result = ai.embed(["a", "b", "c"])

        assert len(result) == 3
        assert result[1] == [0.3, 0.4]

    def test_sends_dimensions_param(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/embeddings",
            method="POST",
            json=_embeddings_response([[0.1]]),
        )

        ai.embed("test")

        request = httpx_mock.get_requests()[-1]
        body = json.loads(request.read())
        assert body["dimensions"] == 768
        assert body["model"] == "test-embed"

    def test_runtime_embed_model_override_skips_dimensions(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        # A GUI-selected embed model gets the provider's default dims — the
        # env AI_EMBED_DIM belongs to the env-configured model only (Mistral
        # 422s on an unexpected `dimensions` param).
        from app.services import ai

        ai.set_runtime_config(embed_model="mistral-embed")
        try:
            httpx_mock.add_response(
                url="http://test-ai.local/v1/embeddings",
                method="POST",
                json=_embeddings_response([[0.1]]),
            )

            ai.embed("test")

            body = json.loads(httpx_mock.get_requests()[-1].read())
            assert body["model"] == "mistral-embed"
            assert "dimensions" not in body
        finally:
            ai.set_runtime_config()


class TestSplitEmbedProvider:
    """Chat-only gateways exist (OpenCode Zen 404s on /embeddings), so
    embeddings must be able to point at their own host and key."""

    def test_unset_keeps_embeddings_on_the_chat_host(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services import ai

        assert ai.effective_embed_base_url() == ai.effective_base_url()
        httpx_mock.add_response(
            url="http://test-ai.local/v1/embeddings", method="POST",
            json=_embeddings_response([[0.1]]),
        )
        ai.embed("test")

    def test_embeddings_go_to_their_own_host_with_their_own_key(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services import ai

        monkeypatch.setenv("AI_EMBED_BASE_URL", "https://api.mistral.ai/v1")
        monkeypatch.setenv("AI_EMBED_API_KEY", "embed-key")
        monkeypatch.setenv("AI_API_KEY", "chat-key")

        httpx_mock.add_response(
            url="https://api.mistral.ai/v1/embeddings", method="POST",
            json=_embeddings_response([[0.1]]),
        )
        ai.embed("test")

        request = httpx_mock.get_requests()[-1]
        assert request.headers["Authorization"] == "Bearer embed-key"

    def test_chat_key_is_not_leaked_to_a_different_embed_provider(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A split host with no AI_EMBED_API_KEY must send NO key — forwarding the
        # chat provider's credential to a third party would be a leak.
        from app.services import ai

        monkeypatch.setenv("AI_EMBED_BASE_URL", "https://api.mistral.ai/v1")
        monkeypatch.setenv("AI_API_KEY", "chat-key")
        monkeypatch.delenv("AI_EMBED_API_KEY", raising=False)

        httpx_mock.add_response(
            url="https://api.mistral.ai/v1/embeddings", method="POST",
            json=_embeddings_response([[0.1]]),
        )
        ai.embed("test")

        assert "Authorization" not in httpx_mock.get_requests()[-1].headers

    def test_embed_failure_names_the_embed_knobs_not_the_chat_ones(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The exact case that cost a debugging session: a chat-only gateway
        # 404s on /embeddings, and the message must say so.
        from app.services import ai

        monkeypatch.setenv("AI_EMBED_BASE_URL", "https://opencode.ai/zen/v1")
        httpx_mock.add_response(
            url="https://opencode.ai/zen/v1/embeddings", method="POST",
            status_code=404, text="<!DOCTYPE html>",
        )
        with pytest.raises(ai.AIProviderError) as caught:
            ai.embed("test")

        detail = ai.provider_error_detail(caught.value)
        assert "opencode.ai" in detail
        assert "AI_EMBED_BASE_URL" in detail
        assert "no /embeddings endpoint" in detail
        assert "AI_MODEL" not in detail


class TestErrorAttribution:
    """Which call failed comes from the error, not from comparing hosts."""

    def test_chat_401_names_chat_key_even_when_both_hosts_match(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The production incident: a Settings override moved chat onto the embed
        # host, so host-equality inference could not tell the calls apart.
        from app.services import ai

        monkeypatch.setenv("AI_EMBED_BASE_URL", "http://test-ai.local/v1")
        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions", method="POST",
            status_code=401, json={"detail": "Invalid API Key"},
        )
        with pytest.raises(ai.AIProviderError) as caught:
            ai.call_tool(system="s", user="u", tool={"name": "t"}, tool_name="t")

        assert caught.value.endpoint == "chat"
        assert "AI_API_KEY" in ai.provider_error_detail(caught.value)

    def test_embed_401_names_the_embed_key_only_when_split(
        self, _clean_ai_env: None, httpx_mock: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.services import ai

        monkeypatch.setenv("AI_EMBED_BASE_URL", "https://api.mistral.ai/v1")
        monkeypatch.setenv("AI_EMBED_API_KEY", "bad")
        httpx_mock.add_response(
            url="https://api.mistral.ai/v1/embeddings", method="POST",
            status_code=401, json={"detail": "Invalid API Key"},
        )
        with pytest.raises(ai.AIProviderError) as caught:
            ai.embed("x")

        assert caught.value.endpoint == "embeddings"
        assert "AI_EMBED_API_KEY" in ai.provider_error_detail(caught.value)

    def test_embed_401_names_the_chat_key_when_not_split(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        # No AI_EMBED_BASE_URL: embeddings authenticate with the chat key, so
        # AI_EMBED_API_KEY would be the wrong thing to tell someone to check.
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/embeddings", method="POST",
            status_code=401, json={"detail": "nope"},
        )
        with pytest.raises(ai.AIProviderError) as caught:
            ai.embed("x")

        detail = ai.provider_error_detail(caught.value)
        assert "AI_API_KEY" in detail and "AI_EMBED_API_KEY" not in detail

    def test_settings_override_is_called_out(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        # Telling someone to check AI_BASE_URL is useless while a GUI override
        # wins — the message has to say where the value actually comes from.
        from app.services import ai

        ai.set_runtime_config(base_url="http://gui.local/v1", model="gui-model")
        try:
            httpx_mock.add_response(
                url="http://gui.local/v1/chat/completions", method="POST",
                status_code=401, json={"detail": "nope"},
            )
            with pytest.raises(ai.AIProviderError) as caught:
                ai.call_tool(system="s", user="u", tool={"name": "t"}, tool_name="t")

            detail = ai.provider_error_detail(caught.value)
            assert "Settings page" in detail
            assert "base_url" in detail and "model" in detail
        finally:
            ai.set_runtime_config()

    def test_no_override_note_when_env_is_authoritative(
        self, _clean_ai_env: None, httpx_mock: Any
    ) -> None:
        from app.services import ai

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions", method="POST",
            status_code=401, json={"detail": "nope"},
        )
        with pytest.raises(ai.AIProviderError) as caught:
            ai.call_tool(system="s", user="u", tool={"name": "t"}, tool_name="t")

        assert "Settings page" not in ai.provider_error_detail(caught.value)


class TestLocalFirstKeyless:
    """Local-first is a hard requirement: Ollama/vLLM must work without an API key."""

    def test_no_authorization_header_when_key_empty(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        assert ai.AI_API_KEY == ""

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_response({"ok": True}),
        )

        _call(ai)

        request = httpx_mock.get_requests()[-1]
        assert "authorization" not in {k.lower() for k in request.headers.keys()}

    def test_authorization_header_when_key_set(self, monkeypatch: pytest.MonkeyPatch, httpx_mock: Any) -> None:
        monkeypatch.setenv("AI_BASE_URL", "http://test-ai.local/v1")
        monkeypatch.setenv("AI_API_KEY", "sk-test-key-123")
        monkeypatch.setenv("AI_MODEL", "gpt-4o-mini")
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

        import importlib

        import app.services.ai as ai_mod

        importlib.reload(ai_mod)

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_mod_response(),
        )

        ai_mod.call_tool(system="s", user="u", tool={"type": "function", "function": {"name": "t"}}, tool_name="t")

        request = httpx_mock.get_requests()[-1]
        assert request.headers.get("authorization") == "Bearer sk-test-key-123"


def _ai_mod_response() -> dict[str, Any]:
    return {
        "choices": [
            {"message": {"tool_calls": [{"function": {"name": "t", "arguments": '{"ok": true}'}}]}}
        ],
        "usage": {},
    }


class TestVectorLiteral:
    def test_formats_for_pgvector(self, _clean_ai_env: None) -> None:
        from app.services import ai

        result = ai.to_vector_literal([0.1, 0.2, 0.3])
        assert result == "[0.1,0.2,0.3]"

    def test_empty_vector(self, _clean_ai_env: None) -> None:
        from app.services import ai

        assert ai.to_vector_literal([]) == "[]"


class TestLangfuseGracefulDegradation:
    """Langfuse must be optional: no crash when unconfigured."""

    def test_get_langfuse_returns_none_when_unconfigured(self, _clean_ai_env: None) -> None:
        from app.services import ai

        assert ai._get_langfuse() is None

    def test_call_tool_works_without_langfuse(self, _clean_ai_env: None, httpx_mock: Any) -> None:
        from app.services import ai

        assert ai._get_langfuse() is None

        httpx_mock.add_response(
            url="http://test-ai.local/v1/chat/completions",
            method="POST",
            json=_ai_response({"ok": True}),
        )

        result =             _call(ai)
        assert result == {"ok": True}
