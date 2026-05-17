"""Deployment helpers for Streamlit Cloud compatibility."""
from __future__ import annotations

import os
from typing import Any


def _read_secret(key: str, default: str = "") -> str:
    try:
        import streamlit as st  # type: ignore

        value: Any = st.secrets.get(key, default)
        return str(value or default)
    except Exception:
        return default


def get_config_value(key: str, default: str = "") -> str:
    """Read configuration from Streamlit secrets, then environment variables."""
    secret_value = _read_secret(key, "")
    if secret_value:
        return secret_value
    return str(os.environ.get(key, default) or default)


def is_cloud_runtime() -> bool:
    """Best-effort Streamlit Community Cloud detection."""
    forced = (
        get_config_value("MEETINGMIND_CLOUD", "")
        or get_config_value("MEETINGMIND_CLOUD_MODE", "")
    ).strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    if forced in {"0", "false", "no", "off"}:
        return False

    return bool(
        os.environ.get("STREAMLIT_SHARING")
        or os.environ.get("STREAMLIT_SHARING_MODE")
        or os.environ.get("STREAMLIT_CLOUD")
    )


def get_app_mode() -> str:
    """``web`` = 云端（本地功能触发时提示部署）；``local`` = 完整本机功能。"""
    mode = get_config_value("MEETINGMIND_APP_MODE", "").strip().lower()
    if mode in {"web", "local"}:
        return mode
    deploy = get_config_value("MEETINGMIND_DEPLOY_MODE", "").strip().lower()
    if deploy == "cloud":
        return "web"
    if deploy == "local":
        return "local"
    return "web" if is_cloud_runtime() else "local"


def local_only_features_enabled() -> bool:
    return get_app_mode() != "web"


LOCAL_DEPLOY_HINT = """⚠️ **此功能需在本地部署后使用**

Streamlit 云端无法运行 OpenClaw Agent 或本机浏览器自动化。请在本机执行：

```bash
cd meeting-action-agent
pip install -r requirements.txt
streamlit run demo_ui.py
```

本地运行后，在「工作模式」中切换 **Agent 模式** 或 **浏览器搜索** 即可使用。"""


def local_deploy_hint(feature: str = "") -> str:
    """Return a user-facing reminder to run the app locally."""
    if feature:
        return f"{LOCAL_DEPLOY_HINT}\n\n（你尝试使用的功能：**{feature}**）"
    return LOCAL_DEPLOY_HINT
