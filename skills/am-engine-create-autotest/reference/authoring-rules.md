# Authoring rules for VSO engine autotests

Originally ported from vso-engine-autotests `.cursor/rules/test.mdc` and since corrected against the
repo; where they disagree, this file and the code win. Priority order when rules conflict:
**Critical → Important → Best practice.**

All generated Python must additionally satisfy `.cursor/rules/code.mdc` and
`.cursor/rules/python.mdc`: Python 3.10+ type-hint syntax, 120-char lines, double
quotes, 4-space indent, import order, class member order, naming, docstring policy,
error handling. `make code-style` applies ruff format + lint.

---

## Qase — critical

- Read the case with `mcp__qase__get_test_case_data(project_code="VSO", test_case_id=<id>)`.
- Case steps are the **primary source of truth** for implementation.
- Include the case id in both the test name and the file name. Ask if it is unclear.
- Implement the case preconditions:
  - implementable with available steps → apply them **first** in the test;
  - not implementable → commented code plus an explanation of why.

## Qase — important

- Add only the tags the case actually requires.
- When a step carries a platform prefix (`iOS:`, `Android:`), analyse each step on its own.

---

## Test structure — critical

- Create only new test files, one test per file.
- Use only the `step` and `data` fixtures (plus parametrization arguments when parametrized).
- **No `assert` statements in test functions.** Every verification goes through `step.check.*`.
- Perform all actions through existing steps.
- Modify only the test file being created.
- No step comments or action narration (`# Step 1: ...`, `# Set user`).
- Add only the verifications the case's expected results describe (widgets, logs, database).
- Omit implicit state confirmations such as "app is backgrounded".
- Put database checks in a separate test function — see the SDK sections below.
- A verification that cannot be implemented becomes commented code with an explanation.
- Every case step must appear; when no implementation exists, add commented code carrying
  the step number and the reason.
- Omit type hints for the `step`, `data` and `device` fixtures.

## Test structure — important

- Match the code style of the other tests in the same directory.
- Read neighbouring test files for correct step-usage patterns before writing.

## Test structure — best practice

- Keep descriptions minimal.
- When uncertain, add commented code with an explanation rather than a guess.

---

## Step usage — critical

- Use only existing steps from `framework/test_management/test_steps`.
- When a new step is genuinely needed, add it to the right file under that package:
  - names must be **business-oriented** — intent, not UI/API/service mechanics
    (`confirm_purchase`, not `purchase_success_dialog_click_ok`);
  - use services and/or utils internally; no raw UI or API calls inline;
  - accept arguments when behaviour varies by caller;
  - read the existing steps in that file first and match their structure.
- Verify a step method exists in the implementation file before calling it.
- **Decorator safety check** — grep the implementation of every step you use:
  - `@ios_only_step` → iOS only
  - `@android_only_step` → Android only
  - `@bs_only_step` → BrowserStack platforms only (iOS, Android)
  - `@mac_only_step`, `@uwp_only_step` → that desktop platform only
  - `@ios_macos_only_step` → iOS and macOS only
  - no platform decorator → cross-platform
  - decorator conflicts with the case's platform requirements → report it in chat and
    leave a `TODO` comment; do not silently drop the step.

## Step usage — important

Use common steps plus the steps for the SDK under test. Namespaces:

| Namespace | Source | Availability |
|---|---|---|
| `step.app.internet_reachability.*` | `app_widget/internet_reachability` | all tests |
| `step.app.shared.*` | `app_widget/shared` | all tests |
| `step.app.marketing_tracker.*` | `app_widget/marketing_authorization` | all tests |
| `step.device.*` | `device` | all tests |
| `step.app.crashes.*`, `step.sentry.*` | `app_widget/crashes`, `sentry` | Sentry tests |
| `step.app.appsflyer.*`, `step.appsflyer.*` | `app_widget/appsflyer`, `appsflyer` | AppsFlyer tests |
| `step.purchase.*` | `purchase` | purchase tests |

Reference tests: `tests/test_sentry`, `tests/tests_appsflyer`, `tests/tests_in_app_purchase`,
`tests/tests_adjust`, `tests/tests_amplitude`.

