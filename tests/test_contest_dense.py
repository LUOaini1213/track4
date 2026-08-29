from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starter.shopping_agent.contest_dense import (
    DEFAULT_HUB_ID,
    PoolDenseEncoder,
    is_transformers_dir,
    resolve_model_source,
)


def _write_fake_snapshot(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text('{"model_type": "bert"}', encoding="utf-8")
    (root / "model.safetensors").write_bytes(b"not-a-real-weight")
    return root


class MiniLMSourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._home = os.environ.get("TECHJAM_DENSE_HOME")
        os.environ.pop("TECHJAM_DENSE_HOME", None)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.addCleanup(self._restore_home)

    def _restore_home(self) -> None:
        if self._home is None:
            os.environ.pop("TECHJAM_DENSE_HOME", None)
        else:
            os.environ["TECHJAM_DENSE_HOME"] = self._home

    def test_dense_home_wins_over_hub_id(self) -> None:
        snap = _write_fake_snapshot(Path(self.tempdir.name) / "home")
        os.environ["TECHJAM_DENSE_HOME"] = str(snap)
        self.assertTrue(is_transformers_dir(snap))
        self.assertEqual(resolve_model_source(), str(snap))

    def test_invalid_dense_home_falls_through(self) -> None:
        os.environ["TECHJAM_DENSE_HOME"] = str(Path(self.tempdir.name) / "missing")
        with patch(
            "starter.shopping_agent.contest_dense.snapshot_dir",
            return_value=Path(self.tempdir.name) / "also-missing",
        ):
            self.assertEqual(resolve_model_source(), DEFAULT_HUB_ID)

    def test_snapshot_dir_used_when_present(self) -> None:
        snap = _write_fake_snapshot(Path(self.tempdir.name) / "sidecar")
        with patch(
            "starter.shopping_agent.contest_dense.snapshot_dir",
            return_value=snap,
        ):
            self.assertEqual(resolve_model_source(), str(snap))

    def test_local_dir_does_not_hit_the_hub(self) -> None:
        encoder = PoolDenseEncoder()
        calls: list[bool] = []

        class DummyModel:
            def eval(self) -> object:
                return self

        def fake_load(local_files_only: bool):
            calls.append(local_files_only)
            return "tok", DummyModel(), object()

        encoder._source = lambda: str(Path("C:/models/all-MiniLM-L6-v2"))  # type: ignore[method-assign]
        encoder._source_is_local_dir = lambda: True  # type: ignore[method-assign]
        encoder._load_transformers = fake_load  # type: ignore[method-assign]
        self.assertTrue(encoder.available())
        self.assertEqual(calls, [True])


if __name__ == "__main__":
    unittest.main()
