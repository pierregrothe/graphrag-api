#!/usr/bin/env python
"""
scripts/run_ci_checks.py
Run all CI checks locally matching GitHub Actions workflow

Author: Pierre Grothé
Creation Date: 2025-09-05
"""

import os
import subprocess
import sys
from pathlib import Path

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{BLUE}{BOLD}{'=' * 60}{RESET}")
    print(f"{BLUE}{BOLD}{message}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 60}{RESET}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{GREEN}[SUCCESS] {message}{RESET}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{RED}[ERROR] {message}{RESET}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}[WARNING] {message}{RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{BLUE}[INFO] {message}{RESET}")


def run_command(command: str, description: str, env_vars: dict = None) -> bool:
    """Run a command and return success status."""
    print(f"\n{BOLD}Running: {description}{RESET}")
    print(f"Command: {command}")
    
    # Set up environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode == 0:
            print_success(f"{description} passed")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print_error(f"{description} failed")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
            if result.stdout:
                print(f"Standard output:\n{result.stdout}")
            return False
    except Exception as e:
        print_error(f"Failed to run command: {e}")
        return False


def main() -> int:
    """Run all CI checks."""
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print_info(f"Working directory: {project_root}")
    
    # Track overall success
    all_passed = True
    results = {}
    
    # Set up environment variables for tests
    test_env = {
        "JWT_SECRET_KEY": "test-secret-key-for-ci-only-12345678",
        "DEBUG": "true",
        "GRAPHRAG_LLM_PROVIDER": "ollama",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_LLM_MODEL": "llama2",
        "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text"
    }
    
    # ===== CODE QUALITY CHECKS =====
    print_header("CODE QUALITY CHECKS")
    
    # Black formatting check
    if run_command(
        "poetry run black --check src/ tests/",
        "Black formatting check"
    ):
        results["Black"] = "PASSED"
    else:
        results["Black"] = "FAILED"
        all_passed = False
        print_warning("Run 'poetry run black src/ tests/' to fix formatting")
    
    # Ruff linting
    if run_command(
        "poetry run ruff check src/ tests/",
        "Ruff linting"
    ):
        results["Ruff"] = "PASSED"
    else:
        results["Ruff"] = "FAILED"
        all_passed = False
        print_warning("Run 'poetry run ruff check --fix src/ tests/' to fix issues")
    
    # MyPy type checking
    if run_command(
        "poetry run mypy src/graphrag_api_service",
        "MyPy type checking",
        test_env
    ):
        results["MyPy"] = "PASSED"
    else:
        results["MyPy"] = "FAILED"
        all_passed = False
    
    # Bandit security check
    if run_command(
        "poetry run bandit -r src/ -ll",
        "Bandit security check",
        test_env
    ):
        results["Bandit"] = "PASSED"
    else:
        results["Bandit"] = "FAILED"
        all_passed = False
    
    # ===== UNIT TESTS =====
    print_header("UNIT TESTS")
    
    # Run unit tests with coverage
    if run_command(
        "poetry run pytest tests/unit/ --cov=src/graphrag_api_service --cov-report=term-missing -v",
        "Unit tests with coverage",
        test_env
    ):
        results["Unit Tests"] = "PASSED"
    else:
        results["Unit Tests"] = "FAILED"
        all_passed = False
    
    # ===== ADDITIONAL CHECKS (Not in CI but useful locally) =====
    print_header("ADDITIONAL LOCAL CHECKS")
    
    # Check if pre-commit hooks pass
    if run_command(
        "pre-commit run --all-files",
        "Pre-commit hooks"
    ):
        results["Pre-commit"] = "PASSED"
    else:
        results["Pre-commit"] = "FAILED"
        print_warning("Some pre-commit hooks failed but may have auto-fixed issues")
    
    # ===== SUMMARY =====
    print_header("SUMMARY")
    
    for check, status in results.items():
        if status == "PASSED":
            print(f"{GREEN}[PASS] {check}{RESET}")
        else:
            print(f"{RED}[FAIL] {check}{RESET}")
    
    print()
    if all_passed:
        print_success("All CI checks passed! Ready to commit and push.")
        return 0
    else:
        print_error("Some checks failed. Please fix the issues before pushing.")
        print_info("Tip: Run 'poetry run black src/ tests/' and 'poetry run ruff check --fix src/ tests/' to auto-fix many issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())