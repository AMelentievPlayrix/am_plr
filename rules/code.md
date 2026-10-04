# Code rules

General rules for any code you write or change, in any language. Python specifics are in `python.md`.
Based on vso-engine-autotests `.cursor/rules/code.mdc`, updated. Priority when rules conflict:
critical → important → best practice. The project's own rules win where they are stricter.

## Critical

- Production code is complete and working: no stubs, placeholders or dummy methods. (Test code may keep an
  unimplementable step as commented code with a reason, where the test rules allow it.)
- Consider the security impact of every change. Secrets only from environment variables or a secret store;
  never hardcoded, never logged, never committed.
- Validate input at boundaries: user input, files, network and external APIs.

## Important

- Prefer the simplest design that works (KISS, YAGNI). Add an abstraction or design pattern only when it
  removes real duplication or a real coupling problem, not in anticipation.
- Single-purpose functions and classes; no duplicated logic (DRY); composition over inheritance.
- Put values that may change in constants or configuration, not inline.
- Match the style and structure of the surrounding code.

## Documentation

- Self-documenting code: descriptive names for variables, functions, classes and modules.
- Comments only for corner cases, non-obvious behaviour, complex algorithms or business rationale.
  Explain *why*, not *what*.
- Docstrings only for public APIs, complex interfaces, and functions with non-trivial contracts or
  counter-intuitive behaviour. Don't restate types or the obvious in docstrings.

## Errors

- Let exceptions propagate unless there is specific handling to do.
- Catch only to recover from an expected error, to translate it, or to clean up. Catch specific exception
  types; never a bare catch-all that hides the cause.
- When translating an exception, keep the original cause attached.
- Use dedicated error types for domain errors callers are expected to handle.

## Logging

- Log errors, warnings, important state changes and calls to external services.
- Levels: DEBUG for diagnostics, INFO for significant events, WARNING for recoverable problems, ERROR for failures.
- Include context (IDs, parameters, state), but never secrets, tokens or personal data.
- Log meaningful events, not every obvious step.

## Tests

- No fixed sleeps: wait on an observable condition.
- Each test checks the expected behaviour directly; don't weaken an assertion to make a test pass.
- Share setup through the framework's fixture mechanism; use parametrisation instead of copy-pasted tests.
