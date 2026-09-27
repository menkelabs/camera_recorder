"""Hotspot gate for changed Python and Vue files.

Fails only when a changed file is both complex and in the top
change-frequency set. Complex means any function with CCN > 10 or
NLOC > 80. A complex file outside that set does not fail. A frequently
changed file that is not complex does not fail. Untouched files do not fail.
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import subprocess
import sys
import tempfile
from pathlib import Path

SUFFIX_LANGUAGE = {".py": "python", ".vue": "vue"}
DEFAULT_CCN = 10
DEFAULT_NLOC = 80


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True
    ).rstrip("\n")


def changed_files(repo: Path, base: str) -> list[str]:
    rels = git(repo, "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    files = []
    for line in rels.splitlines():
        rel = line.strip().replace("\\", "/")
        if rel and Path(rel).suffix in SUFFIX_LANGUAGE:
            files.append(rel)
    return files


def change_counts(repo: Path) -> dict[str, int]:
    log = git(repo, "log", "--name-only", "--pretty=format:")
    counts: dict[str, int] = {}
    for line in log.splitlines():
        rel = line.strip().replace("\\", "/")
        if Path(rel).suffix not in SUFFIX_LANGUAGE:
            continue
        counts[rel] = counts.get(rel, 0) + 1
    return counts


def top_change_set(counts: dict[str, int], fraction: float) -> tuple[set[str], int]:
    ranked = sorted(
        ((count, path) for path, count in counts.items() if count > 0),
        key=lambda item: (-item[0], item[1]),
    )
    if not ranked:
        return set(), 0
    cutoff_index = max(1, math.ceil(len(ranked) * fraction)) - 1
    threshold = ranked[cutoff_index][0]
    return {path for count, path in ranked if count >= threshold}, threshold


def lizard_rows(source: str, filename: str, language: str) -> list[dict[str, str]]:
    if not source.strip():
        return []
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / Path(filename).name
        dest.write_text(source, encoding="utf-8")
        csv_path = Path(tmp) / "out.csv"
        subprocess.run(
            [
                "lizard",
                "-l",
                language,
                "-C",
                "999",
                "-L",
                "999999",
                "-o",
                str(csv_path),
                str(dest),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        text = csv_path.read_text(encoding="utf-8")
    rows = []
    for rec in csv.reader(io.StringIO(text)):
        if len(rec) < 2 or not rec[0].isdigit():
            continue
        rows.append(
            {"nloc": rec[0], "ccn": rec[1], "name": rec[7] if len(rec) > 7 else ""}
        )
    return rows


def is_complex(
    rows: list[dict[str, str]], ccn_limit: int, nloc_limit: int
) -> tuple[bool, int, int]:
    max_ccn = 0
    max_nloc = 0
    for row in rows:
        max_ccn = max(max_ccn, int(row["ccn"]))
        max_nloc = max(max_nloc, int(row["nloc"]))
    return max(max_ccn - ccn_limit, max_nloc - nloc_limit) > 0, max_ccn, max_nloc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/master")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--ccn", type=int, default=DEFAULT_CCN)
    parser.add_argument("--nloc", type=int, default=DEFAULT_NLOC)
    parser.add_argument("--fraction", type=float, default=0.10)
    args = parser.parse_args()
    if args.fraction <= 0 or args.fraction > 1:
        print("check-hotspots: --fraction must be in (0, 1]", file=sys.stderr)
        return 2
    repo = Path(args.repo).resolve()
    try:
        files = changed_files(repo, args.base)
        counts = change_counts(repo)
        hot, threshold = top_change_set(counts, args.fraction)
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"check-hotspots: {exc}", file=sys.stderr)
        return 2
    if not files:
        print("check-hotspots: no changed Python or Vue files")
        return 0

    failures = []
    for rel in sorted(set(files) & hot):
        src = (repo / rel).read_text(encoding="utf-8")
        language = SUFFIX_LANGUAGE[Path(rel).suffix]
        try:
            rows = lizard_rows(src, rel, language)
        except (subprocess.CalledProcessError, OSError) as exc:
            print(f"check-hotspots: lizard failed on {rel}: {exc}", file=sys.stderr)
            return 2
        complex_file, max_ccn, max_nloc = is_complex(rows, args.ccn, args.nloc)
        if complex_file:
            failures.append(
                f"HOT {rel} commits={counts.get(rel, 0)} "
                f"maxCCN={max_ccn} maxNLOC={max_nloc} "
                f"(top {args.fraction:.0%} threshold {threshold} commits)"
            )
    if failures:
        print("check-hotspots: FAIL", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    print(f"check-hotspots: PASS ({len(files)} changed Python/Vue file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
