#!/usr/bin/env python3
"""Repository hygiene scanner for the public tree.

Self-contained (standard library only). Fails (exit 1) if the tracked tree
contains any of:

  * secrets (API keys / tokens),
  * machine-absolute paths,
  * tracked binary blobs that don't belong in source (stray archives).

Run in CI and locally:  python scripts/security_scan.py
"""
from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

SECRETS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}",   # JWT
    r"AKIA[0-9A-Z]{16}",
    r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
]
ABS_PATHS = [r"[A-Za-z]:\\Users\\", r"/home/[a-z]", r"/Users/[A-Za-z]"]

SKIP = {"security_scan.py"}  # this file legitimately contains the patterns above
TEXT_EXT = {".py", ".md", ".json", ".css", ".html", ".yml", ".yaml", ".txt", ".toml"}


def tracked_files() -> list[pathlib.Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
        return [ROOT / p for p in out if (ROOT / p).is_file()]
    except Exception:
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def main() -> int:
    problems: list[str] = []
    files = tracked_files()
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in {".zip", ".7z", ".rar"}:
            problems.append(f"stray archive tracked: {rel}")
            continue
        if path.name in SKIP or path.suffix.lower() not in TEXT_EXT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat in SECRETS:
            if re.search(pat, text):
                problems.append(f"possible secret in {rel} (/{pat}/)")
        for pat in ABS_PATHS:
            if re.search(pat, text):
                problems.append(f"machine-absolute path in {rel} (/{pat}/)")

    if problems:
        print("HYGIENE SCAN FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"hygiene scan OK ({len(files)} tracked files checked; no secrets/abs-paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
