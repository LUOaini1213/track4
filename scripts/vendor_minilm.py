#!/usr/bin/env python3
"""Copy the frozen MiniLM checkpoint into models/all-MiniLM-L6-v2.

Does not change the encoder. Uses the local Hugging Face cache when present,
otherwise downloads sentence-transformers/all-MiniLM-L6-v2 at the pinned
revision. Apache-2.0; do not git-commit the snapshot. Include it in the
Devpost package if the scoring host may be offline.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starter.shopping_agent.contest_dense import (  # noqa: E402
    DEFAULT_HUB_ID,
    HUB_REVISION,
    WEIGHTS_SHA256,
    snapshot_dir,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    dest = snapshot_dir()
    dest.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub is required (it comes with transformers).", file=sys.stderr)
        return 1
    try:
        snapshot_download(
            repo_id=DEFAULT_HUB_ID,
            revision=HUB_REVISION,
            local_dir=str(dest),
            local_files_only=True,
        )
    except Exception:
        snapshot_download(
            repo_id=DEFAULT_HUB_ID,
            revision=HUB_REVISION,
            local_dir=str(dest),
        )
    weights = dest / "model.safetensors"
    if not weights.is_file():
        weights = dest / "pytorch_model.bin"
    if not weights.is_file():
        print(f"download finished but no weights under {dest}", file=sys.stderr)
        return 1
    digest = _sha256(weights)
    print(f"snapshot: {dest}")
    print(f"revision: {HUB_REVISION}")
    print(f"{weights.name} sha256: {digest}")
    if weights.name == "model.safetensors" and digest != WEIGHTS_SHA256:
        print(
            f"sha256 mismatch: expected {WEIGHTS_SHA256} (Hub LFS at {HUB_REVISION})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
