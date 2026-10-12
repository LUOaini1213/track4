"""Validate the recorded MiniLM files before any Transformers load.

The committed manifest is bound to this module by SHA-256. Local files cannot
authorize themselves by writing a new manifest. No model package is imported.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_HUB_ID = "sentence-transformers/all-MiniLM-L6-v2"
HUB_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
WEIGHTS_SHA256 = "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
MANIFEST_SHA256 = "ad1b805bac91feb0a675354caf7bfdc772165e0c8ea849b7fd1e7545012f7fb1"
MINILM_FILES = ("config.json", "model.safetensors", "tokenizer.json",
                "tokenizer_config.json", "special_tokens_map.json", "vocab.txt")
# These can override the validated single-file checkpoint/tokenizer recipe.
_OVERRIDES = ("added_tokens.json", "tokenizer.model", "spiece.model",
              "model.safetensors.index.json")


class CheckpointError(ValueError):
    """Only generic reasons and allowlisted filenames, never local paths."""


def manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "minilm-manifest.json"


def load_manifest() -> dict:
    try:
        with manifest_path().open("rb") as handle:
            raw = handle.read(16385)
    except OSError as exc:
        raise CheckpointError("Trusted MiniLM manifest is missing") from exc
    if len(raw) > 16384 or hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise CheckpointError("Trusted MiniLM manifest hash mismatch")
    try:
        value = json.loads(raw)
        if (value["schema"] != 1 or value["repo_id"] != DEFAULT_HUB_ID or
            value["revision"] != HUB_REVISION or set(value["files"]) != set(MINILM_FILES) or
            value["files"]["model.safetensors"]["sha256"] != WEIGHTS_SHA256):
            raise ValueError("identity")
    except (ValueError, KeyError, TypeError) as exc:
        raise CheckpointError("Trusted MiniLM manifest schema/identity mismatch") from exc
    return value


def _validate_files(directory: Path, expected: dict) -> None:
    """Separate pure helper for synthetic tests; production uses load_manifest."""
    if not directory.is_dir():
        raise CheckpointError("MiniLM checkpoint directory is missing")
    for name in _OVERRIDES:
        if (directory / name).exists():
            raise CheckpointError("Unexpected MiniLM override file: " + name)
    for name in MINILM_FILES:
        path = directory / name
        try:
            before = path.stat()
            if not path.is_file():
                raise OSError("not a file")
            if before.st_size != expected[name]["bytes"]:
                raise CheckpointError("MiniLM file size mismatch: " + name)
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.stat()
        except OSError as exc:
            raise CheckpointError("MiniLM file is missing or unreadable: " + name) from exc
        if ((before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise CheckpointError("MiniLM file changed while validating: " + name)
        if digest.hexdigest() != expected[name]["sha256"]:
            raise CheckpointError("MiniLM file hash mismatch: " + name)


def validate_checkpoint(directory: str | Path) -> dict:
    manifest = load_manifest()
    _validate_files(Path(directory), manifest["files"])
    return {"status": "verified", "repo_id": DEFAULT_HUB_ID,
            "revision": HUB_REVISION, "manifest_sha256": MANIFEST_SHA256,
            "files_checked": len(MINILM_FILES)}
