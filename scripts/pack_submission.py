#!/usr/bin/env python3
"""Build a clean Devpost ZIP. Does not change E123 or rank().

GitHub keeps holdout JSON and agent-tooling dirs. The ZIP does not.
Requires MiniLM sidecar; vendors it if missing.
"""

from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "submission_dist"
STAGE = DIST / "bytesize-track4"
ZIP_PATH = DIST / "bytesize-track4.zip"

INCLUDE_FILES = [
    "README.md",
    "requirements.txt",
    "DATA_ATTRIBUTION.md",
    "SUBMISSION_CHECKLIST.md",
    "starter/agent.py",
    "starter/__init__.py",
    "evaluator/__init__.py",
    "evaluator/local_evaluator.py",
    "demo/__init__.py",
    "demo/run_demo.py",
    "docs/agent_api_contract.json",
    "docs/competition_specification.md",
    "docs/submission_rules.md",
    "docs/evaluation_config.json",
    "report/freeze.md",
    "report/architecture.md",
    "report/submit.md",
    "report/attribution.md",
    "report/robustness.md",
    "report/complete_agent.md",
    "models/README.md",
    "scripts/vendor_minilm.py",
    "data/public_set.jsonl",
    "data/README.md",
]

INCLUDE_GLOBS = [
    "starter/shopping_agent/contest_*.py",
    "starter/shopping_agent/__init__.py",
]

# Hugging Face snapshot also ships ONNX/TF/PyTorch duplicates (~800MB).
# ContestAgent only loads AutoModel + AutoTokenizer.
MINILM_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from starter.shopping_agent.contest_dense import is_transformers_dir, snapshot_dir

    snap = snapshot_dir()
    if not is_transformers_dir(snap):
        print("MiniLM sidecar missing; running vendor_minilm.py", flush=True)
        import subprocess

        code = subprocess.call([sys.executable, str(ROOT / "scripts" / "vendor_minilm.py")], cwd=ROOT)
        if code != 0:
            print("cannot pack without MiniLM weights", file=sys.stderr)
            return 1
    if not is_transformers_dir(snap):
        print(f"still no transformers dir at {snap}", file=sys.stderr)
        return 1

    if DIST.exists():
        shutil.rmtree(DIST)
    STAGE.mkdir(parents=True)

    for rel in INCLUDE_FILES:
        src = ROOT / rel
        if src.is_file():
            _copy_file(src, STAGE / rel)

    for pattern in INCLUDE_GLOBS:
        for src in ROOT.glob(pattern):
            if src.is_file():
                _copy_file(src, STAGE / src.relative_to(ROOT))

    dest_models = STAGE / "models" / "all-MiniLM-L6-v2"
    dest_models.mkdir(parents=True, exist_ok=True)
    for name in MINILM_FILES:
        src = snap / name
        if not src.is_file():
            print(f"missing MiniLM file {src}", file=sys.stderr)
            return 1
        shutil.copy2(src, dest_models / name)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in STAGE.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(DIST).as_posix())

    weights = dest_models / "model.safetensors"
    print(f"zip: {ZIP_PATH}")
    print(f"bytes: {ZIP_PATH.stat().st_size}")
    print(f"minilm: {weights.is_file()} {weights}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
