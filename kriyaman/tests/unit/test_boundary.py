import ast
from pathlib import Path

# Directories belonging to the rebuild
REBUILD_PACKAGES = ["app", "domain", "application", "adapters", "persistence", "tests"]
REBUILD_PACKAGES = ["app", "domain", "application", "adapters", "persistence", "kriyaman_ui", "tests"]
PROHIBITED_IMPORTS = {"backend", "chromadb", "chroma", "agents", "services", "api"}


def test_architectural_boundary_and_no_legacy_imports():
    """Verify that all rebuilt code does not import from legacy packages or ChromaDB."""
    root_dir = Path(__file__).resolve().parent.parent.parent

    violations = []

    for pkg_name in REBUILD_PACKAGES:
        pkg_dir = root_dir / pkg_name
        if not pkg_dir.exists():
            continue

        for py_file in pkg_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except SyntaxError as e:
                    violations.append(f"Syntax error in {py_file}: {e}")
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                        if top_pkg in PROHIBITED_IMPORTS or alias.name.startswith("kriyaman.agents") or alias.name.startswith("kriyaman.services"):
                            violations.append(
                                f"{py_file}:{node.lineno} imports prohibited module '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split(".")[0]
                        if top_pkg in PROHIBITED_IMPORTS or node.module.startswith("kriyaman.agents") or node.module.startswith("kriyaman.services"):
                            violations.append(
                                f"{py_file}:{node.lineno} imports prohibited module '{node.module}'"
                            )

    assert not violations, "Architectural boundary violations found:\n" + "\n".join(violations)


def test_no_memory_saver_in_application_runtime():
    """Verify that production application runtime code never imports or references MemorySaver."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    app_dir = root_dir / "application"

    violations = []
    for py_file in app_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "MemorySaver" in content:
                violations.append(f"{py_file} references MemorySaver")

    assert not violations, "Production application runtime must not use MemorySaver:\n" + "\n".join(violations)


def test_ui_isolation_boundary():
    """Verify that kriyaman_ui thin client only consumes HTTP API and has no internal dependencies."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    ui_dir = root_dir / "kriyaman_ui"
    if not ui_dir.exists():
        return

    internal_backend_packages = {"application", "persistence", "adapters", "domain"}
    violations = []

    for py_file in ui_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_pkg = alias.name.split(".")[0]
                    if top_pkg in internal_backend_packages:
                        violations.append(f"{py_file}:{node.lineno} UI imports internal backend '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_pkg = node.module.split(".")[0]
                    if top_pkg in internal_backend_packages:
                        violations.append(f"{py_file}:{node.lineno} UI imports internal backend '{node.module}'")

    assert not violations, "UI isolation boundary violations found:\n" + "\n".join(violations)


def test_no_files_outside_kriyaman():
    """Verify that no rebuilt files were created in parent legacy directories."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    parent_backend = root_dir.parent / "backend"
    
    # We should never find new rebuild artifacts in parent backend
    if parent_backend.exists():
        assert not (parent_backend / "domain").exists()
        assert not (parent_backend / "adapters").exists()
        assert not (parent_backend / "persistence").exists()

