from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "submission_dist" / "bytesize-track4"


def _pack_module():
    """Load scripts/pack_submission.py without running main()."""

    spec = importlib.util.spec_from_file_location(
        "pack_submission", ROOT / "scripts" / "pack_submission.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _packed_relpaths() -> set[str]:
    pack = _pack_module()
    packed = set(pack.INCLUDE_FILES)
    for pattern in pack.INCLUDE_GLOBS:
        packed.update(
            src.relative_to(ROOT).as_posix()
            for src in ROOT.glob(pattern)
            if src.is_file()
        )
    return packed


class SubmissionPackageTests(unittest.TestCase):
    def test_demo_copy_does_not_embed_a_commit_sha(self) -> None:
        builder = (ROOT / "scripts" / "build_demo_video.py").read_text(encoding="utf-8")
        srt = (ROOT / "report" / "demo_video" / "captions.en.srt").read_text(encoding="utf-8")
        youtube = (ROOT / "report" / "demo_video" / "YOUTUBE.md").read_text(encoding="utf-8")
        self.assertNotIn("11069c6", builder)
        self.assertNotIn("11069c6", srt)
        self.assertNotIn("11069c6", youtube)
        self.assertIn("reproducible locally", builder)
        self.assertIn("reproducible locally", srt)
        self.assertIn("reproducible locally", youtube)

    def test_zip_checklist_requires_minilm_and_excludes_holdout_jsonl(self) -> None:
        checklist = (ROOT / "SUBMISSION_CHECKLIST.md").read_text(encoding="utf-8")
        self.assertIn("models/all-MiniLM-L6-v2/", checklist)
        self.assertIn("holdout/holdout_200.jsonl", checklist)
        pack = (ROOT / "scripts" / "pack_submission.py").read_text(encoding="utf-8")
        self.assertNotIn("holdout_200.jsonl", pack)
        self.assertIn("all-MiniLM-L6-v2", pack)
        self.assertIn("model.safetensors", pack)
        self.assertIn("vendor_minilm.py", pack)
        self.assertIn("MINILM_FILES", pack)

    def test_pack_ships_every_shopping_agent_module(self) -> None:
        """A contest_*-only whitelist crashes the scored entry in the ZIP.

        ``starter/shopping_agent/__init__.py`` imports catalog, config, model,
        semantic_ranking, qwen_reranker, state, policy and structured_pool at
        module level, so importing any submodule pulls all of them in.  The
        whole package must ship or ``from starter.agent import Agent`` raises
        ModuleNotFoundError on the judge's machine.
        """

        packed = _packed_relpaths()
        missing = sorted(
            src.relative_to(ROOT).as_posix()
            for src in (ROOT / "starter" / "shopping_agent").glob("*.py")
            if src.relative_to(ROOT).as_posix() not in packed
        )
        self.assertEqual(missing, [], f"ZIP whitelist omits {missing}")

    def test_packed_tree_scored_entry_imports(self) -> None:
        """The staged tree is what gets zipped; import it the way a judge does."""

        if not (STAGE / "starter" / "agent.py").is_file():
            self.skipTest("run scripts/pack_submission.py first")
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "from starter.agent import Agent;"
                "print(','.join(c.__name__ for c in Agent.__mro__))",
            ],
            cwd=STAGE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ContestAgent", proc.stdout)


if __name__ == "__main__":
    unittest.main()
