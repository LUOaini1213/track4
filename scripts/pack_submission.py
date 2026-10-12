#!/usr/bin/env python3
"""Build a clean Devpost ZIP. Does not change E123 or rank().

GitHub keeps holdout JSON and agent-tooling dirs. The ZIP does not.
Requires a verified MiniLM sidecar; never downloads weights automatically.
"""

from __future__ import annotations

import shutil
import os
import subprocess
import tempfile
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "submission_dist"
STAGE = DIST / "bytesize-track4"
ZIP_PATH = DIST / "bytesize-track4.zip"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    "demo/fixture.py",
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
    "models/minilm-manifest.json",
    "scripts/vendor_minilm.py",
    "scripts/import_catalog.py",
    "data/public_set.jsonl",
    "data/README.md",
]

# The whole package, not just contest_*.py. starter/shopping_agent/__init__.py
# eagerly imports catalog/config/model/state/policy/... and starter/agent.py
# imports ranking/response/retrieval for LegacyAgent, so a contest_*-only ZIP
# raises ModuleNotFoundError on `from starter.agent import Agent`. Every module
# here is stdlib-only at import time; torch/transformers/flashrank are lazy.
INCLUDE_GLOBS = [
    "starter/shopping_agent/*.py",
]

# The complete, trusted load-file list is shared with runtime validation.
from starter.shopping_agent.contest_checkpoint import MINILM_FILES, validate_checkpoint, CheckpointError


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _safe_outputs() -> None:
    base = ROOT.resolve()
    expected = base / "submission_dist"
    if DIST.resolve() != expected or DIST.is_symlink():
        raise ValueError("Package output directory escapes the fixed artifact location")
    for path in (STAGE, ZIP_PATH):
        if path.parent.resolve() != expected or path.is_symlink() or not path.resolve().is_relative_to(expected):
            raise ValueError("Package output path escapes the fixed artifact location")


def _check_import(stage: Path) -> None:
    env = dict(os.environ, TECHJAM_DENSE_OFFLINE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    env.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-S", "-c",
        "from starter.agent import Agent; from pathlib import Path; import starter.agent as a; "
        "import sys; ok=Path(a.__file__).resolve().is_relative_to(Path.cwd().resolve()) and "
        "'ContestAgent' in [c.__name__ for c in Agent.__mro__]; sys.exit(0 if ok else 2)"],
        cwd=stage, env=env, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError("Staged Agent import failed; previous ZIP preserved")


def main() -> int:
    from starter.shopping_agent.contest_dense import snapshot_dir
    try:
        _safe_outputs()
        snap = snapshot_dir()
        validate_checkpoint(snap)
        DIST.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".pack-", dir=DIST) as directory:
            temporary = Path(directory)
            if temporary.resolve().parent != DIST.resolve():
                raise ValueError("Temporary package directory escapes artifact location")
            candidate = temporary / STAGE.name
            candidate.mkdir()
            for rel in INCLUDE_FILES:
                src = ROOT / rel
                if not src.is_file() or not src.resolve().is_relative_to(ROOT.resolve()):
                    raise ValueError("Required package source missing or outside repository: " + rel)
                _copy_file(src, candidate / rel)
            for pattern in INCLUDE_GLOBS:
                for src in ROOT.glob(pattern):
                    if src.is_file():
                        if not src.resolve().is_relative_to(ROOT.resolve()):
                            raise ValueError("Package source escapes repository")
                        _copy_file(src, candidate / src.relative_to(ROOT))
            dest_models = candidate / "models" / "all-MiniLM-L6-v2"
            for name in MINILM_FILES:
                _copy_file(snap / name, dest_models / name)  # includes model.safetensors
            proof = validate_checkpoint(dest_models)
            _check_import(candidate)
            candidate_zip = temporary / ZIP_PATH.name
            with zipfile.ZipFile(candidate_zip, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in candidate.rglob("*"):
                    if path.is_file() and "__pycache__" not in path.parts:
                        archive.write(path, path.relative_to(temporary).as_posix())
            with zipfile.ZipFile(candidate_zip) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Staged ZIP failed CRC verification")
            # Keep the old stage until ZIP replacement succeeds. All rename/cleanup
            # targets were resolved inside the fixed generated artifact directory.
            backup = temporary / "previous-stage"
            if STAGE.exists():
                os.replace(STAGE, backup)
            try:
                os.replace(candidate, STAGE)
                os.replace(candidate_zip, ZIP_PATH)
            except OSError:
                if STAGE.exists(): os.replace(STAGE, candidate)
                if backup.exists(): os.replace(backup, STAGE)
                raise
        print("zip: " + str(ZIP_PATH))
        print("bytes: " + str(ZIP_PATH.stat().st_size))
        print("MiniLM verified: " + str(proof["files_checked"]) + " files at " + str(proof["revision"]))
        return 0
    except (CheckpointError, OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile):
        print("Package validation failed; previous ZIP preserved. Verify the pinned sidecar with scripts/vendor_minilm.py before packing.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
