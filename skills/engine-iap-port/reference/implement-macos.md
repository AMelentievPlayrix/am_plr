Your goal is to implement the macOS test plan from the previous chat, then run and validate it on the local machine. The `.env` file is already configured for macOS — do **not** modify it.

## Prerequisites

Before writing any code, read:

1. the authoring rules ([authoring-rules.md](../../engine-create-autotest/reference/authoring-rules.md)) and the repo's `.cursor/rules/python.mdc` / `code.mdc`.
2. `tests/tests_in_app_purchase/test_{id}_*.py` — current state of the target test file.
3. `framework/test_management/test_steps/system_ui/mac_system_ui_steps.py` — only if the plan calls for new macOS steps.

## Implementation steps

1. Read the plan from the previous chat (user will reference or paste it).
2. Read the target test file fully.
3. Append `test_{id}_*_mac(step: StepManager)` to the **same file**, after the last existing platform function.
4. If the plan calls for new `MacSystemUiSteps` methods: read `mac_system_ui_steps.py` first, then add them following the existing class structure with `@mac_only_step` decorator and `@step_decorator` if used in the file.
5. If the plan calls for new code, write it.
6. Pre-commit checklist before saving:
   - No `assert` statements — verifications only via `step.check.*` or `step.purchase.*`
   - No `if PLATFORM_TO_RUN` guards — platform separation via tagged functions only
   - Imports are sorted (stdlib → third-party → local, alphabetically within each group) and no unused imports
   - Type hints on all params and returns except test function return and `self`
   - Black-compatible: 120-char lines, double quotes, 4-space indent, trailing comma in multiline structures
   - Tags come from `framework/test_management/enums/common/tags.py` only

## Validation steps

1. From the project root, run:
   ```
   make ai-run-tests key=<full_test_function_name_mac> platform_to_run=macOS
   ```
   Use the full function name as the key, e.g. `key=test_10559_purchase_network_loss_during_transaction_completion_mac`.
2. On failure: read the terminal output, identify the root cause, fix the code, and retry — **maximum 3 attempts total**.
3. After 3 failed attempts: stop, do not make further changes, and report the current state.

## Result report format

After validation completes, report:

- **Status**: PASSED / FAILED
- **Attempts**: N of 3
- **Fixes applied**: bullet list, or "none" if first run passed
- **Remaining issues**: describe if FAILED

## Post-validation

If the plan stated that `inapp_purchase.mdc` should be updated:

- Add a new entry to the `## Known patterns` section with the test number and its step sequence.
- If a new `mac_system_ui_steps.py` method was added, append its signature to the `## Available macOS steps` section in `inapp_purchase.mdc`.

## Known patterns

- **test_5822** — basic purchase: `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog`
