#!/usr/bin/env python3
"""Build static reader assets from text/vol01 chapter files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "text" / "vol01"
DEFAULT_REPORTS = DEFAULT_SOURCE / ".reports"
DEFAULT_COVER = ROOT.parent / "images" / "vol01" / "cover.jpeg"
STORY_TITLE = "Ai Bảo Hắn Tu Tiên"
VN_TZ = timezone(timedelta(hours=7))

CHAPTER_FILE_RE = re.compile(
    r"^\d+_Chương\s+(\d+)\s*[-–:]\s*(.+)\.txt$",
    re.IGNORECASE,
)


def parse_chapter_no(filename: str) -> int | None:
    match = CHAPTER_FILE_RE.match(filename)
    return int(match.group(1)) if match else None


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


def build_story_index(files: list[Path]) -> dict[int, int]:
    """Map story chapter number -> reader list index n."""
    mapping: dict[int, int] = {}
    for n, src in enumerate(files, start=1):
        chapter_no = parse_chapter_no(src.name)
        if chapter_no is not None:
            mapping[chapter_no] = n
    return mapping


def find_file_by_story_no(files: list[Path], story_no: int) -> Path | None:
    for src in files:
        if parse_chapter_no(src.name) == story_no:
            return src
    return None


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip() + "\n"


def get_updated_at(src: Path, reports_dir: Path) -> str | None:
    report_path = reports_dir / f"{src.name}.json"
    if report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            if data.get("updated_at"):
                return data["updated_at"]
        except (json.JSONDecodeError, OSError):
            pass
    mtime = src.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=VN_TZ).isoformat(timespec="seconds")


def chapter_entry(n: int, src: Path, reports_dir: Path) -> dict:
    title = parse_title(src.name) or src.stem
    rel_path = f"chapters/chuong-{n}.txt"
    story_no = parse_chapter_no(src.name)
    entry: dict = {
        "n": n,
        "title": title,
        "story": STORY_TITLE,
        "path": rel_path,
        "updated_at": get_updated_at(src, reports_dir),
    }
    if story_no is not None:
        entry["story_no"] = story_no
    return entry


def load_existing_meta(out: Path) -> list[dict] | None:
    path = out / "chapters.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build(
    source: Path,
    out: Path,
    cover_src: Path,
    reports_dir: Path,
    *,
    from_ch: int | None = None,
    to_ch: int | None = None,
) -> int:
    chapters_dir = out / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    files = collect_chapter_files(source)
    if not files:
        raise SystemExit(f"No chapter files found in {source}")

    story_index = build_story_index(files)
    incremental = from_ch is not None or to_ch is not None
    existing = load_existing_meta(out) if incremental else None

    if incremental and existing is None:
        raise SystemExit("Incremental build requires existing chapters.json in output dir")

    if incremental:
        start = from_ch or 1
        end = to_ch or max(story_index)
        updated_count = 0
        meta = list(existing)

        for story_no in range(start, end + 1):
            reader_n = story_index.get(story_no)
            src = find_file_by_story_no(files, story_no)
            if reader_n is None or src is None:
                print(f"  WARN: story chapter {story_no} not found, skip")
                continue

            dest = out / f"chapters/chuong-{reader_n}.txt"
            dest.write_text(normalize_text(src.read_text(encoding="utf-8")), encoding="utf-8")
            entry = chapter_entry(reader_n, src, reports_dir)
            meta[reader_n - 1] = entry
            updated_count += 1
            print(f"  [story={story_no} n={reader_n}] {entry['title']}")

        (out / "chapters.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if cover_src.exists():
            shutil.copy2(cover_src, out / "cover.jpeg")
        print(f"\nUpdated {updated_count} chapter(s) in {chapters_dir}/")
        print(f"chapters.json: {(out / 'chapters.json').stat().st_size:,} bytes")
        return updated_count

    meta: list[dict] = []
    for n, src in enumerate(files, start=1):
        dest = out / f"chapters/chuong-{n}.txt"
        dest.write_text(normalize_text(src.read_text(encoding="utf-8")), encoding="utf-8")
        entry = chapter_entry(n, src, reports_dir)
        meta.append(entry)
        if n <= 3 or n == len(files):
            print(f"  [{n}/{len(files)}] {entry['title']}")
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


def reader_indices_for_story_range(
    source: Path,
    from_ch: int,
    to_ch: int,
) -> list[int]:
    files = collect_chapter_files(source)
    story_index = build_story_index(files)
    indices = []
    for story_no in range(from_ch, to_ch + 1):
        n = story_index.get(story_no)
        if n is not None:
            indices.append(n)
    return indices


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare static reader from vol01 text.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--out", type=Path, default=ROOT)
    parser.add_argument("--cover", type=Path, default=DEFAULT_COVER)
    parser.add_argument("--from", dest="from_ch", type=int, help="Story chapter start")
    parser.add_argument("--to", dest="to_ch", type=int, help="Story chapter end")
    args = parser.parse_args()

    if not args.source.is_dir():
        raise SystemExit(f"Source not found: {args.source}")

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Source: {args.source}")
    print(f"Output: {args.out}")
    if args.from_ch or args.to_ch:
        print(f"Story range: ch {args.from_ch or 1} – {args.to_ch or '…'}")
    build(
        args.source,
        args.out,
        args.cover,
        args.reports,
        from_ch=args.from_ch,
        to_ch=args.to_ch,
    )


if __name__ == "__main__":
    main()
