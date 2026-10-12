"""Synthetic assets verify guard behavior, never the real MiniLM checkpoint/score.

Production-trust tests use the committed official manifest. Positive small-file
fixtures explicitly patch only load_manifest to a synthetic expected-hash table.
No real model package, encoder download or forward is used.
"""
from __future__ import annotations
import hashlib
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from starter.shopping_agent import contest_checkpoint as checkpoint
from starter.shopping_agent import contest_dense as dense


def synthetic_snapshot(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in checkpoint.MINILM_FILES:
        raw = ("synthetic guard fixture: " + name).encode()
        (root / name).write_bytes(raw)
        files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return root, {"files": files}


class MiniLMIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"TECHJAM_DENSE_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
        self.env.start(); self.addCleanup(self.env.stop)
        self.home = patch.dict(os.environ)
        self.home.start(); self.addCleanup(self.home.stop)
        os.environ.pop("TECHJAM_DENSE_HOME", None)

    def test_official_manifest_is_bound_to_recorded_revision_and_weights(self):
        manifest = checkpoint.load_manifest()
        self.assertEqual(manifest["revision"], dense.HUB_REVISION)
        self.assertEqual(manifest["files"]["model.safetensors"]["sha256"], dense.WEIGHTS_SHA256)
        self.assertEqual(manifest["files"]["model.safetensors"]["bytes"], 90868376)
        self.assertEqual(set(manifest["files"]), set(checkpoint.MINILM_FILES))
        for name, record in manifest["files"].items():
            self.assertIn(dense.HUB_REVISION, record["source"])
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            if name != "model.safetensors": self.assertRegex(record["git_blob_sha1"], r"^[0-9a-f]{40}$")

    def test_untrusted_local_manifest_cannot_self_authorize(self):
        path, manifest = synthetic_snapshot(self.root / "self-signed")
        (path / "manifest.json").write_text(json.dumps(manifest))
        self.assertFalse(dense.is_transformers_dir(path))
        forged = self.root / "trusted.json"; forged.write_text(json.dumps(manifest))
        with patch.object(checkpoint, "manifest_path", return_value=forged):
            with self.assertRaisesRegex(checkpoint.CheckpointError, "manifest hash"):
                checkpoint.load_manifest()

    def test_missing_trusted_manifest_fails_closed(self):
        with patch.object(checkpoint, "manifest_path", return_value=self.root / "missing.json"):
            with self.assertRaisesRegex(checkpoint.CheckpointError, "manifest is missing"):
                checkpoint.load_manifest()

    def test_synthetic_files_check_bytes_and_hashes_for_each_required_file(self):
        for name in checkpoint.MINILM_FILES:
            with self.subTest(file=name):
                path, manifest = synthetic_snapshot(self.root / name)
                with patch.object(checkpoint, "load_manifest", return_value=manifest):
                    self.assertEqual(checkpoint.validate_checkpoint(path)["files_checked"], 6)
                    raw = (path / name).read_bytes()
                    (path / name).write_bytes(b"X" + raw[1:])
                    with self.assertRaisesRegex(checkpoint.CheckpointError, "hash mismatch"):
                        checkpoint.validate_checkpoint(path)
                    (path / name).unlink()
                    with self.assertRaisesRegex(checkpoint.CheckpointError, "missing or unreadable"):
                        checkpoint.validate_checkpoint(path)

    def test_extra_tokenizer_or_checkpoint_override_is_rejected(self):
        path, manifest = synthetic_snapshot(self.root / "extra")
        with patch.object(checkpoint, "load_manifest", return_value=manifest):
            for name in ("added_tokens.json", "model.safetensors.index.json", "tokenizer.model", "spiece.model"):
                (path / name).write_bytes(b"{}")
                with self.assertRaisesRegex(checkpoint.CheckpointError, "override file"):
                    checkpoint.validate_checkpoint(path)
                (path / name).unlink()

    def test_dense_home_wins_only_after_validation(self):
        path, manifest = synthetic_snapshot(self.root / "home")
        os.environ["TECHJAM_DENSE_HOME"] = str(path)
        with patch.object(checkpoint, "load_manifest", return_value=manifest):
            self.assertEqual(dense.resolve_model_source(), str(path))
            self.assertTrue(dense.is_transformers_dir(path))

    def test_invalid_explicit_home_is_terminal_and_never_hits_loader(self):
        path, _ = synthetic_snapshot(self.root / "private-path-do-not-disclose")
        os.environ["TECHJAM_DENSE_HOME"] = str(path)
        encoder = dense.PoolDenseEncoder()
        with patch.object(encoder, "_load_transformers") as loader:
            self.assertFalse(encoder.available())
            loader.assert_not_called()
        self.assertEqual(encoder.diagnostics["mode"], "nodense")
        self.assertNotIn(str(path), json.dumps(encoder.diagnostics))
        self.assertNotIn("private-path", json.dumps(encoder.diagnostics))

    def test_missing_explicit_home_is_not_silently_changed_to_hub(self):
        os.environ["TECHJAM_DENSE_HOME"] = str(self.root / "missing")
        with self.assertRaises(checkpoint.CheckpointError): dense.resolve_model_source()

    def test_sidecar_is_selected_only_after_validation(self):
        path, manifest = synthetic_snapshot(self.root / "sidecar")
        with patch.object(checkpoint, "load_manifest", return_value=manifest), patch.object(dense, "snapshot_dir", return_value=path):
            self.assertEqual(dense.resolve_model_source(), str(path))
        with patch.object(dense, "snapshot_dir", return_value=path):
            self.assertFalse(dense.PoolDenseEncoder().available())

    def test_absent_optional_sidecar_selects_fixed_hub_id(self):
        with patch.object(dense, "snapshot_dir", return_value=self.root / "absent"):
            self.assertEqual(dense.resolve_model_source(), dense.DEFAULT_HUB_ID)

    def test_hub_cache_is_pinned_and_validated_before_fake_transformers(self):
        path, manifest = synthetic_snapshot(self.root / "cache")
        calls = []
        hub = types.ModuleType("huggingface_hub")
        hub.snapshot_download = lambda **kw: calls.append(("snapshot", kw)) or str(path)
        transformers = types.ModuleType("transformers")
        class Model:
            def eval(self): return self
        class Factory:
            @staticmethod
            def from_pretrained(source, **kw):
                calls.append(("factory", source, kw)); return Model()
        transformers.AutoModel = Factory; transformers.AutoTokenizer = Factory
        encoder = dense.PoolDenseEncoder()
        with patch.object(checkpoint, "load_manifest", return_value=manifest), patch.object(encoder, "_source", return_value=dense.DEFAULT_HUB_ID), patch.dict(sys.modules, {"huggingface_hub":hub,"transformers":transformers,"torch":types.ModuleType("torch")}):
            encoder._load_transformers(True)
        self.assertEqual(calls[0][1]["revision"], dense.HUB_REVISION)
        self.assertEqual(calls[0][1]["repo_id"], dense.DEFAULT_HUB_ID)
        self.assertEqual(set(calls[0][1]["allow_patterns"]), set(checkpoint.MINILM_FILES))
        self.assertTrue(calls[0][1]["local_files_only"])
        for call in calls[1:]:
            self.assertEqual(call[1], str(path))
            self.assertEqual(call[2]["revision"], dense.HUB_REVISION)
            self.assertTrue(call[2]["local_files_only"])
            self.assertFalse(call[2]["trust_remote_code"])
        self.assertTrue(calls[-1][2]["use_safetensors"])

    def test_bad_cached_hub_files_do_not_reach_transformers_or_network_retry(self):
        path, _ = synthetic_snapshot(self.root / "bad-cache")
        hub = types.ModuleType("huggingface_hub"); calls = []
        hub.snapshot_download = lambda **kw: calls.append(kw) or str(path)
        encoder = dense.PoolDenseEncoder()
        with patch.object(encoder,"_source",return_value=dense.DEFAULT_HUB_ID), patch.dict(sys.modules,{"huggingface_hub":hub}), patch.dict(os.environ,{"TECHJAM_DENSE_OFFLINE":"0","HF_HUB_OFFLINE":"0"}):
            self.assertFalse(encoder.available())
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["local_files_only"])
        self.assertEqual(encoder.diagnostics["mode"], "nodense")

    def test_vendor_uses_fixed_revision_required_files_and_shared_validator(self):
        from scripts import vendor_minilm
        path, manifest = synthetic_snapshot(self.root / "vendor")
        hub = types.ModuleType("huggingface_hub"); calls = []
        hub.snapshot_download = lambda **kw: calls.append(kw)
        with patch.object(vendor_minilm, "snapshot_dir", return_value=path), patch.object(checkpoint, "load_manifest", return_value=manifest), patch.object(vendor_minilm, "load_manifest", return_value=manifest), patch.dict(sys.modules, {"huggingface_hub": hub}):
            self.assertEqual(vendor_minilm.main(), 0)
        self.assertEqual(calls[0]["revision"], dense.HUB_REVISION)
        self.assertTrue(calls[0]["local_files_only"])
        self.assertEqual(set(calls[0]["allow_patterns"]), set(checkpoint.MINILM_FILES))

    def test_vendor_cannot_resolve_assets_without_trusted_manifest(self):
        from scripts import vendor_minilm
        hub = types.ModuleType("huggingface_hub")
        with patch.object(vendor_minilm, "load_manifest", side_effect=checkpoint.CheckpointError("fixture")), patch.dict(sys.modules, {"huggingface_hub": hub}):
            self.assertEqual(vendor_minilm.main(), 1)


if __name__ == "__main__": unittest.main()
