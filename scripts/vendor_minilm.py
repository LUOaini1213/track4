#!/usr/bin/env python3
"""Copy the frozen MiniLM checkpoint into models/all-MiniLM-L6-v2.

Does not change the encoder. Uses the local Hugging Face cache when present,
otherwise downloads sentence-transformers/all-MiniLM-L6-v2 at the pinned
revision. Apache-2.0; do not git-commit the snapshot. Include it in the
Devpost package if the scoring host may be offline.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starter.shopping_agent.contest_checkpoint import MINILM_FILES, validate_checkpoint, CheckpointError, load_manifest
from starter.shopping_agent.contest_dense import (  # noqa: E402
    DEFAULT_HUB_ID,
    HUB_REVISION,
    WEIGHTS_SHA256,
    snapshot_dir,
)


def main() -> int:
    try:
        load_manifest()
    except CheckpointError as exc:
        print("MiniLM trust validation failed: " + str(exc), file=sys.stderr)
        return 1
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
            allow_patterns=list(MINILM_FILES),
            local_files_only=True,
        )
    except Exception:
        snapshot_download(
            repo_id=DEFAULT_HUB_ID,
            revision=HUB_REVISION,
            local_dir=str(dest),
            allow_patterns=list(MINILM_FILES),
        )
    try:
        proof = validate_checkpoint(dest)
    except CheckpointError as exc:
        print("MiniLM validation failed: " + str(exc), file=sys.stderr)
        return 1
    print("snapshot: " + str(dest))
    print("revision: " + str(proof["revision"]))
    print("model.safetensors sha256: " + WEIGHTS_SHA256)
    print("verified files: " + str(proof["files_checked"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
