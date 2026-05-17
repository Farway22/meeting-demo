"""最小 OpenAI 兼容 Chat Completions 调用（支持 Streamlit secrets / 环境变量）。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _chat_completions_url(base: str) -> str:
    b = base.rstrip("/")
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    return f"{b}/v1/chat/completions"


def get_llm_config() -> dict[str, str]:
    """读取 LLM 配置，优先级：Streamlit secrets > 环境变量 > 默认值。"""
    api_key = ""
    base_url = "https://api.openai.com/v1"
    model = "gpt-4o-mini"

    try:
        import streamlit as st  # type: ignore

        secrets = getattr(st, "secrets", {}) or {}
        api_key = str(secrets.get("OPENAI_API_KEY", "") or secrets.get("api_key", "") or "").strip()
        base_url = str(secrets.get("OPENAI_BASE_URL", "") or secrets.get("base_url", "") or base_url).strip()
        model = str(secrets.get("OPENAI_MODEL", "") or secrets.get("model", "") or model).strip()
    except Exception:
        pass

    api_key = api_key or (os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (os.environ.get("OPENAI_BASE_URL") or base_url or "https://api.openai.com/v1").strip()
    model = (os.environ.get("OPENAI_MODEL") or model or "gpt-4o-mini").strip()
    return {"api_key": api_key, "base_url": base_url, "model": model}


def call_llm(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.2,
) -> str:
    """
    调用 LLM，返回助手文本内容（不含 JSON 解析）。

    配置优先级：
    - Streamlit secrets
    - 环境变量
    - 默认值
    """
    cfg = get_llm_config()
    api_key = cfg["api_key"]
    if not api_key:
        return ""

    base = cfg["base_url"]
    model = cfg["model"]

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        _chat_completions_url(base),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError):
        return ""

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    if content is None:
        return ""
    return str(content).strip()
