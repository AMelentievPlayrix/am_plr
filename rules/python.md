---
paths:
  - "**/*.py"
---

# Python rules

Python specifics on top of `code.md`, for Python 3.10 (the version the VSO repos target). Loaded when working
on Python files. Based on vso-engine-autotests `.cursor/rules/python.mdc`, updated.
Priority when rules conflict: critical → important → best practice.

## Tooling — critical

- Formatting, import order and lint are owned by ruff: run the project's formatter and linter
  (`make code-style` / `make code-style-check` in vso-engine-autotests; otherwise `ruff format` and
  `ruff check --fix`). Don't hand-format against it.
- Write code that passes ruff's `E`, `F`, `B`, `UP`, `SIM`, `RUF` rule sets and a type checker (pyright or
  mypy, basic mode), even where the project has only enabled fewer rules so far.

## Type hints — critical

- Type hints on every parameter and return type (`-> None` explicit), and on class and instance attributes.
  Omit them for `self`/`cls`, the return of `__init__`, test function returns, and the `step`, `data` and
  `device` test fixtures.
- 3.10 syntax: `X | None` and `A | B`, never `Optional` or `Union`; built-in generics `list[int]`,
  `dict[str, Any]`, never `typing.List` or `typing.Dict`.
- Abstract types from `collections.abc`, not `typing`: `Callable`, `Iterable`, `Iterator`, `Sequence`, `Mapping`.
- Parameters take the most general type that works (`Sequence`, `Mapping`, `Iterable`); return values use
  concrete types (`list`, `dict`).
- `Self` doesn't exist in `typing` on 3.10: import it from `typing_extensions`, or use the class name in quotes.
- `Any` only when the type truly can't be known.

## Type hints — important

- `Literal[...]` for fixed sets of values; `Final` for module and class constants.
- `Protocol` for interfaces satisfied by duck typing; `TypedDict` for dict-shaped payloads such as JSON from APIs.
- `Callable[[A, B], R]` for callables.

## Structure — critical

- Class member order:
  1. `__init__`
  2. abstract members: properties first, then methods
  3. public: properties first, then methods
  4. protected (`_name`): properties first, then methods
  5. private (`__name`): properties first, then methods
- `@staticmethod` for methods that use no instance or class state.

## Idioms — important

- Structured data: `@dataclass(frozen=True, slots=True)` (or a Pydantic model where the project uses
  Pydantic) instead of loose dicts or tuples.
- `pathlib.Path` instead of `os.path`; f-strings for formatting; `with` for files, locks, sessions and
  anything else that must be closed.
- `match` where it makes dispatch on a value's shape or type clearer than an `if` chain.
- Named arguments in calls where they make the meaning clearer.
- Logging with lazy formatting: `logger.info("loaded %s items", count)`, not f-strings in log calls.
- Exceptions: `raise NewError(...) from e` when translating; never a bare `except:`; subclass `Exception`
  for domain errors.
- Define `__all__` only when asked.

## Tests (pytest)

- Fixtures for setup, `@pytest.mark.parametrize` for variants, plain `assert` only where the project allows it
  (vso-engine-autotests tests verify through `step.check.*` instead).