---

## Platform logic — critical

The Qase case decides platform-specific logic. Namespace rules:

- `step.app.*` → no platform check; the app handles it internally.
- `step.device.*` → add a check **only** when the case specifies a platform prefix.
- `step.<sdk>.*` (sentry, appsflyer, adjust, amplitude) → no platform check.

Interpretation algorithm:

1. Read the step description.
2. Step has a platform prefix (`iOS: Tap Allow`):
   - decide app-level command vs device-level system interaction;
   - app-level → `step.app.*`, no check;
   - device-level → `step.device.*` guarded by `if PLATFORM_TO_RUN == Platform.IOS:`.
3. No prefix → applies to all platforms; use `step.app.*` / `step.<sdk>.*` / cross-platform
   `step.device.*` without checks.
4. When the case groups actions under a platform heading, analyse each action separately.

## Platform logic — important

Common patterns:

| Case step | Implementation |
|---|---|
| `Request tracking authorization` | `step.app.marketing_tracker.request_tracking_authorization()` — no check |
| `iOS: Tap Allow` | `if PLATFORM_TO_RUN == Platform.IOS: step.device.authorize_att_tracking(allow=True)` |
| `Set user` | `step.app.appsflyer.set_user()` — no check |
| `Background app` | `step.device.background_app_for_duration()` — no check |
| `Android: Enable X` | `if PLATFORM_TO_RUN == Platform.ANDROID: step.device.<action>()` |

A command that triggers UI → `step.app.*` (no check). Interaction with that UI →
`step.device.*` (checked when the case says so).

Validation workflow: implement from the case → grep each `step.device.*` for decorators →
verify compatibility → on a conflict, explain in chat and add a `TODO`.

---

## Tagging — critical

- Use only tags that exist in the `Tag` enum at
  `framework/test_management/enums/common/tags.py`. Read the file; do not assume.
- `APPSFLYER_CHECK` platform tags must match **all** `APPSFLYER_INIT` platforms:
  - iOS (INIT) → `IOS_ON_LINUX` (CHECK)
  - Android (INIT) → `ANDROID_ON_LINUX` (CHECK)
  - MAC → `MAC`; UWP → `UWP`; Windows → `WINDOWS`
- Database checks are supported on all platforms — include every platform from INIT.

## Tagging — important

- Platform tags matching the test's supported platforms.
- SDK tags (`APPSFLYER_INIT` / `APPSFLYER_CHECK`, `SENTRY`, `ADJUST`, `AMPLITUDE`, `PURCHASE`).
- Test-type tags when the case has them (`SMOKE`, `REGRESSION`, ...).

---

## AppsFlyer — critical

- Base part tagged `APPSFLYER_INIT`; database check tagged `APPSFLYER_CHECK`.
- Decide on the database check **before** writing:
  1. custom events (`example_event`, `event_purchase`, ...) → active check;
  2. `track_session()` or init methods → look at similar tests in the same directory:
     they have a check → active check; they do not → commented check;
  3. pure config/settings test → no check;
  4. the case describes no verification → no check.
- Commented check (when uncertain): write the whole function as commented Python, prefix
  every line with `#`, and add a note saying which tests you compared, why it is uncertain,
  and what it would verify. Do not validate commented code.

## AppsFlyer — important

- Split into two functions: `APPSFLYER_INIT` (execution) and `APPSFLYER_CHECK` (verification).
- Use `@parametrize_devices` for `APPSFLYER_CHECK` with the `device=None` attribute.
- Verify every event from INIT exists in the database with the right schema.
- `example_event` produces three events: `EXAMPLE_EVENT_SCHEMA`,
  `EXAMPLE_EVENT_EXTENDED_SCHEMA`, `EXAMPLE_EVENT_STORE_SCHEMA`.

## Sentry

Tag all Sentry tests with `SENTRY`.

---

## In-app purchase — critical

- Directory `tests/tests_in_app_purchase/`, one file per test (`tests/test_in_app_purchase/` is an
  empty leftover — do not add files there).
- A file may define a non-test `def common_part(step):` holding the steps shared across
  platforms.
