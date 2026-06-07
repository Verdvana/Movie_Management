#!/usr/bin/env python3
"""
Export local movie folder names and parsed years to CSV.

Usage:
  python3 export_local_movies.py "/Volumes/Exos X18 Movie/电影"
  python3 export_local_movies.py "/Volumes/Exos X18 Movie/电影" -o local_movies.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


YEAR_TOKEN_RE = re.compile(r"(?<!\d)((?:18|19|20)\d{2})(?!\d)")
NOISE_TOKENS = {
    "4k",
    "8k",
    "1080p",
    "1080",
    "2160p",
    "2160",
    "720p",
    "720",
    "bluray",
    "blu-ray",
    "bdrip",
    "web-dl",
    "webdl",
    "hdrip",
    "dvdrip",
    "hdtv",
    "imax",
    "remux",
    "x264",
    "x265",
    "h264",
    "h265",
    "hevc",
    "aac",
    "dts",
    "truehd",
    "atmos",
    "hdr",
    "hdr10",
    "uhd",
    "dv",
    "dovi",
    "中字",
    "国语",
    "粤语",
    "日语",
    "英语",
    "国英双语",
    "中英双字",
}


@dataclass
class LocalMovie:
    category: str
    folder_name: str
    movie_name: str
    year: str
    relative_path: str
    parse_status: str
    note: str


def normalize_title(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -_[](){}")


def parse_movie_folder_name(folder_name: str) -> tuple[str, str, str]:
    match = find_year_match(folder_name)
    year = match.group(1) if match else ""
    before_year = folder_name[: match.start(1)] if match else folder_name

    before_year = normalize_title(before_year)
    tokens = [token for token in re.split(r"[.\s_\-]+", before_year) if token]
    cleaned_tokens: list[str] = []
    for token in tokens:
        if token.lower() in NOISE_TOKENS:
            break
        cleaned_tokens.append(token)

    movie_name = normalize_title(" ".join(cleaned_tokens) or before_year)
    notes = []
    if not movie_name:
        notes.append("电影名解析失败")
    if not year:
        notes.append("年份未找到")

    status = "OK" if movie_name and year else "NEEDS_CHECK"
    return movie_name, year, "；".join(notes)


def find_year_match(folder_name: str) -> re.Match[str] | None:
    matches = list(YEAR_TOKEN_RE.finditer(folder_name))
    if not matches:
        return None

    if len(matches) > 1 and matches[0].start(1) == 0:
        return matches[1]

    return matches[0]


def iter_movie_folders(movie_root: Path) -> Iterable[tuple[str, Path]]:
    for category_dir in sorted(movie_root.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue
        for movie_dir in sorted(category_dir.iterdir()):
            if movie_dir.is_dir() and not movie_dir.name.startswith("."):
                yield category_dir.name, movie_dir


def resolve_existing_dir(raw_parts: list[str]) -> Path | None:
    raw_path = " ".join(raw_parts)
    candidates = [
        raw_path,
        raw_path.replace("\\ ", " "),
        strip_path_part_spaces(raw_path),
        strip_path_part_spaces(raw_path.replace("\\ ", " ")),
    ]

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        path = Path(candidate).expanduser().resolve()
        if path.is_dir():
            return path

    return None


def strip_path_part_spaces(path_text: str) -> str:
    if path_text.startswith("/"):
        parts = [part.strip() for part in path_text.split("/")]
        return "/" + "/".join(part for part in parts[1:] if part)
    return "/".join(part.strip() for part in path_text.split("/") if part.strip())


def export_movies(movie_root: Path, output_csv: Path) -> list[LocalMovie]:
    rows: list[LocalMovie] = []
    for category, movie_dir in iter_movie_folders(movie_root):
        movie_name, year, note = parse_movie_folder_name(movie_dir.name)
        rows.append(
            LocalMovie(
                category=category,
                folder_name=movie_dir.name,
                movie_name=movie_name,
                year=year,
                relative_path=str(movie_dir.relative_to(movie_root)),
                parse_status="OK" if movie_name and year else "NEEDS_CHECK",
                note=note,
            )
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(LocalMovie.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只扫描本地电影文件夹，导出电影名和年份 CSV，不访问豆瓣")
    parser.add_argument("movie_root", nargs="+", help="电影根目录，下面包含分类目录")
    parser.add_argument("-o", "--output", default="local_movies.csv", help="输出 CSV 文件，默认 local_movies.csv")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    movie_root = resolve_existing_dir(args.movie_root)
    if movie_root is None:
        raw_path = " ".join(args.movie_root)
        print(f"电影根目录不存在: {raw_path}", file=sys.stderr)
        print('正确示例: python3 export_local_movies.py "/Volumes/Exos X18 Movie/电影"', file=sys.stderr)
        return 2

    output_csv = Path(args.output).expanduser().resolve()
    rows = export_movies(movie_root, output_csv)
    ok_count = sum(1 for row in rows if row.parse_status == "OK")
    print(f"完成: {len(rows)} 部电影")
    print(f"解析成功: {ok_count}")
    print(f"需要检查: {len(rows) - ok_count}")
    print(f"CSV: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
