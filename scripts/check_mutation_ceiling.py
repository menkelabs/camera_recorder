"""Compare a mutmut export to the committed survived ceiling.

Reads mutants/mutmut-cicd-stats.json and config/mutation-swing-score-baseline.json.
Fails when survived mutants increase. Does not write the baseline and does not
start mutmut.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "config" / "mutation-swing-score-baseline.json"
DEFAULT_STATS = ROOT / "mutants" / "mutmut-cicd-stats.json"


def compare(baseline: dict, stats: dict) -> tuple[int, str]:
    if int(stats.get("check_was_interrupted_by_user") or 0) > 0:
        return 1, "check-mutation-ceiling: FAIL interrupted run"
    if int(stats.get("total") or 0) <= 0:
        return 1, "check-mutation-ceiling: FAIL empty mutmut export"
    allowed = int(baseline["survived"])
    survived = int(stats["survived"])
    if survived > allowed:
        return 1, f"check-mutation-ceiling: FAIL survived {allowed} -> {survived}"
    return 0, f"check-mutation-ceiling: PASS survived {survived} (ceiling {allowed})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--stats", type=Path, default=DEFAULT_STATS)
    args = parser.parse_args()
    if not args.baseline.is_file():
        print(f"missing mutation baseline: {args.baseline}", file=sys.stderr)
        return 2
    if not args.stats.is_file():
        print(f"missing mutmut stats: {args.stats}", file=sys.stderr)
        return 2
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    code, message = compare(baseline, stats)
    print(message, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
