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
    files.sort(key=lambda p: (parse_chapter_no(p.name) or 10**9, p.name))
    return files


def build_story_index(files: list[Path]) -> dict[int, int]:
    """Map story chapter number -> reader list index n (n == story_no)."""
    mapping: dict[int, int] = {}
    for src in files:
        chapter_no = parse_chapter_no(src.name)
        if chapter_no is not None:
            mapping[chapter_no] = chapter_no
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


def chapter_entry(story_no: int, src: Path, reports_dir: Path) -> dict:
    title = parse_title(src.name) or src.stem
    rel_path = f"chapters/chuong-{story_no}.txt"
    return {
        "n": story_no,
        "story_no": story_no,
        "title": title,
        "story": STORY_TITLE,
        "path": rel_path,
        "updated_at": get_updated_at(src, reports_dir),
    }


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
        meta_by_story = {c["story_no"]: c for c in existing if c.get("story_no") is not None}
        meta = list(existing)

        for story_no in range(start, end + 1):
            src = find_file_by_story_no(files, story_no)
            if src is None:
                print(f"  WARN: story chapter {story_no} not found, skip")
                continue

            dest = out / f"chapters/chuong-{story_no}.txt"
            dest.write_text(normalize_text(src.read_text(encoding="utf-8")), encoding="utf-8")
            entry = chapter_entry(story_no, src, reports_dir)
            if story_no in meta_by_story:
                idx = next(i for i, c in enumerate(meta) if c.get("story_no") == story_no)
                meta[idx] = entry
            else:
                meta.append(entry)
                meta.sort(key=lambda c: c.get("story_no") or 0)
            meta_by_story[story_no] = entry
            updated_count += 1
            print(f"  [story={story_no}] {entry['title']}")

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
    seen: set[int] = set()
    for src in files:
        story_no = parse_chapter_no(src.name)
        if story_no is None or story_no in seen:
            continue
        seen.add(story_no)
        dest = out / f"chapters/chuong-{story_no}.txt"
        dest.write_text(normalize_text(src.read_text(encoding="utf-8")), encoding="utf-8")
        entry = chapter_entry(story_no, src, reports_dir)
        meta.append(entry)
        if len(meta) <= 3:
            print(f"  [{len(meta)}] {entry['title']}")
        elif len(meta) == 4:
            print("  ...")
    meta.sort(key=lambda c: c["story_no"])
    if meta:
        print(f"  [{len(meta)}] {meta[-1]['title']}")

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
        if story_no in story_index:
            indices.append(story_no)
    return indices


def repair_from_built_files(out: Path) -> int:
    """Rebuild chapters.json from deployed chapter text files (content is source of truth)."""
    chapters_dir = out / "chapters"
    if not chapters_dir.is_dir():
        raise SystemExit(f"Chapters dir not found: {chapters_dir}")

    existing_path = out / "chapters.json"
    existing = load_existing_meta(out) if existing_path.exists() else []
    by_reader_n = {c["n"]: c for c in existing}

    content_map: dict[int | None, list[dict]] = {}
    for txt in chapters_dir.glob("chuong-*.txt"):
        reader_n = int(txt.stem.split("-", 1)[1])
        text = txt.read_text(encoding="utf-8")
        first = text.splitlines()[0].strip() if text else ""
        match = re.match(r"Chương\s+(\d+)", first)
        story_no = int(match.group(1)) if match else None
        meta = by_reader_n.get(reader_n, {})
        content_map.setdefault(story_no, []).append(
            {
                "reader_n": reader_n,
                "path": f"chapters/{txt.name}",
                "title_from_content": first,
                "meta_title": meta.get("title"),
                "meta_story_no": meta.get("story_no"),
                "updated_at": meta.get("updated_at"),
                "title_match": meta.get("story_no") == story_no,
            }
        )

    def pick_best(candidates: list[dict]) -> dict:
        matched = [c for c in candidates if c["title_match"]]
        if matched:
            return matched[0]
        return candidates[0]

    meta: list[dict] = []
    for story_no in sorted(k for k in content_map if k is not None):
        candidates = content_map[story_no]
        best = pick_best(candidates) if len(candidates) > 1 else candidates[0]
        title = best["meta_title"]
        if not title or not title.startswith(f"Chương {story_no}"):
            title_from_content = best["title_from_content"]
            if " - " in title_from_content and ":" not in title_from_content:
                title_from_content = title_from_content.replace(" - ", ": ", 1)
            title = (
                title_from_content
                if title_from_content.startswith("Chương")
                else f"Chương {story_no}"
            )
        meta.append(
            {
                "n": story_no,
                "story_no": story_no,
                "title": title,
                "story": STORY_TITLE,
                "path": best["path"],
                "updated_at": best.get("updated_at"),
            }
        )

    existing_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Repaired {len(meta)} chapter(s) in chapters.json")
    return len(meta)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare static reader from vol01 text.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--out", type=Path, default=ROOT)
    parser.add_argument("--cover", type=Path, default=DEFAULT_COVER)
    parser.add_argument("--from", dest="from_ch", type=int, help="Story chapter start")
    parser.add_argument("--to", dest="to_ch", type=int, help="Story chapter end")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Rebuild chapters.json from existing chapter text files",
    )
    args = parser.parse_args()

    if args.repair:
        print(f"Repairing chapters.json in {args.out}")
        repair_from_built_files(args.out)
        return

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
