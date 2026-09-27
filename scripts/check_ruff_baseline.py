"""Compare current ruff findings to a committed baseline.

CI fails when a finding is new. This command does not rewrite the baseline
unless --write-baseline is passed, and it refuses that flag in CI.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

DEFAULT_PATHS = ("src", "scripts", "tests", "run_all_tests.py")
DEFAULT_BASELINE = Path("config/ruff-baseline.txt")


def ruff_findings(repo: Path, paths: list[str]) -> list[tuple[str, str, str]]:
    targets = [str(repo / path) for path in paths]
    result = subprocess.run(
        ["ruff", "check", "--output-format", "json", *targets],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "ruff failed")
    if not result.stdout.strip():
        return []
    payload = json.loads(result.stdout)
    if isinstance(payload, dict):
        payload = payload.get("diagnostics", [])
    findings = []
    for item in payload:
        filename = str(item.get("filename") or "")
        try:
            rel = str(Path(filename).resolve().relative_to(repo))
        except ValueError:
            rel = filename
        rel = rel.replace("\\", "/")
        findings.append(
            (rel, str(item.get("code") or ""), str(item.get("message") or ""))
        )
    return findings


def load_baseline(path: Path) -> Counter[tuple[str, str, str]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rel, code, message = stripped.split("\t", 2)
        counts[(rel, code, message)] += 1
    return counts


def render(counts: Counter[tuple[str, str, str]]) -> str:
    lines = [
        "# ruff baseline. CI compares this file and must not rewrite it.",
        "# path<TAB>code<TAB>message — one line per occurrence.",
    ]
    for key in sorted(counts):
        for _ in range(counts[key]):
            lines.append("\t".join(key))
    lines.append("")
    return "\n".join(lines)


def in_ci() -> bool:
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Rewrite the baseline. Refused when CI or GITHUB_ACTIONS is set.",
    )
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = repo / baseline_path
    try:
        current = Counter(ruff_findings(repo, args.paths))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"check-ruff-baseline: {exc}", file=sys.stderr)
        return 2

    if args.write_baseline:
        if in_ci():
            print(
                "check-ruff-baseline: refusing to rewrite the baseline in CI",
                file=sys.stderr,
            )
            return 2
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(render(current), encoding="utf-8")
        print(f"check-ruff-baseline: wrote {baseline_path} ({sum(current.values())})")
        return 0

    baseline = load_baseline(baseline_path)
    new_items = []
    for key, count in sorted(current.items()):
        extra = count - baseline[key]
        if extra > 0:
            rel, code, message = key
            new_items.append(f"NEW x{extra} {rel}:{code} {message}")
    if new_items:
        print("check-ruff-baseline: FAIL", file=sys.stderr)
        for line in new_items:
            print(line, file=sys.stderr)
        return 1
    print(
        "check-ruff-baseline: PASS "
        f"({sum(current.values())} current, {sum(baseline.values())} baselined)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
