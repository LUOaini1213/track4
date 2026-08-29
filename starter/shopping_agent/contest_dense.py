"""MiniLM cosine over a short hard-filter pool.

Coupled **after** verbatim AND: popularity stays the sort key, cosine is a
bounded tie-break on pools of size 2..80.

Load order: ``TECHJAM_DENSE_HOME`` → ``models/all-MiniLM-L6-v2`` sidecar →
Hugging Face cache → Hub (same pinned revision) if the process may use the
network. Missing torch/transformers/weights, or any encode error, leaves
ranking unchanged. That fallback is runnable, not score-equivalent.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path

from .contest_index import ContestIndex
from .contest_slots import ContestState

EncodeFn = Callable[[list[str]], list[list[float]]]

# Same checkpoint that produced Holdout Hit 0.980 / Public 0.95125.
DEFAULT_HUB_ID = "sentence-transformers/all-MiniLM-L6-v2"
HUB_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
# Hub LFS oid for model.safetensors at HUB_REVISION (90,868,376 bytes).
WEIGHTS_SHA256 = "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
SNAPSHOT_RELATIVE = Path("models") / "all-MiniLM-L6-v2"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_dir() -> Path:
    return repo_root() / SNAPSHOT_RELATIVE


def is_transformers_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / "config.json").is_file():
        return False
    return (path / "model.safetensors").is_file() or (path / "pytorch_model.bin").is_file()


def resolve_model_source() -> str:
    """Prefer a local snapshot; otherwise the pinned Hub id."""
    env = (os.environ.get("TECHJAM_DENSE_HOME") or "").strip()
    if env:
        candidate = Path(env).expanduser()
        if is_transformers_dir(candidate):
            return str(candidate)
    snap = snapshot_dir()
    if is_transformers_dir(snap):
        return str(snap)
    return DEFAULT_HUB_ID


class PoolDenseEncoder:
    """Lazy MiniLM encoder with an injectable ``encode`` for tests."""

    def __init__(
        self,
        model_name: str = DEFAULT_HUB_ID,
        *,
        encode: EncodeFn | None = None,
    ) -> None:
        self.model_name = model_name
        self.encode = encode
        self._ready: bool | None = True if encode is not None else None
        self._cache: dict[str, list[float]] = {}
        self._tokenizer = None
        self._model = None
        self._torch = None

    def available(self) -> bool:
        if self.encode is not None:
            return True
        self._ensure()
        return bool(self._ready)

    def _offline_only(self) -> bool:
        flag = os.environ.get("TECHJAM_DENSE_OFFLINE") or os.environ.get("HF_HUB_OFFLINE")
        return str(flag or "").strip().lower() in {"1", "true", "yes", "on"}

    def _source(self) -> str:
        if self.model_name != DEFAULT_HUB_ID:
            return self.model_name
        return resolve_model_source()

    def _source_is_local_dir(self) -> bool:
        try:
            return Path(self._source()).is_dir()
        except OSError:
            return False

    def _load_transformers(self, local_files_only: bool):
        import torch
        from transformers import AutoModel, AutoTokenizer

        source = self._source()
        kwargs: dict[str, object] = {"local_files_only": local_files_only}
        if not Path(source).is_dir():
            kwargs["revision"] = HUB_REVISION
        tokenizer = AutoTokenizer.from_pretrained(source, **kwargs)
        model = AutoModel.from_pretrained(source, **kwargs)
        model.eval()
        return tokenizer, model, torch

    def _ensure(self) -> None:
        if self._ready is not None:
            return
        attempts = (True,) if (self._offline_only() or self._source_is_local_dir()) else (True, False)
        for local_only in attempts:
            try:
                tokenizer, model, torch = self._load_transformers(local_only)
            except Exception:
                continue
            self._tokenizer = tokenizer
            self._model = model
            self._torch = torch
            self._ready = True
            return
        self._ready = False

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.encode is not None:
            return self.encode(texts)
        self._ensure()
        if not self._ready or self._model is None or self._tokenizer is None or self._torch is None:
            return []
        torch = self._torch
        encoded = self._tokenizer(
            [str(item)[:500] for item in texts],
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        with torch.no_grad():
            output = self._model(**encoded)
            mask = encoded["attention_mask"].unsqueeze(-1).to(output.last_hidden_state.dtype)
            summed = (output.last_hidden_state * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            emb = torch.nn.functional.normalize(summed / counts, p=2, dim=1)
        return emb.cpu().tolist()

    def vector(self, text: str) -> list[float] | None:
        key = text[:500]
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        rows = self._embed_batch([key])
        if not rows:
            return None
        self._cache[key] = rows[0]
        return rows[0]

    def pool_scores(self, query: str, docs: Sequence[str]) -> list[float] | None:
        if not docs:
            return []
        query_vec = self.vector(query)
        if query_vec is None:
            return None
        vectors: list[list[float]] = []
        for doc in docs:
            item = self.vector(doc)
            if item is None:
                return None
            vectors.append(item)
        raw = [_dot(query_vec, item) for item in vectors]
        lo = min(raw)
        hi = max(raw)
        if hi - lo < 1e-9:
            return [0.0] * len(raw)
        return [(value - lo) / (hi - lo) for value in raw]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


_ENCODER: PoolDenseEncoder | None = None


def get_encoder() -> PoolDenseEncoder:
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = PoolDenseEncoder()
    return _ENCODER


def set_encoder(encoder: PoolDenseEncoder | None) -> None:
    global _ENCODER
    _ENCODER = encoder


def dense_query(state: ContestState) -> str:
    parts = [state.category or ""]
    parts.extend(item.text for item in state.active)
    return " ".join(part for part in parts if part)[:500]


def dense_doc(index: ContestIndex, idx: int) -> str:
    return (index.titles[idx] + " " + index.blobs[idx])[:500]
