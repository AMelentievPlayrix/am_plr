---
paths:
  - "**/*.py"
---

# Python style rules

Copied from vso-engine-autotests `.cursor/rules/python.mdc`. Loaded when working on Python files.
Priority when rules conflict: critical → important → best practice. Ruff (`make code-style`) enforces formatting.

## Class layout — critical

- Class member order:
  1. __init__ method
  2. Abstract methods: properties first, then methods
  3. Public: properties first, then methods
  4. Protected (_): properties first, then methods
  5. Private (__): properties first, then methods
- Minimize docstrings for internal methods

## Type hints — critical

- Use Python 3.10+ union syntax: `X | None` instead of `Optional[X]`
- Add type hints to all function/method parameters and return types (including `None`)
- Add type hints for all class and instance attributes
- Use `Self` for methods returning their own class instance
- Use `Any` only when type cannot be determined
- Omit type hints for: test function returns, `self` and `cls` parameters
- Omit type hints for return of __init__ function

## Type hints — important

- Use built-in generics: `list[int]`, `dict[str, Any]` instead of `typing.List`, `typing.Dict`
- Use `Literal[...]` for fixed value sets
- Use `Callable[[T1, T2], TResult]` for callable types

## Formatting — critical

- Follow Black formatting: 120 character line length, double quotes, 4-space indent
- Add trailing comma after last item in multiline structures
- Maintain clean spacing: no extra spaces inside parentheses, brackets, or braces
- Use only necessary blank lines

## Imports — critical

- Sort imports in three groups: standard library, third-party, local (alphabetically within each)
- Keep only used imports without duplicates

## Python — best practice

- Use named arguments in function calls when clarity improves
- Use `@staticmethod` for methods without instance or class state access
- Define `__all__` only when explicitly requested
