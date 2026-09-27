"""Clean as You Code: lint only the diff.

New ruff findings on changed Python fail the build. Findings that already
exist on the base revision are printed and do not fail. Eslint runs on
changed Vue/TS/JS only when the frontend already has an eslint config.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

PY_SUFFIXES = {".py"}
ESLINT_SUFFIXES = {".vue", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
ESLINT_CONFIG_NAMES = (
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    "eslint.config.ts",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.cjs",
    ".eslintrc.json",
    ".eslintrc.yml",
    ".eslintrc.yaml",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True
    ).rstrip("\n")


def changed_files(repo: Path, base: str, suffixes: set[str]) -> list[str]:
    rels = git(repo, "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    files = []
    for line in rels.splitlines():
        rel = line.strip().replace("\\", "/")
        if rel and Path(rel).suffix in suffixes:
            files.append(rel)
    return files


def file_at(repo: Path, rev: str, rel: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"{rev}:{rel}"],
            cwd=repo,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None


def ruff_json(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    result = subprocess.run(
        ["ruff", "check", "--output-format", "json", str(path)],
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
    return list(payload)


def classify(base_diags: list[dict], head_diags: list[dict]) -> list[tuple[str, dict]]:
    base_counts: Counter[tuple[str, str]] = Counter(
        (str(item.get("code") or ""), str(item.get("message") or ""))
        for item in base_diags
    )
    seen: Counter[tuple[str, str]] = Counter()
    classified = []
    for item in head_diags:
        key = (str(item.get("code") or ""), str(item.get("message") or ""))
        seen[key] += 1
        kind = "OLD" if seen[key] <= base_counts[key] else "NEW"
        classified.append((kind, item))
    return classified


def format_ruff(kind: str, rel: str, item: dict) -> str:
    loc = item.get("location") or {}
    row = loc.get("row", "?")
    code = item.get("code") or ""
    message = item.get("message") or ""
    return f"{kind} {rel}:{row}:{code} {message}"


def eslint_config(repo: Path) -> Path | None:
    frontend = repo / "frontend"
    if not frontend.is_dir():
        return None
    for name in ESLINT_CONFIG_NAMES:
        candidate = frontend / name
        if candidate.is_file():
            return candidate
    package = frontend / "package.json"
    if not package.is_file():
        return None
    data = json.loads(package.read_text(encoding="utf-8"))
    if data.get("eslintConfig"):
        return package
    deps = {}
    deps.update(data.get("dependencies") or {})
    deps.update(data.get("devDependencies") or {})
    if "eslint" in deps:
        return package
    return None


def eslint_on(repo: Path, files: list[str]) -> tuple[list[str], list[str]]:
    """Return (visible findings, new failures). No config means both empty."""
    if eslint_config(repo) is None or not files:
        return [], []
    frontend = repo / "frontend"
    rels = []
    for rel in files:
        path = Path(rel)
        if path.parts and path.parts[0] == "frontend":
            rels.append(str(Path(*path.parts[1:])))
        else:
            rels.append(rel)
    result = subprocess.run(
        ["npx", "--no-install", "eslint", "--format", "json", *rels],
        cwd=frontend,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or "eslint failed")
    payload = json.loads(result.stdout or "[]")
    visible = []
    fresh = []
    for entry in payload:
        for message in entry.get("messages") or []:
            line = (
                f"{entry.get('filePath')}:{message.get('line')}:"
                f"{message.get('ruleId')} {message.get('message')}"
            )
            visible.append(line)
            fresh.append(line)
    return visible, fresh


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/master")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    try:
        py_files = changed_files(repo, args.base, PY_SUFFIXES)
        ui_files = changed_files(repo, args.base, ESLINT_SUFFIXES)
    except subprocess.CalledProcessError as exc:
        print(f"check-diff-lint: git diff failed: {exc}", file=sys.stderr)
        return 2

    new_findings: list[str] = []
    old_findings: list[str] = []
    for rel in py_files:
        head_path = repo / rel
        head_diags = ruff_json(head_path)
        base_src = file_at(repo, args.base, rel)
        if base_src is None:
            base_diags: list[dict] = []
        else:
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / Path(rel).name
                dest.write_text(base_src, encoding="utf-8")
                base_diags = ruff_json(dest)
        for kind, item in classify(base_diags, head_diags):
            line = format_ruff(kind, rel, item)
            if kind == "NEW":
                new_findings.append(line)
            else:
                old_findings.append(line)

    if eslint_config(repo) is None:
        print("eslint: no frontend lint config; skipped")
    else:
        try:
            visible, fresh = eslint_on(repo, ui_files)
        except (OSError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"check-diff-lint: eslint failed: {exc}", file=sys.stderr)
            return 2
        for line in visible:
            print(f"ESLINT {line}")
        new_findings.extend(f"NEW eslint {line}" for line in fresh)

    for line in old_findings:
        print(line)
    if new_findings:
        print("check-diff-lint: FAIL", file=sys.stderr)
        for line in new_findings:
            print(line, file=sys.stderr)
        return 1
    print(
        "check-diff-lint: PASS "
        f"({len(py_files)} python, {len(ui_files)} frontend file(s); "
        f"{len(old_findings)} old finding(s) still visible)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
