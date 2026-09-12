from __future__ import annotations

import importlib.util
import re
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
    def test_demo_assets_have_valid_captions_without_a_commit_sha(self) -> None:
        builder = (ROOT / "scripts" / "build_demo_video.py").read_text(encoding="utf-8")
        srt = (ROOT / "report" / "demo_video" / "captions.en.srt").read_text(encoding="utf-8")
        youtube = (ROOT / "report" / "demo_video" / "YOUTUBE.md").read_text(encoding="utf-8")
        for name, text in (("builder", builder), ("captions", srt), ("youtube", youtube)):
            with self.subTest(asset=name):
                self.assertNotRegex(text, r"\b[0-9a-fA-F]{7,40}\b", "do not freeze a commit SHA in demo copy")
        self.assertIn("python -m evaluator.local_evaluator", youtube)

        # SRT contains the spoken narration, not every on-screen footer. Check
        # the delivery contract without inventing speech to match a slogan.
        def milliseconds(stamp: str) -> int:
            h, m, s, ms = map(int, re.split(r"[:,]", stamp))
            self.assertLess(m, 60)
            self.assertLess(s, 60)
            return ((h * 60 + m) * 60 + s) * 1000 + ms

        cues = re.split(r"\n\s*\n", srt.strip())
        self.assertTrue(cues)
        previous_end = 0
        for expected_index, cue in enumerate(cues, 1):
            lines = cue.splitlines()
            self.assertGreaterEqual(len(lines), 3)
            self.assertEqual(lines[0], str(expected_index))
            timing = re.fullmatch(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", lines[1])
            self.assertIsNotNone(timing)
            start, end = (milliseconds(stamp) for stamp in timing.groups())
            self.assertGreaterEqual(start, previous_end)
            self.assertGreater(end, start)
            self.assertLessEqual(end, 180_000)
            self.assertTrue(" ".join(lines[2:]).strip())
            previous_end = end

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
