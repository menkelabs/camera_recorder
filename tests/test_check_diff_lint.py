"""Clean as You Code grades changed Vue files and keeps old findings."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "check_diff_lint.py"
    spec = importlib.util.spec_from_file_location("check_diff_lint", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _commit(repo: Path, message: str) -> None:
    subprocess.check_call(["git", "add", "."], cwd=repo)
    subprocess.check_call(
        [
            "git",
            "-c",
            "user.email=ratchet@example.com",
            "-c",
            "user.name=ratchet",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
    )


def test_classify_keeps_existing_findings_and_flags_new_ones() -> None:
    mod = _load()
    base = [{"code": "vue/html-self-closing", "message": "require self close"}]
    head = [
        {"code": "vue/html-self-closing", "message": "require self close"},
        {"code": "vue/max-attributes-per-line", "message": "too many"},
    ]
    kinds = [kind for kind, _item in mod.classify(base, head)]
    assert kinds == ["OLD", "NEW"]


def test_frontend_eslint_config_is_present() -> None:
    mod = _load()
    found = mod.eslint_config(ROOT)
    assert found is not None
    assert found.name == "eslint.config.js"


def test_vue_sources_without_eslint_config_fail(tmp_path: Path) -> None:
    subprocess.check_call(["git", "init"], cwd=tmp_path)
    vue = tmp_path / "frontend" / "src"
    vue.mkdir(parents=True)
    target = vue / "App.vue"
    target.write_text("<template><p>Hi</p></template>\n", encoding="utf-8")
    _commit(tmp_path, "init")
    target.write_text("<template><p>Hello</p></template>\n", encoding="utf-8")
    _commit(tmp_path, "edit")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_diff_lint.py"),
            "--repo",
            str(tmp_path),
            "--base",
            "HEAD~1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "no eslint config for Vue sources" in result.stderr


def test_existing_vue_warning_stays_old_and_a_new_one_fails() -> None:
    if not (ROOT / "frontend" / "node_modules" / "eslint").is_dir():
        pytest.skip("eslint is not installed")
    mod = _load()
    frontend = ROOT / "frontend"
    dest = frontend / ".cayc-tmp" / "SamplePanel.vue"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        '<template>\n  <div role="main" aria-label="x">Hi</div>\n</template>\n',
        encoding="utf-8",
    )
    try:
        diags = mod.eslint_diags(frontend, [dest])[dest.resolve()]
        assert diags
        old = [kind for kind, _item in mod.classify(diags, diags)]
        fresh = [kind for kind, _item in mod.classify([], diags)]
    finally:
        shutil.rmtree(frontend / ".cayc-tmp", ignore_errors=True)
    assert old
    assert set(old) == {"OLD"}
    assert "NEW" in fresh
