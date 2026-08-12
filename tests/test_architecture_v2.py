import ast
from pathlib import Path


def test_dependency_boundaries_and_module_cohesion() -> None:
    source = Path("src/livebench_hermes_ab")
    for path in source.glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        if path.name != "cli.py":
            assert not any(module and module.endswith("cli") for module in imports)
        if path.name == "scheduler.py":
            assert not ({"subprocess", "yaml"} & imports)
        if path.name == "report.py":
            assert "pathlib" not in imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                assert node.end_lineno - node.lineno < 80, f"oversized function: {path}:{node.name}"
