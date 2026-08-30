"""Optional listwise LLM reorder of a hard-pool shortlist.

Runs only after verbatim AND already produced a recommendation list.
Missing credentials, timeout, or a bad permutation leaves the current
ranking unchanged. Official scoring may have network; kit docs still allow
the organizer to disable it, so ContestAgent PUBLIC keeps this off.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from .contest_index import ContestIndex
from .contest_slots import ContestState

CompleteFn = Callable[[list[dict[str, str]]], tuple[str, dict[str, int]]]

_ARRAY_RE = re.compile(r"\[[^\[\]]*\]", re.S)
_COMPLETE: CompleteFn | None = None


def set_completer(fn: CompleteFn | None) -> None:
    global _COMPLETE
    _COMPLETE = fn


def _dotenv_map() -> dict[str, str]:
    path = Path.home() / "Desktop" / ".env"
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    mapped: dict[str, str] = {}
    for line in raw.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if "=" in text:
            name, value = text.split("=", 1)
            mapped[name.strip()] = value.strip().strip('"').strip("'")
        elif "FIRSTLINE" not in mapped:
            mapped["FIRSTLINE"] = text.strip('"').strip("'")
    return mapped


def _api_key() -> str:
    """Prefer contest-specific names, then Desktop .env, then generic env.

    A stale process-level ``DEEPSEEK_API_KEY`` must not hide a valid
    ``Desktop/.env`` key used for local scoring.
    """

    dotenv = _dotenv_map()
    ordered = [
        (os.environ.get("SHOPPING_AGENT_DEEPSEEK_API_KEY") or "").strip(),
        (os.environ.get("TECHJAM_LLM_KEY") or "").strip(),
        dotenv.get("SHOPPING_AGENT_DEEPSEEK_API_KEY", ""),
        dotenv.get("TECHJAM_LLM_KEY", ""),
        dotenv.get("DEEPSEEK_API_KEY", ""),
        dotenv.get("FIRSTLINE", ""),
        (os.environ.get("DEEPSEEK_API_KEY") or "").strip(),
    ]
    for source in ordered:
        if source:
            return source
    return ""


def _usage(prompt: int = 0, completion: int = 0) -> dict[str, int]:
    prompt = max(int(prompt), 0)
    completion = max(int(completion), 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def _card(index: ContestIndex, idx: int) -> str:
    title = (index.titles[idx] or "")[:140]
    lines = getattr(index, "field_lines", None)
    extra = ""
    if lines and idx < len(lines):
        for line in list(lines[idx])[:2]:
            if line and len(line) >= 8:
                extra = line[:120]
                break
    return f"{title} | {extra}".strip(" |")


def build_prompt(index: ContestIndex, state: ContestState, pool: Sequence[int]) -> str:
    constraints = "; ".join(item.text for item in state.active) or "none"
    lines = "\n".join(f"{i + 1}. {_card(index, idx)}" for i, idx in enumerate(pool))
    n = len(pool)
    return (
        "Rank catalog products for one shopper. Prefer the single item that "
        "matches every stated requirement; popularity is already applied.\n"
        f"Category: {state.category or 'unknown'}.\n"
        f"Requirements: {constraints}.\n"
        f"Candidates:\n{lines}\n"
        f'Return ONLY JSON {{"order": [..]}} using each index 1..{n} once, best first.'
    )


def parse_order(text: str, n: int) -> list[int] | None:
    if n < 2:
        return None
    blob = text.strip() if isinstance(text, str) else ""
    if not blob:
        return None
    payload: object
    try:
        payload = json.loads(blob)
    except json.JSONDecodeError:
        match = _ARRAY_RE.search(blob)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if isinstance(payload, dict):
        payload = payload.get("order") or payload.get("ranking") or payload.get("ids")
    if not isinstance(payload, list):
        return None
    order: list[int] = []
    seen: set[int] = set()
    for item in payload:
        try:
            value = int(item)
        except (TypeError, ValueError):
            return None
        if value < 1 or value > n or value in seen:
            return None
        seen.add(value)
        order.append(value - 1)
    if len(order) != n:
        return None
    return order


def _complete_http(messages: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
    from .model import DeepSeekAPIBackend, _coerce_usage

    key = _api_key()
    if not key:
        return "", _usage()
    timeout = float(os.environ.get("SHOPPING_AGENT_MODEL_TIMEOUT_SECONDS") or 6)
    preferred = (os.environ.get("SHOPPING_AGENT_DEEPSEEK_MODEL") or "deepseek-chat").strip()
    models = [preferred]
    if "deepseek-chat" not in models:
        models.append("deepseek-chat")
    last_error: Exception | None = None
    response = None
    for model in models:
        try:
            backend = DeepSeekAPIBackend(key, model=model, timeout_seconds=max(timeout, 1.0))
            response = backend.complete(messages, temperature=0.0, max_tokens=256)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            continue
    if response is None:
        if last_error is not None:
            raise last_error
        return "", _usage()
    content = response.content
    if isinstance(content, (dict, list)):
        text = json.dumps(content, ensure_ascii=False)
    else:
        text = str(content or "")
    tokens = _coerce_usage(response.usage)
    if tokens is None:
        return text, _usage()
    return text, _usage(tokens.prompt_tokens, tokens.completion_tokens)


def listwise_rerank(
    index: ContestIndex,
    state: ContestState,
    pool: Sequence[int],
) -> tuple[list[int] | None, dict[str, int]]:
    """Return a permutation of ``pool``, or None to keep the current order."""

    if len(pool) < 2:
        return None, _usage()
    messages = [
        {"role": "system", "content": "You rank shopping catalog items. Reply with JSON only."},
        {"role": "user", "content": build_prompt(index, state, pool)},
    ]
    try:
        completer = _COMPLETE or _complete_http
        text, usage = completer(messages)
    except Exception:
        return None, _usage()
    order = parse_order(text, len(pool))
    if order is None:
        return None, usage
    return [pool[i] for i in order], usage
