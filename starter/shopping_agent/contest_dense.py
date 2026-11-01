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
from .contest_checkpoint import (CheckpointError, DEFAULT_HUB_ID, HUB_REVISION,
    WEIGHTS_SHA256, MINILM_FILES, validate_checkpoint, load_manifest)
from .contest_slots import ContestState

EncodeFn = Callable[[list[str]], list[list[float]]]

SNAPSHOT_RELATIVE = Path("models") / "all-MiniLM-L6-v2"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_dir() -> Path:
    return repo_root() / SNAPSHOT_RELATIVE


def is_transformers_dir(path: Path) -> bool:
    try:
        validate_checkpoint(path)
        return True
    except CheckpointError:
        return False


def resolve_model_source() -> str:
    """An explicitly selected invalid local source fails, rather than changing encoder."""
    env = (os.environ.get("TECHJAM_DENSE_HOME") or "").strip()
    if env:
        candidate = Path(env).expanduser()
        validate_checkpoint(candidate)
        return str(candidate)
    snap = snapshot_dir()
    if snap.exists():
        validate_checkpoint(snap)
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
        self.diagnostics: dict[str, object] = {"mode": "injected" if encode is not None else "not_loaded"}

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

    def _load_transformers(self, local_files_only: bool):
        load_manifest()  # fail before any cache/network resolver if trust data is absent
        source = self._source()
        if source == DEFAULT_HUB_ID:
            from huggingface_hub import snapshot_download
            source = snapshot_download(repo_id=DEFAULT_HUB_ID, revision=HUB_REVISION,
                allow_patterns=list(MINILM_FILES), local_files_only=local_files_only)
        elif not Path(source).is_dir():
            raise CheckpointError("Custom MiniLM model IDs are not a frozen checkpoint")
        proof = validate_checkpoint(source)
        # Validate before importing any model package; corrupted data cannot reach a loader.
        import torch
        from transformers import AutoModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True,
            revision=HUB_REVISION, trust_remote_code=False)
        model = AutoModel.from_pretrained(source, local_files_only=True,
            revision=HUB_REVISION, use_safetensors=True, trust_remote_code=False)
        model.eval()
        self.diagnostics = dict(proof, mode="verified_dense")
        return tokenizer, model, torch

    def _ensure(self) -> None:
        if self._ready is not None:
            return
        # Source validation errors are terminal for this instance. An invalid explicit
        # local directory must not trigger a network request or another checkpoint.
        try:
            source = self._source()
        except CheckpointError as exc:
            self.diagnostics = {"mode": "nodense", "reason": str(exc)}
            self._ready = False
            return
        attempts = (True,) if (self._offline_only() or Path(source).is_dir()) else (True, False)
        for local_only in attempts:
            try:
                tokenizer, model, torch = self._load_transformers(local_only)
            except CheckpointError as exc:
                self.diagnostics = {"mode": "nodense", "reason": str(exc)}
                self._ready = False
                return
            except Exception:
                continue
            self._tokenizer = tokenizer
            self._model = model
            self._torch = torch
            self._ready = True
            return
        self.diagnostics = {"mode": "nodense", "reason": "Pinned MiniLM assets or model dependencies unavailable"}
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
