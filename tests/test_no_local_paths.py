"""No tracked text file may carry a developer's absolute local path.

A path such as ``C:\\Users\\<name>\\Desktop\\...`` or ``/Users/<name>/Downloads``
publishes a username and a private folder layout, and it never works on anyone
else's machine. The README's commands are written relative to the repository
root; this gate keeps every other tracked text file that way too.

Standard library only. It reads the file list from ``git ls-files`` when git is
available (CI checkouts and clones) and otherwise walks the tree, skipping
``.git`` and virtual environments.
"""

from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A real user or home directory: drive-letter Users folders on Windows, and
# /Users/<name>/ or /home/<name>/ on macOS and Linux. The name must start with
# a letter, digit, underscore or hyphen, so generic placeholders such as
# ``/mnt/c/Users/...`` in a comment do not count.
NAME = r"[A-Za-z0-9_-][A-Za-z0-9._-]*"
LOCAL_PATH = re.compile(
    r"(?i)(?<![A-Za-z])[a-z]:[\\/]+(?:users|documents and settings)[\\/]+" + NAME
    + r"|(?<![\w.])/(?:Users|home)/" + NAME + r"/"
)
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".pptx", ".pdf", ".zip", ".gz",
    ".safetensors", ".bin", ".pyc", ".ico", ".woff", ".woff2",
}


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
        ).stdout.decode("utf-8")
        names = [name for name in out.split("\0") if name]
        if names:
            return [ROOT / name for name in names]
    except (OSError, subprocess.CalledProcessError):
        pass
    found = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__"}]
        found.extend(Path(base) / name for name in files)
    return found


def offending_lines(text: str) -> list[tuple[int, str]]:
    return [
        (number, line.strip())
        for number, line in enumerate(text.splitlines(), 1)
        if LOCAL_PATH.search(line)
    ]


class NoLocalPathTests(unittest.TestCase):
    def test_pattern_catches_the_forms_it_guards(self) -> None:
        for sample in (
            r'cd "C:\Users\someone\Desktop\repo"',
            "C:/Users/someone/repo",
            "see /Users/someone/Downloads/kit/",
            "/home/someone/work/",
        ):
            with self.subTest(sample=sample):
                self.assertTrue(offending_lines(sample), sample)
        for sample in (
            "# WSL mounted drive: /mnt/c/Users/...",
            "cd <repo-root>",
            "python -S demo/fixture.py",
        ):
            with self.subTest(sample=sample):
                self.assertFalse(offending_lines(sample), sample)

    def test_no_tracked_text_file_contains_a_local_user_path(self) -> None:
        hits = []
        for path in tracked_files():
            if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in offending_lines(text):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {line[:120]}")
        self.assertEqual(hits, [], "local machine paths in tracked files:\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()
