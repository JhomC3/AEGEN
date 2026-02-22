import ast
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _analyze_file_functions(py_file: Path, max_lines_func: int) -> list[str]:
    file_violations = []
    try:
        content = py_file.read_text()
        tree = ast.parse(content)
    except Exception as e:
        logger.debug("Parse error %s: %s", py_file, e)
        return []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if start is not None and end is not None:
            length = end - start
            if length > max_lines_func:
                file_violations.append(
                    f"{py_file}:{start} - {node.name} ({length} lines)"
                )
    return file_violations


def check_function_lengths() -> None:
    max_lines = 50
    violations = []
    for py_file in Path("src").glob("**/*.py"):
        violations.extend(_analyze_file_functions(py_file, max_lines))
    if violations:
        print(f"Warning: {len(violations)} functions exceed {max_lines} lines.")
        for v in sorted(violations, reverse=True)[:10]:
            print(f"   {v}")


def check_file_lengths() -> None:
    max_lines = 200
    violations = []
    for py_file in Path("src").glob("**/*.py"):
        if py_file.name == "main.py":
            continue
        count = len(py_file.read_text().splitlines())
        if count > max_lines:
            violations.append(f"{py_file}: {count} lines")
    if violations:
        print(f"Warning: {len(violations)} files exceed {max_lines} lines.")
        for v in violations:
            print(f"   {v}")


def main() -> None:
    check_function_lengths()
    check_file_lengths()
    print("Done")


if __name__ == "__main__":
    main()
