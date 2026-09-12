#!/usr/bin/env python3
"""Validate and import an existing organizer catalog; never downloads data."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_SHA256 = "da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67"
CATALOG_ROWS = 50_000
PUBLIC_SESSIONS = 200


def _open_catalog(path: Path):
    return gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb")


def validate_catalog(
    source: Path,
    dataset: Path,
    *,
    expected_sha256: str = CATALOG_SHA256,
    expected_rows: int = CATALOG_ROWS,
    expected_sessions: int = PUBLIC_SESSIONS,
) -> dict:
    """Check frozen decompressed bytes, unique product IDs and public targets."""
    digest = hashlib.sha256()
    ids: set[str] = set()
    rows = 0
    with _open_catalog(source) as stream:
        for line_number, raw in enumerate(stream, 1):
            digest.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            pid = row.get("parent_asin") if isinstance(row, dict) else None
            if not isinstance(pid, str) or not pid:
                raise ValueError(f"catalog line {line_number}: missing string parent_asin")
            if pid in ids:
                raise ValueError(f"catalog line {line_number}: duplicate parent_asin {pid}")
            ids.add(pid)
            rows += 1
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"catalog SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}")
    if rows != expected_rows:
        raise ValueError(f"catalog row count: expected {expected_rows}, got {rows}")

    samples = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(samples) != expected_sessions:
        raise ValueError(f"public session count: expected {expected_sessions}, got {len(samples)}")
    targets = {sample["ground_truth"]["parent_asin"] for sample in samples}
    missing = targets - ids
    if missing:
        raise ValueError(f"public targets missing from catalog: {sorted(missing)}")
    return {
        "sha256": actual_sha256,
        "catalog_rows": rows,
        "unique_product_ids": len(ids),
        "public_sessions": len(samples),
        "public_targets_present": len(targets),
    }


def import_catalog(source: Path, destination: Path, dataset: Path, **validation) -> dict:
    """Validate a staged copy before making it available; keep existing files."""
    if destination.exists():
        result = validate_catalog(source, dataset, **validation)
        validate_catalog(destination, dataset, **validation)
        return {**result, "destination": str(destination.resolve()), "status": "already verified"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".jsonl", delete=False) as output:
            staging = Path(output.name)
            with _open_catalog(source) as stream:
                shutil.copyfileobj(stream, output)
        result = validate_catalog(staging, dataset, **validation)
        # Exclusive creation refuses to overwrite a file created during validation.
        with destination.open("xb") as output, staging.open("rb") as stream:
            try:
                shutil.copyfileobj(stream, output)
            except BaseException:
                output.close()
                destination.unlink(missing_ok=True)
                raise
        return {**result, "destination": str(destination.resolve()), "status": "imported"}
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="path to original catalog.jsonl or catalog.jsonl.gz")
    parser.add_argument("--destination", type=Path, default=ROOT / "data" / "catalog.jsonl")
    parser.add_argument("--check-only", action="store_true", help="validate without copying")
    args = parser.parse_args()
    dataset = ROOT / "data" / "public_set.jsonl"
    try:
        result = validate_catalog(args.source, dataset) if args.check_only else import_catalog(args.source, args.destination, dataset)
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        parser.exit(1, f"Catalog validation failed: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
