#!/usr/bin/env python3
"""Build static reader assets from text/vol01 chapter files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "text" / "vol01"
DEFAULT_COVER = ROOT.parent / "images" / "vol01" / "cover.jpeg"
STORY_TITLE = "Ai Bảo Hắn Tu Tiên"

CHAPTER_FILE_RE = re.compile(
    r"^\d+_Chương\s+(\d+)\s*[-–:]\s*(.+)\.txt$",
    re.IGNORECASE,
)


def parse_title(filename: str) -> str | None:
    match = CHAPTER_FILE_RE.match(filename)
    if not match:
        return None
    chapter_no = int(match.group(1))
    subtitle = match.group(2).strip()
    return f"Chương {chapter_no}: {subtitle}"


def is_chapter_file(path: Path) -> bool:
    name = path.name
    if "split" in name.lower():
        return False
    if "chương" not in name.lower():
        return False
    return path.suffix.lower() == ".txt"


def collect_chapter_files(source: Path) -> list[Path]:
    files = [p for p in source.glob("*.txt") if is_chapter_file(p)]
    files.sort(key=lambda p: p.name)
    return files


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip() + "\n"


def build(source: Path, out: Path, cover_src: Path) -> int:
    chapters_dir = out / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    files = collect_chapter_files(source)
    if not files:
        raise SystemExit(f"No chapter files found in {source}")

    meta: list[dict] = []
    for n, src in enumerate(files, start=1):
        title = parse_title(src.name)
        if not title:
            title = src.stem

        rel_path = f"chapters/chuong-{n}.txt"
        dest = out / rel_path
        dest.write_text(normalize_text(src.read_text(encoding="utf-8")), encoding="utf-8")

        meta.append(
            {
                "n": n,
                "title": title,
                "story": STORY_TITLE,
                "path": rel_path,
            }
        )
        if n <= 3 or n == len(files):
            print(f"  [{n}/{len(files)}] {title}")
        elif n == 4:
            print("  ...")

    (out / "chapters.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if cover_src.exists():
        shutil.copy2(cover_src, out / "cover.jpeg")
        print(f"Cover → {out / 'cover.jpeg'}")
    else:
        print(f"WARN: cover not found at {cover_src}")

    print(f"\nWrote {len(meta)} chapter(s) → {chapters_dir}/")
    print(f"chapters.json: {(out / 'chapters.json').stat().st_size:,} bytes")
    return len(meta)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare static reader from vol01 text.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=ROOT)
    parser.add_argument("--cover", type=Path, default=DEFAULT_COVER)
    args = parser.parse_args()

    if not args.source.is_dir():
        raise SystemExit(f"Source not found: {args.source}")

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Source: {args.source}")
    print(f"Output: {args.out}")
    build(args.source, args.out, args.cover)


if __name__ == "__main__":
    main()
