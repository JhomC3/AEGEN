#!/usr/bin/env python3
"""
Simple Architecture Check - Validación básica y rápida.
Reemplaza el enforce_architecture.py complejo por checks esenciales.
"""

import subprocess
import sys
from pathlib import Path


def check_file_sizes() -> bool:
    """Check that Python files are < 700 lines (per AGENTS.md)."""
    violations = []

    for py_file in Path("src").glob("**/*.py"):
        if not py_file.exists():
            continue

        lines = len(py_file.read_text().splitlines())
        if lines > 700:
            violations.append(f"{py_file}: {lines} lines (max: 700)")

    if violations:
        print("❌ File size violations:")
        for v in violations[:5]:  # Show max 5
            print(f"   {v}")
        if len(violations) > 5:
            print(f"   ... and {len(violations) - 5} more")
        return False

    return True


def check_basic_patterns() -> bool:  # noqa: C901
    """Check basic patterns in changed files."""
    try:
        # Get changed files
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        changed_files = [
            f
            for f in result.stdout.strip().split("\n")
            if f
            and f.endswith(".py")
            and not f.startswith("scripts/")
            and not f.startswith("tests/")
        ]

        if not changed_files:
            return True

        violations = []

        for file_path in changed_files:
            if not Path(file_path).exists():
                continue

            # Skip legacy or specific exception files
            if "global_knowledge_loader.py" in file_path or "polling.py" in file_path:
                continue

            content = Path(file_path).read_text()

            # Check for sync I/O patterns
            if "import requests" in content:
                violations.append(f"{file_path}: Use aiohttp instead of requests")

            if "open(" in content and "async" not in content:
                violations.append(
                    f"{file_path}: Use aiofiles for file I/O (ephemeral only)"
                )

            if '"storage/' in content or "'storage/" in content:
                violations.append(
                    f"{file_path}: Use Redis/Cloud instead of 'storage/' for persistent data"
                )

        if violations:
            print("❌ Pattern violations:")
            for v in violations:
                print(f"   {v}")
            return False

        return True

    except subprocess.CalledProcessError:
        # Git command failed, skip check
        return True


def main():
    """Simple validation - file sizes + basic patterns."""
    print("🔍 Running simple architecture checks...")

    all_passed = True

    # Check file sizes
    if not check_file_sizes():
        all_passed = False
        print("\n📏 Fix: Split large files into smaller modules")

    # Check basic patterns
    if not check_basic_patterns():
        all_passed = False
        print("\n🔄 Fix: Use async patterns (see DEVELOPMENT.md)")

    if all_passed:
        print("✅ Simple architecture checks passed!")
        return True
    else:
        print("\n❌ Architecture issues found")
        print("📚 Check DEVELOPMENT.md for guidelines")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
