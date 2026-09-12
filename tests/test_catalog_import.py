from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_catalog import import_catalog, validate_catalog


class CatalogImportTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source.jsonl"
        self.dataset = self.root / "public.jsonl"
        self.data = b'{"parent_asin":"A"}\n{"parent_asin":"B"}\n'
        self.source.write_bytes(self.data)
        self.dataset.write_text(json.dumps({"ground_truth": {"parent_asin": "A"}}) + "\n", encoding="utf-8")
        self.expected = dict(expected_sha256=hashlib.sha256(self.data).hexdigest(), expected_rows=2, expected_sessions=1)

    def test_gzip_import_preserves_exact_bytes_and_is_idempotent(self) -> None:
        compressed = self.root / "catalog.jsonl.gz"
        compressed.write_bytes(gzip.compress(self.data))
        destination = self.root / "data" / "catalog.jsonl"
        result = import_catalog(compressed, destination, self.dataset, **self.expected)
        self.assertEqual(destination.read_bytes(), self.data)
        self.assertEqual(result["catalog_rows"], 2)
        self.assertEqual(result["public_targets_present"], 1)
        self.assertEqual(import_catalog(compressed, destination, self.dataset, **self.expected)["status"], "already verified")

    def test_changed_catalog_fails_without_creating_destination(self) -> None:
        self.source.write_bytes(self.data + b"\n")
        destination = self.root / "output.jsonl"
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            import_catalog(self.source, destination, self.dataset, **self.expected)
        self.assertFalse(destination.exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["public.jsonl", "source.jsonl"])

    def test_existing_different_destination_is_never_overwritten(self) -> None:
        destination = self.root / "output.jsonl"
        destination.write_bytes(b"old file")
        with self.assertRaises(ValueError):
            import_catalog(self.source, destination, self.dataset, **self.expected)
        self.assertEqual(destination.read_bytes(), b"old file")

    def test_missing_public_target_is_rejected(self) -> None:
        self.dataset.write_text('{"ground_truth":{"parent_asin":"ABSENT"}}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "public targets missing"):
            validate_catalog(self.source, self.dataset, **self.expected)

    def test_row_and_session_counts_are_checked(self) -> None:
        for field, value, message in (("expected_rows", 3, "row count"), ("expected_sessions", 2, "session count")):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                validate_catalog(self.source, self.dataset, **{**self.expected, field: value})

    def test_duplicate_ids_and_corrupt_gzip_are_rejected(self) -> None:
        self.source.write_bytes(b'{"parent_asin":"A"}\n{"parent_asin":"A"}\n')
        with self.assertRaisesRegex(ValueError, "duplicate parent_asin"):
            validate_catalog(self.source, self.dataset, **self.expected)
        broken = self.root / "broken.jsonl.gz"
        broken.write_bytes(gzip.compress(self.data)[:-8])
        with self.assertRaises(EOFError):
            import_catalog(broken, self.root / "output.jsonl", self.dataset, **self.expected)
        self.assertFalse((self.root / "output.jsonl").exists())
