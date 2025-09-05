# scripts/run_api_tests.py
# Script to run API tests using pytest and Postman collections
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Run comprehensive API tests for GraphRAG API Service."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_pytest_tests(test_type: str = "all") -> int:
    """Run pytest-based API tests.

    Args:
        test_type: Type of tests to run (all, api, graphql, integration)

    Returns:
        Exit code
    """
    print("Running pytest API tests...")
    print("=" * 60)

    test_files = {
        "api": "tests/test_api_integration.py",
        "graphql": "tests/test_graphql_integration.py",
        "postman": "tests/test_postman_runner.py",
        "all": "tests/test_api_integration.py tests/test_graphql_integration.py tests/test_postman_runner.py",
    }

    test_file = test_files.get(test_type, test_files["all"])

    cmd = ["poetry", "run", "pytest", "-v"]
    cmd.extend(test_file.split())

    if test_type == "integration":
        cmd.extend(["-m", "integration"])

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def run_postman_collections() -> int:
    """Run Postman collections using the Python runner.

    Returns:
        Exit code
    """
    print("\nRunning Postman collections...")
    print("=" * 60)

    cmd = ["poetry", "run", "python", "tests/test_postman_runner.py"]
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def run_newman_tests() -> int:
    """Run Postman collections using Newman CLI if available.

    Returns:
        Exit code
    """
    print("\nChecking for Newman CLI...")

    # Check if newman is installed
    try:
        subprocess.run(["newman", "--version"], capture_output=True, check=True)
        print("Newman found, running collections...")
        print("=" * 60)

        collections = [
            "tests/postman/graphrag_api_collection.json",
            "tests/postman/graphql_collection.json",
        ]

        for collection in collections:
            print(f"\nRunning {Path(collection).name}...")
            cmd = [
                "newman",
                "run",
                collection,
                "-e",
                "tests/postman/environment.json",
                "--reporters",
                "cli,json",
                "--reporter-json-export",
                f"{collection}.results.json",
            ]
            result = subprocess.run(cmd, capture_output=False)
            if result.returncode != 0:
                return result.returncode

        return 0

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Newman not found. Install with: npm install -g newman")
        return 0  # Don't fail if Newman isn't installed


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run API tests for GraphRAG API Service")
    parser.add_argument(
        "--type",
        choices=["all", "api", "graphql", "postman", "integration"],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument("--newman", action="store_true", help="Also run tests using Newman CLI")

    args = parser.parse_args()

    # Run pytest tests
    exit_code = run_pytest_tests(args.type)

    # Run Postman collections with Python
    if args.type in ["all", "postman"]:
        postman_code = run_postman_collections()
        if postman_code != 0:
            exit_code = postman_code

    # Optionally run Newman tests
    if args.newman:
        newman_code = run_newman_tests()
        if newman_code != 0:
            exit_code = newman_code

    if exit_code == 0:
        print("\n" + "=" * 60)
        print("All API tests passed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Some API tests failed. Please review the output above.")
        print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
