"""Listing a provider's models fails with a message that says what to do, not with an exception."""

import socket

import httpx
import pytest

from tuttle import llm
from tuttle.app.core.dispatch import dispatch


@pytest.fixture
def closed_url():
    """A local address where nothing listens: connecting is refused."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def answering(status: int, payload: dict | None = None):
    """Stands in for httpx.get: the provider answers with *status*."""

    def get(url, **kwargs):
        return httpx.Response(status, json=payload or {}, request=httpx.Request("GET", url))

    return get


def test_ollama_not_running(closed_url):
    res = dispatch("llm.get_models", {"base_url": closed_url, "provider": "ollama"})
    assert res["ok"] is False
    assert res["error"] == f"Ollama isn't running at {closed_url}. Start Ollama, or choose another provider."


def test_nothing_at_the_providers_url(closed_url):
    res = dispatch("llm.get_models", {"base_url": closed_url, "provider": "openai"})
    assert res["ok"] is False
    assert res["error"] == f"Nothing answers at {closed_url}. Check the URL and your internet connection."


@pytest.mark.parametrize("status", [401, 403])
def test_key_refused(monkeypatch, status):
    monkeypatch.setattr(llm.httpx, "get", answering(status))
    res = dispatch("llm.get_models", {"base_url": "https://api.example.com/v1", "provider": "openai", "api_key": "x"})
    assert res["ok"] is False
    assert res["error"] == "The provider refused the API key. Check the key."


def test_url_without_model_list(monkeypatch):
    monkeypatch.setattr(llm.httpx, "get", answering(404))
    res = dispatch("llm.get_models", {"base_url": "https://api.example.com", "provider": "openai"})
    assert res["ok"] is False
    assert "Check the URL: it usually ends in /v1." in res["error"]


def test_models_listed(monkeypatch):
    monkeypatch.setattr(llm.httpx, "get", answering(200, {"models": [{"name": "qwen3:8b"}, {"size": 1}]}))
    assert dispatch("llm.get_models", {"base_url": "http://localhost:11434"})["data"] == ["qwen3:8b"]
    monkeypatch.setattr(llm.httpx, "get", answering(200, {"data": [{"id": "gpt-x"}]}))
    assert dispatch("llm.get_models", {"base_url": "https://api.example.com/v1", "provider": "openai"})["data"] == ["gpt-x"]
