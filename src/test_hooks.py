"""Test file to verify pre-commit hooks run automatically."""


def test_function():
    x = 1 + 2  # Formatting issue: missing spaces around operators
    return x


print("Should use double quotes")  # Style issue: single quotes
