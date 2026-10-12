"""Synthetic pack failures preserve the old ZIP; no real weights are loaded.

Positive fixture trust is explicitly patched in the test process. It tests the
guard/copy/import/ZIP transaction, not a valid frozen MiniLM model or score.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from starter.shopping_agent import contest_checkpoint as checkpoint
from starter.shopping_agent import contest_dense as dense
from tests.test_contest_dense import synthetic_snapshot

ROOT = Path(__file__).resolve().parents[1]


def pack_module():
    spec = importlib.util.spec_from_file_location("checkpoint_pack", ROOT / "scripts/pack_submission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckpointPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pack = pack_module()
        self.pack.ROOT = self.root
        self.pack.DIST = self.root / "submission_dist"
        self.pack.STAGE = self.pack.DIST / "bytesize-track4"
        self.pack.ZIP_PATH = self.pack.DIST / "bytesize-track4.zip"
        self.pack.DIST.mkdir()
        self.pack.ZIP_PATH.write_bytes(b"previous reviewed ZIP fixture")
        self.old = self.pack.ZIP_PATH.read_bytes()
        for rel in self.pack.INCLUDE_FILES:
            target = self.root / rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        for src in (ROOT / "starter/shopping_agent").glob("*.py"):
            target = self.root / src.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, target)
        self.snap, self.manifest = synthetic_snapshot(self.root / "models/all-MiniLM-L6-v2")
        source = patch.object(dense, "snapshot_dir", return_value=self.snap)
        source.start(); self.addCleanup(source.stop)

    def assert_old_zip(self):
        self.assertEqual(self.pack.ZIP_PATH.read_bytes(), self.old)

    def test_production_trust_rejects_fake_weights_before_stage_or_download(self):
        with patch.object(self.pack.subprocess, "run") as runner:
            self.assertEqual(self.pack.main(), 1)
            runner.assert_not_called()
        self.assert_old_zip()
        self.assertFalse(self.pack.STAGE.exists())

    def test_missing_source_copy_preserves_zip(self):
        (self.root / "starter/agent.py").unlink()
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest):
            self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()

    def test_copied_file_is_revalidated_and_zip_preserved(self):
        original = self.pack._copy_file
        def corrupt(src, dest):
            original(src, dest)
            if src.name == "model.safetensors":
                raw = dest.read_bytes(); dest.write_bytes(b"X" + raw[1:])
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest), patch.object(self.pack, "_copy_file", side_effect=corrupt):
            self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()

    def test_import_failure_preserves_existing_stage_and_zip(self):
        self.pack.STAGE.mkdir(); (self.pack.STAGE / "old.txt").write_text("previous stage")
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest), patch.object(self.pack, "_check_import", side_effect=ValueError("fixture")):
            self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()
        self.assertEqual((self.pack.STAGE / "old.txt").read_text(), "previous stage")

    def test_zip_write_failure_preserves_previous_zip(self):
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest), patch.object(self.pack.zipfile, "ZipFile", side_effect=OSError("fixture")):
            self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()

    def test_publication_failure_restores_previous_stage_and_zip(self):
        self.pack.STAGE.mkdir(); (self.pack.STAGE / "old.txt").write_text("previous stage")
        original = self.pack.os.replace
        def fail_zip(src, dest):
            if Path(dest) == self.pack.ZIP_PATH: raise OSError("fixture rename failure")
            return original(src, dest)
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest), patch.object(self.pack.os, "replace", side_effect=fail_zip):
            self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()
        self.assertEqual((self.pack.STAGE / "old.txt").read_text(), "previous stage")

    def test_synthetic_success_imports_complete_package_and_keeps_fixed_asset_list(self):
        with patch.object(checkpoint, "load_manifest", return_value=self.manifest):
            self.assertEqual(self.pack.main(), 0)
        with zipfile.ZipFile(self.pack.ZIP_PATH) as archive:
            names = set(archive.namelist())
            self.assertIsNone(archive.testzip())
            self.assertIn("bytesize-track4/models/minilm-manifest.json", names)
            for name in checkpoint.MINILM_FILES:
                self.assertIn("bytesize-track4/models/all-MiniLM-L6-v2/" + name, names)
            for name in ("catalog.py", "policy.py", "contest_checkpoint.py"):
                self.assertIn("bytesize-track4/starter/shopping_agent/" + name, names)
            self.assertFalse(any("__pycache__" in name or "holdout/" in name for name in names))

    def test_output_cannot_escape_fixed_artifact_directory(self):
        self.pack.DIST = self.root.parent / "outside-generated-output"
        self.assertEqual(self.pack.main(), 1)
        self.assert_old_zip()


if __name__ == "__main__": unittest.main()
