"""Bridge to the local LLM (`llamafile`) health endpoint and chat page.

Only ever talks to `/v1/models` for a health check and opens the browser at the base
URL. No chat completion endpoint is ever called from this repository - the person
generates the answer themselves, in the chat page `llamafile` already serves.
"""

import json
import os
import webbrowser
from dataclasses import dataclass
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

__all__ = ["HealthStatus", "resolve_base_url", "check_health", "open_browser"]

_DEFAULT_BASE_URL = "http://127.0.0.1:8080"
_ENV_VAR = "LOCAL_LLM_BASE_URL"


@dataclass(frozen=True)
class HealthStatus:
    reachable: bool
    detail: str
    context_window: int | None


def resolve_base_url() -> str:
    base_url = os.environ.get(_ENV_VAR, _DEFAULT_BASE_URL)
    if urlparse(base_url).scheme not in ("http", "https"):
        raise ValueError(f"{_ENV_VAR} must be an http(s) URL, got: {base_url!r}")
    return base_url


def check_health(base_url: str, timeout: float = 2.0) -> HealthStatus:
    try:
        with urlopen(f"{base_url}/v1/models", timeout=timeout) as response:
            payload = json.loads(response.read())
    except (URLError, TimeoutError, ValueError) as exc:
        return HealthStatus(reachable=False, detail=str(exc), context_window=None)

    context_window = None
    data = payload.get("data") if isinstance(payload, dict) else None
    if data:
        context_window = data[0].get("meta", {}).get("n_ctx")

    return HealthStatus(reachable=True, detail="ok", context_window=context_window)


def open_browser(base_url: str) -> bool:
    try:
        return webbrowser.open(base_url)
    except Exception:
        return False
