from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
