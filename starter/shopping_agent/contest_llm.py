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


def _api_key() -> str:
    for name in (
        "SHOPPING_AGENT_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY",
        "TECHJAM_LLM_KEY",
    ):
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    path = Path.home() / "Desktop" / ".env"
    try:
        raw = path.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return ""
    if not raw:
        return ""
    first = raw.splitlines()[0].strip()
    if "=" in first:
        first = first.split("=", 1)[1].strip()
    return first.strip().strip('"').strip("'")


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
    model = (os.environ.get("SHOPPING_AGENT_DEEPSEEK_MODEL") or "deepseek-v4-flash").strip()
    backend = DeepSeekAPIBackend(key, model=model, timeout_seconds=max(timeout, 1.0))
    response = backend.complete(messages, temperature=0.0, max_tokens=256)
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