- Each platform gets its own `def test_XXX_<platform>(step):` tagged only for that platform.
- **No `if PLATFORM_TO_RUN ==` guards** — platform separation is done entirely by separate
  tagged functions.
- Platform-specific dialog interaction goes through `step.device.*`; dialog classes live in
  device steps, never in tests.
- Tag with platform tags, the `PURCHASE` tag, and test-type tags.

> `Tag.PURCHASE = "purchase"` exists in `tags.py` (the old `test.mdc` said it didn't).
> Always verify tags against the enum.

## In-app purchase — important

Available UI dialog classes per platform:

- **MAC**: `MacPurchaseDialog(app_name)` — `click_buy()`, `click_cancel()`, `is_dialog_present`;
  `MacPurchaseSuccessDialog()` — `click_ok()`
- **UWP**: `UWPPurchaseDialog1(app_name)` — `click_buy()`, `is_dialog_present`;
  `UWPPurchaseDialog2(app_name)`, `UWPPaymentMethodDialog(app_name)`
- **Windows / iOS / Android**: no purchase dialog automation available

Dialog usage rule: wrap every dialog interaction in a `@step_decorator` method added to
`framework/test_management/test_steps/device/device_steps.py`, carrying the right platform
decorator. Tests call only `step.device.<method>()` and never import a dialog class.

```python
# device_steps.py — new step wrapping the dialog
@step_decorator
@mac_only_step
def purchase_dialog_click_buy(self) -> None:
    MacPurchaseDialog(app_name=config.app_name).click_buy()


# test file
def common_part(step):
    step.purchase.set_market_can_buy(can_buy=True)
    step.purchase.buy_product_ui(product_id="product_1")


@tag(Tag.MAC, Tag.PURCHASE, Tag.SMOKE)
def test_XXX_simple_purchase_mac(step):
    step.device.purchase_dialog_click_buy()
    common_part(step=step)
    step.device.purchase_success_dialog_click_ok()


@tag(Tag.UWP, Tag.PURCHASE, Tag.SMOKE)
def test_XXX_simple_purchase_uwp(step):
    step.device.purchase_dialog_click_buy()
    common_part(step=step)
```

---

## Waits, timeouts and flakiness

- Prefer the project's existing waits and helpers.
- Wait on observable state, not on time: visible, enabled, clickable, gone, text updated,
  screen ready, loader disappeared.
- A custom timeout is acceptable only for a known asynchronous event — animation, lazy load,
  scene transition, network-backed refresh — and must carry a comment saying what is awaited
  and how that was confirmed.
- Never raise a timeout "just in case" or after a single failure with no established cause.
- `sleep` is a temporary stabiliser only: short, commented with its reason, and only when no
  suitable explicit wait exists.
- A long `sleep` or a noticeably raised timeout means the cause is not yet understood —
  record it as a risk or a blocker instead of shipping it.
- Forbidden as stabilisers: broad `except`, silent action repeats, "loop until it works",
  random fallback paths.

## Branching

An `if` is allowed in exactly three cases:

1. the branch follows explicitly from the case text;
2. the branch reflects real product state confirmed by code or UI reconnaissance;
3. it is a technical guard for environment/setup that does not change the scenario.

An `if` is forbidden when it hides instability or a race, adapts to unknown UI state, skips
an assertion or a mandatory step, or implements a fallback instead of fixing the locator or
action. Every non-obvious `if` carries a short comment explaining why.

## Assertions

- Assertions check the case's expected result, not the mere absence of a crash.
- Do not substitute an indirect signal when a direct check is available.
- Do not weaken an assertion for stability without recording the deviation explicitly.
- One expected result may need several assertions; that is fine when it improves verifiability.

## Signs of a product defect

Do not treat a failure as flakiness when any of these holds:

- an element never appears although the product logic says it should;
- a control stays disabled because of the app's functional state;
- data does not load or is displayed inconsistently;
- the UI shows a state that contradicts the case;
- the behaviour reproduces deterministically.

In that case: do not weaken the test, do not substitute a softer check, record the risk or
blocker, and limit yourself to improving diagnosability and correctness of waits.
