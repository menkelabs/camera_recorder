"""Fitness: ``python run_all_tests.py --unit`` stays off the camera.

The unit list is ``UNIT_TEST_MODULES`` in ``run_all_tests.py``. Hardware
scripts live in ``HARDWARE_TEST_SCRIPTS``. The hardware opener is
``dual_camera_soak.run_hardware``, which calls
``camera_utils.create_camera_capture`` on a device index. Unit tests may
call ``create_camera_capture`` only while ``cv2.VideoCapture`` is patched.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVICE_CALLS = {
    "create_camera_capture",
    "VideoCapture",
    "start_cameras",
    "run_hardware",
}
EXTRA_HARDWARE_MODULES = {
    "detect_linux_cameras",
    "detect_windows_cameras",
    "camera_test_gui",
    "dual_camera_soak",
    "smoke_real_swings",
}


def _string_list(tree: ast.AST, name: str) -> list[str]:
    for node in tree.body:  # type: ignore[attr-defined]
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if not isinstance(node.value, ast.List):
            continue
        values = []
        for elt in node.value.elts:
            assert isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            values.append(elt.value)
        return values
    raise AssertionError(f"{name} is missing from run_all_tests.py")


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _guard_text(source: str, node: ast.AST) -> str:
    return ast.get_source_segment(source, node) or ""


class _Scanner(ast.NodeVisitor):
    def __init__(self, source: str, path: Path, forbidden_imports: set[str]) -> None:
        self.source = source
        self.path = path
        self.forbidden_imports = forbidden_imports
        self.guard_stack = [False]
        self.violations: list[str] = []
        self.patched = 0

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root in self.forbidden_imports or alias.name == "run_hardware":
                self.violations.append(
                    f"{self.path.name}:{node.lineno} imports {alias.name}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        root = module.split(".", 1)[0]
        names = [alias.name for alias in node.names]
        if root in self.forbidden_imports or "run_hardware" in names:
            self.violations.append(
                f"{self.path.name}:{node.lineno} imports {module} {names}"
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter_function(node)

    def _enter_function(self, node: ast.AST) -> None:
        guarded = self.guard_stack[-1] or any(
            "VideoCapture" in _guard_text(self.source, deco)
            or "create_camera_capture" in _guard_text(self.source, deco)
            or "start_cameras" in _guard_text(self.source, deco)
            for deco in getattr(node, "decorator_list", [])
        )
        self.guard_stack.append(guarded)
        self.generic_visit(node)
        self.guard_stack.pop()

    def visit_With(self, node: ast.With) -> None:
        texts = [_guard_text(self.source, item) for item in node.items]
        guarded = self.guard_stack[-1] or any(
            "VideoCapture" in text
            or "create_camera_capture" in text
            or "start_cameras" in text
            for text in texts
        )
        self.guard_stack.append(guarded)
        self.generic_visit(node)
        self.guard_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)
        if name in DEVICE_CALLS:
            if self.guard_stack[-1]:
                self.patched += 1
            else:
                self.violations.append(
                    f"{self.path.name}:{node.lineno} calls {name} without a VideoCapture patch"
                )
        self.generic_visit(node)


def test_unit_path_does_not_open_camera_or_import_hardware_recorder() -> None:
    runner = (ROOT / "run_all_tests.py").read_text(encoding="utf-8")
    tree = ast.parse(runner)
    unit_modules = _string_list(tree, "UNIT_TEST_MODULES")
    hardware_scripts = _string_list(tree, "HARDWARE_TEST_SCRIPTS")
    assert unit_modules
    assert hardware_scripts
    hardware_stems = {Path(name).stem for name in hardware_scripts}
    overlap = sorted(set(unit_modules) & hardware_stems)
    assert overlap == [], f"unit path includes hardware scripts: {overlap}"

    soak = (ROOT / "scripts" / "dual_camera_soak.py").read_text(encoding="utf-8")
    camera_utils = (ROOT / "src" / "camera_utils.py").read_text(encoding="utf-8")
    recorder = (ROOT / "src" / "dual_camera_recorder.py").read_text(encoding="utf-8")
    assert "def run_hardware" in soak
    assert "def create_camera_capture" in camera_utils
    assert "class DualCameraRecorder" in recorder
    assert "create_camera_capture" in soak

    forbidden = hardware_stems | EXTRA_HARDWARE_MODULES
    violations: list[str] = []
    patched = 0
    for module in unit_modules:
        path = ROOT / "tests" / f"{module}.py"
        assert path.is_file(), module
        source = path.read_text(encoding="utf-8")
        scanner = _Scanner(source, path, forbidden)
        scanner.visit(ast.parse(source))
        violations.extend(scanner.violations)
        patched += scanner.patched

    assert patched >= 1, "expected patched create_camera_capture calls in the unit path"
    assert violations == []
    assert "run_hardware" not in runner.split("HARDWARE_TEST_SCRIPTS", 1)[0]
