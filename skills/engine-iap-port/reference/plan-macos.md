Your goal is to analyse an existing iOS in-app purchase test and produce a concrete plan for adding a macOS variant. You do **not** write or edit any files. Pseudo-code is allowed in the plan for clarity.

## Important — platform-split is intentional

iOS and macOS tests live as **two separate `test_{id}_*_ios` / `test_{id}_*_mac` functions in the same file**, even when QASE describes a single scenario. Each platform may legitimately behave differently (UI, StoreKit, sandbox, engine response timing) — the split lets each test follow the actual platform behaviour rather than papering over it with `if PLATFORM_TO_RUN` guards or "tolerant" assertions. Divergence is acceptable; document it inline (`# TODO`, comment, or a Known-patterns note) when it appears.

## Befor you start
If you are not in Plan mode switch to Plan mode

## Intake steps

1. Extract the test ID from the user message (e.g. "10559" from "add mac test for 10559").
2. Find `tests/tests_in_app_purchase/test_{id}_*.py` and read it fully. If file not found STOP here and describe it in chat.
3. Read the case with `mcp__qase__get_test_case_data(project_code="VSO", test_case_id={id})`
   (see [mcp-tools.md](../../engine-create-autotest/reference/mcp-tools.md)).
4. Inspect the QASE steps for any platform-prefixed entries (e.g. `iOS:`, `macOS:`); note every difference between iOS and macOS.
5. Map each `step.system_ui.ios.*` call in the test file to its macOS equivalent using the table below.
6. Mark iOS-only intermediate steps (sandbox sign-in, already-purchased dialog) as dropped — they have no macOS counterpart.
7. Decide whether any new `step.system_ui.mac.*` method is required beyond what is listed in **Available macOS steps**.
8. If everything is clear reply only with "Creating plan" in the chat.
9. Produce the plan using the output spec below.

## iOS → macOS step mapping

| iOS step | macOS step |
|---|---|
| `ios.authenticate_appstore()` | `mac.authenticate_appstore()` |
| `ios.confirm_sandbox_purchase()` | `mac.confirm_purchase(confirm=True)` |
| `ios.authenticate_sandbox_purchase()` | *drop — not required on macOS* |
| `ios.close_already_purchased_dialog()` | *drop — no macOS equivalent* |
| `ios.close_purchase_success_dialog()` | `mac.close_success_purchase_dialog(with_ok_button=True)` |
| `ios.close_app_store_auth_dialog()` | `mac.authenticate_appstore()` → `mac.dismiss_purchase_dialog_if_present()` — on macOS the sign-in dialog appears **before** the purchase dialog, so auth must precede the dismiss |

## Available macOS steps

These methods already exist in `framework/test_management/test_steps/system_ui/mac_system_ui_steps.py`:

- `mac.authenticate_appstore() -> None` — handles App Store sign-in dialog if it appears; skips if already authenticated
- `mac.confirm_purchase(confirm: bool) -> None` — clicks Buy (`confirm=True`) or Cancel (`confirm=False`) on the purchase dialog; raises if dialog does not appear
- `mac.dismiss_purchase_dialog_if_present() -> None` — cancels the purchase dialog only if it appears; silently skips if absent. **Always call `authenticate_appstore()` first** — on macOS the App Store sign-in dialog appears before the purchase dialog, so without auth the purchase dialog never shows and the dismiss is a silent no-op
- `mac.confirm_purchase(confirm: bool) -> None` — clicks Buy / Cancel on the purchase dialog. Does **not** wait for the sheet to disappear: the dialog detection AppleScript calls `set frontmost to true` on Engine-Example every poll, which actively keeps the parent app frontmost and blocks the `storeuid` window from taking over after Buy is clicked. The next step (`close_success_purchase_dialog` for happy path, `dismiss_purchase_dialog_if_present` for cancel paths) waits on its own dialog appear/disappear signal, which is deterministic.
- `mac.close_success_purchase_dialog(with_ok_button: bool = True, break_mode: BreakMode | None = None) -> None` — closes the success dialog via OK button. Pass `break_mode` when the purchase is expected to fail (crash) in the app — either the OK click itself fires the failure (`CONSUMPTION`) or an earlier break mode crashes the engine around the same window (`AFTER_BUY` / `VALIDATION_CHECK` / `VALIDATION_REMOVE`). With `break_mode` set, the step waits for the relay disconnect **and** the engine OS process termination, then drops the cached relay socket so the test's next `step.device.activate_app()` reconnects to a fresh process. Mirrors the iOS `close_purchase_success_dialog(break_mode=...)` pattern.

## Available macOS device steps

The context manager in `framework/test_management/test_steps/device/device_steps.py`:

- `device.mac_clock_shifted(target_date: date) -> ContextManager` — shift the local macOS system clock to `target_date` for the duration of the `with` block, then re-enable NTP on exit. Requires `MAC_SUDO_PASSWORD` in `.env` (see `.env_example`). Three-layer safety net: (1) `try:/finally:` inside the context manager, (2) self-healing inside `MacActions.set_custom_date` if `setdate` fails after NTP was already disabled, (3) per-test autouse fixture `_ensure_mac_ntp_enabled` that queries live `systemsetup -getusingnetworktime` before every test and re-enables NTP if off — covers SIGKILL/reboot/prior-test restoration failure. Always use the context manager — do not call the underlying `_set_mac_custom_date` / `_restore_mac_system_date` directly.

If the planned test needs a macOS interaction not covered by the above, include a new method proposal in the plan.

## Plan output spec

The plan must contain all of the following (no full code — pseudo-code permitted for clarity):

1. **QASE summary** — title, type, importance, and any iOS vs macOS step differences found in step 4.
2. **Function signature and decorator**:
   - `@tag(Tag.PURCHASE, Tag.MAC, Tag.<TYPE>)`
   - `def test_{id}_*_mac(step: StepManager)`
3. **Ordered step list** — each `step.*` call with a one-line description (pseudo-code style is fine).
4. **New mac steps needed** (if any) — name, signature, and brief behaviour description for each.
5. Any other new code need to be added.
6. **`inapp_purchase.mdc` update** — state whether a new known-pattern entry should be added for this test.

## Coding constraints (apply to anything proposed in the plan)

- No `if PLATFORM_TO_RUN` guards — platform separation is via tagged functions only.
- No `assert` statements — verifications only via `step.check.*` or `step.purchase.*`.
- Tags must come from `framework/test_management/enums/common/tags.py` only.
- Black 120-char lines, double quotes, 4-space indent; `X | None` union syntax; type hints on all params and returns except test function return and `self`; named arguments where clarity improves.
- One `def test_{id}_*_mac(step)` per file; `step` fixture only (no `data` unless the test is parametrised).
- Dialog interactions only via `step.system_ui.mac.*` — never import dialog classes in test files.

## macOS offline RequestProducts (test_10511) — known flakiness

When porting an offline-`RequestProducts` test to macOS, **follow the QASE specification** even where it diverges from the iOS test code. Do **not** skip checks: the framework's API surface may not 1:1 match every QASE bullet (e.g. UI/widget text isn't readable from tests today), but the assertions we *can* make should match QASE — never the iOS test's accidental behaviour.

### Mechanism (verified with mitmproxy logs and per-call polling — test_10511 investigation)

1. `storekitd` (Apple's system daemon that owns `SKProductsRequest`) sends product lookups to `sandbox.itunes.apple.com:443`.
2. When the test toggles Wi-Fi off via `networksetup -setairportpower en0 off`, `storekitd` does **not** fail the in-flight request. It queues the task in the system networking stack.
3. When the test re-enables Wi-Fi, `storekitd` typically completes the queued request and calls the app's `productsRequest:didReceiveResponse:` delegate with invalid/empty product entries (the sandbox doesn't have products loaded for a clean install).
4. The app sets `request_products_result = "Success"` (`PurchaseResult.SUCCESS`) — request callback fired, just with no usable products. **This matches QASE-10511 step 2** ("Products request: Success(1)" / log "`OnRequestProductsFinished: Success Products: ... invalid ...`").

`PurchaseResult.SUCCESS = "Success"` means "the callback fired"; `PurchaseResult.EMPTY = ""` means "no callback has fired yet" (initial value).

### Why iOS asserts `EMPTY` but macOS must assert `SUCCESS`

iOS+BrowserStack uses `NO_NETWORK`, which flips device-level reachability so aggressively that `SKProductsRequest` never fires its callback. The iOS variant of test_10511 ends up at the initial `""`, so `check_request_products_result(EMPTY)` happens to pass. macOS local only kills Wi-Fi; `storekitd` keeps the system-level networking task alive and the callback fires, so macOS must assert `SUCCESS` to follow QASE.

### Known flakiness on macOS

`storekitd` is **not** strictly deterministic about firing the queued callback. In our investigation we observed both `SUCCESS` (callback fired during/after the offline window — the QASE-aligned outcome) and `EMPTY` (callback never fired — same outcome iOS produces). The test_10511 macOS variant is therefore expected to flake at the offline assertion; rerun if it fails there. Do **not**:

- replace the assertion with a tolerant `result in {SUCCESS, EMPTY}` helper — that hides regressions like `MarketError`.
- skip the assertion to make the test green — we want to follow QASE, even at the cost of occasional retries.
- add settle delays / app-restart tricks / proxy-bypass toggles to mask the flake — empirically none of them are reliable, and they only push the test further away from QASE.

The proper fix is **app-side**: attach a wall-clock timeout to `SKProductsRequest` or use `NWPathMonitor` to short-circuit when no path is available. Either makes `request_products_result` settle deterministically. File a ticket and reference this section.

### When the iOS pattern is fine on macOS

- Tests that already expect `PurchaseResult.SUCCESS` after offline (e.g. test_10512 with a populated cache) — `storekitd`'s system-level completion matches the assertion.
- Tests that disable network for a non-StoreKit reason (e.g. `MarketError` on `RequestBuyProduct` like test_6695) — `RequestBuyProduct` failure paths are app-controlled, not delegated to `storekitd`, so the existing offline window is sufficient.

### common_part parameter convention

- **No default values** unless `None` is a meaningful sentinel (i.e. the parameter is genuinely optional for some callers).
- When `None` is used as a default, add a guard inside `common_part` that raises `ValueError` if the parameter is `None` but is required by the current combination of flags. Example:

```python
def common_part(step, buy_while_offline: bool, expected_offline_buy_result: PurchaseResult | None = None):
    if buy_while_offline and expected_offline_buy_result is None:
        raise ValueError("expected_offline_buy_result must be provided when buy_while_offline=True")
```

- Callers that do not trigger the flag simply omit the optional argument; callers that do trigger it must pass an explicit value.

### Pattern for porting

`common_part` takes a required `expected_offline_result` argument so iOS and macOS share the offline → online → buy flow but each test states its own assertion explicitly:

```python
def common_part(step, expected_offline_result: PurchaseResult):
    ...
    step.purchase.check_request_products_result(expected=expected_offline_result)
    ...

# iOS (BrowserStack NO_NETWORK suppresses callback — does NOT match QASE, see comment in test)
common_part(step=step, expected_offline_result=PurchaseResult.EMPTY)

# macOS (storekitd completes callback with invalid products — matches QASE-10511)
common_part(step=step, expected_offline_result=PurchaseResult.SUCCESS)
```

## How `BreakMode` works

`BreakMode` (`framework/test_management/enums/purchase/break_mode.py`) is an `IntEnum` whose values map 1:1 to `EngineTests::PurchaseManager::BreakMode` in the native IAP autotest hook. It tells the engine **at which stage of the purchase pipeline to deliberately stop or crash**, so tests can exercise recovery paths.

### Stages (in pipeline order)

| Value | Member | Effect |
|---|---|---|
| 0 | `NONE` | Hook disabled — normal purchase flow |
| 1 | `BEFORE_BUY` | Crash on `RequestBuyProduct`, **before** StoreKit dialog appears |
| 2 | `AFTER_BUY` | Crash after StoreKit confirms but before validation |
| 3 | `VALIDATION_CHECK` | Crash during server-side receipt validation |
| 4 | `VALIDATION_REMOVE` | Crash while removing the validated purchase from the queue |
| 5 | `ACKNOWLEDGE` | Crash on acknowledgment (post-validation, pre-consumption). On macOS may not crash — see test_10553 TODO |
| 6 | `CONSUMPTION` | Crash on consumption (the final stage, fires when the user clicks OK on the success dialog) |

### How to use it in a test

1. **Set the break mode** before triggering the purchase: `step.app.purchase.set_break_mode(break_mode=BreakMode.X)` — this is wired to the engine via `SetBreakMode` JRPC.
2. **Trigger the purchase** as usual: `step.app.purchase.request_buy_product(...)`.
3. **Reach the configured stage** — for `BEFORE_BUY` this happens immediately on `request_buy_product`; for `CONSUMPTION` it happens on `close_purchase_success_dialog` (clicking OK fires consumption).
4. **Hand the break mode to the UI step that triggers the crash**, so it can do post-crash cleanup. Today only `close_purchase_success_dialog(break_mode=...)` (iOS and macOS) needs this — when `break_mode is not None` the step waits 2 s then drops the stale relay websocket so the next reconnect after `activate_app()` is clean.
5. **Reactivate and verify** via `step.device.activate_app()` followed by the usual `request_products` / `check_money` / `check_product_purchase_payload_result` calls.

### Why the UI step owns the cleanup

The crash is **causally tied to the action the UI step performs** (clicking OK fires consumption → app crashes). The break mode is the step's precondition declaration: "this click will trigger a crash, handle it." The framework's relay layer cannot know which action caused the disconnect, so localising the recovery to the cause-point keeps the test linear and the framework simple.

### macOS crash-recovery: relay-disconnect ≠ process-death

**Problem.** On macOS the relay websocket closes ~5–10 s before the OS actually reaps the crashed engine process. A naïve recovery that only waited for the relay disconnect, dropped the cached socket, and returned would leave the OS still considering the process alive — making the test's next `step.device.activate_app()` (= `open -a`) a no-op and any follow-up JRPC request hang against the dead engine over a fresh socket. Symptom was `TimeoutError: Failed to get request products result within timeout=15s` right after the "restart".

**Solution.** Empirically on macOS the break-mode "crash" does **not** terminate the Engine-Example process. Both `pgrep -x Engine-Example` and `application id "…" is running` keep reporting it alive indefinitely; the visible effect is macOS's `Problem Reporter` crash dialog appearing on top of a halted-but-alive engine. `mac.close_success_purchase_dialog(break_mode=...)` therefore:

1. Polls for `Problem Reporter` to appear within `_ENGINE_CRASH_TIMEOUT = 120s` — the actual macOS crash signal.
2. Closes it via its OK button (mirrors the user closing the dialog; falls back to `pkill "Problem Reporter"` if the click fails).
3. **Reaps the Engine-Example zombie** with `pkill -x Engine-Example`. macOS does not clean up the halted process on its own and leaving it alive blocks the test's next `step.device.activate_app()` with Launch Services -609 ("the application could not be launched"). This step is mandatory: we never leave a zombie behind. QASE does not describe Problem Reporter handling because it's a macOS runtime artifact; the zombie cleanup is test infrastructure required to translate the macOS crash UX into the same clean-restart state iOS gets for free.
4. Sleeps `_LAUNCH_SERVICES_SETTLE = 3s` for Launch Services to release the previous app slot, then closes + drops the cached relay socket so the test's next `open -a` reconnects to a freshly launched process.

**If `Problem Reporter` never appears within the timeout the step raises ``TimeoutError``.** Setting a break mode declares "this purchase must crash the engine" — a missing crash is a product bug (e.g. the macOS engine doesn't actually crash on the configured stage, like the known `test_10553 ACKNOWLEDGE` case), and the test should fail loudly with that root cause rather than cascade into Launch Services -609 / `Money mismatch` errors downstream. Test infrastructure does not paper over missing crashes.

A second macOS-specific quirk shows up in `mac.confirm_purchase`: the purchase dialog detection AppleScript calls `set frontmost to true` on Engine-Example every poll, which actively keeps the parent app frontmost and blocks the `storeuid` window from taking over after Buy is clicked. For break-mode crash tests this makes `wait_for_dialog_disappears` fail (or worse, cascade into the next variant by holding focus). `confirm_purchase` therefore does **not** call `wait_for_dialog_disappears` at all — the next step's `wait_for_dialog_appears` (success window on `storeuid`, or the next purchase sheet) is the deterministic next signal.

### Parametrising over break modes

When QASE lists multiple break modes for the same scenario (e.g. test_10553 lists Acknowledge and Consumption), expose them as a module-level `BREAK_MODE_LIST` and `@pytest.mark.parametrize` the test function — see `test_5826_10551_10552_purchase_with_crashes.py` and `test_10553_purchase_with_crash_consumption.py` for the canonical pattern. Pass the parametrised `break_mode` to both `set_break_mode(...)` and `close_purchase_success_dialog(break_mode=...)`.

## Reference example — test_5822

```python
@tag(Tag.PURCHASE, Tag.MAC, Tag.SMOKE)
def test_5822_purchase_mac(step: StepManager):
    common_part(step=step)                                    # request_products + request_buy_product
    step.system_ui.mac.authenticate_appstore()               # handle App Store sign-in if it appears
    step.system_ui.mac.confirm_purchase(confirm=True)        # click Buy on purchase dialog
    step.system_ui.mac.close_success_purchase_dialog(with_ok_button=True)  # close success dialog
    common_part_verify_purchase(step=step)                   # check money and payload result
```

## Known patterns

- **test_5822** — basic purchase: `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog`
- **test_5824** — canceled purchase: `authenticate_appstore` → `confirm_purchase(False)` (no success dialog)
- **test_6693** — purchase interrupted by app restart while transaction widget is shown: `common_part` (buy + restart) → `dismiss_purchase_dialog_if_present` (optional lingering dialog) → `common_part_after_restart` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog`
- **test_6695** — network loss before transaction widget: `common_part` (buy without internet → MarketError, restore network, retry buy) → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog`
- **test_7304** — purchase interrupted by minimizing app after success dialog: `common_part` (buy) → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog` → `background_app_for_duration(10s)` + verify money/payload
- **test_10511** — request products offline with empty cache. Both platforms share `common_part(step, expected_offline_result)` and verify the post-reconnect online `request_products → SUCCESS`, buy → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog`. iOS asserts `EMPTY` (BrowserStack `NO_NETWORK` suppresses the callback); macOS asserts `SUCCESS` per QASE-10511 (`storekitd` fires the callback with invalid products). See "macOS offline RequestProducts (test_10511) — known flakiness" below.
- **test_10547** — purchase two different products sequentially: `common_part(PRODUCT_1)` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase(SUCCESS, amount=0, money=10, PRODUCT_1)` → `common_part(PRODUCT_2)` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase(SUCCESS, amount=10, money=20, PRODUCT_2)`. `authenticate_appstore` called only before the first purchase.
- **test_10548** — three consecutive purchases of the same product: `common_part` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase(money=10, amount=0)` → (`common_part` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase`) × 2. `authenticate_appstore` called only before the first purchase.
- **test_10549** — purchase after canceled: `common_part` → `authenticate_appstore` → `dismiss_purchase_dialog_if_present` (cancel first attempt) → `common_part_verify_canceled_purchase` → `common_part` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase`. `authenticate_appstore` called before both attempts — the sign-in dialog appears before the purchase dialog on macOS, so auth must precede dismiss. Second call is a no-op if already authenticated.
- **test_10553** — purchase with crash at Acknowledge/Consumption: `common_part` (request_products → set_break_mode(CONSUMPTION) → request_buy_product) → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True, break_mode=BreakMode.CONSUMPTION)` (clicking OK fires consumption → app crashes; the step itself sleeps and drops the stale relay connection) → `common_part_verify_purchase` (activate_app + request_products + verify money=10, payload EMPTY/amount=0).
- **test_10550** — purchase with crash at BEFORE_BUY: `common_part` (request_products → set_break_mode(BEFORE_BUY) → request_buy_product → crash) → `common_part_restart_app_after_crash` (activate_app → request_products → check EMPTY) → `common_part_verify_purchase`. No system UI steps — crash fires before StoreKit dialog appears.
- **test_10512** — request products offline with populated cache. `common_part` takes `buy_while_offline: bool` and `expected_offline_buy_result: PurchaseResult` (no defaults). macOS passes `True` / `EMPTY`: offline buy inside the same offline window as RP returns `EMPTY` because the engine's `CanPurchase` state is not settled after the offline RP (unlike test_6695 where RP was done online first). QASE step 3 expects `MarketError` — divergence noted; same pattern as test_10511 offline RP mismatch. iOS passes `False` / `EMPTY` (BrowserStack behaviour for offline buy not yet verified — see TODO in test). macOS variant: `common_part(buy_while_offline=True, expected_offline_buy_result=EMPTY)` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase`.
- **test_10555** — purchase interrupted by app termination after confirming purchase, during transaction processing: `common_part` (request_products + buy) → `authenticate_appstore` → `confirm_purchase(True)` → `restart_app` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_after_restart` (request_products → SUCCESS) → `common_part_verify_purchase` (money=10, payload SUCCESS, amount=0). Distinct from test_6693 (which restarts **before** `confirm_purchase`, while the transaction widget is shown).
- **test_10558** — purchase interrupted by network loss while purchase dialog is up: `common_part` (buy) → `authenticate_appstore` → `set_network_connection(disable)` + `simulate_delay(2s)` + `set_network_connection(enable)` → `common_part_check_failed_purchase` (money=0, payload EMPTY/0) → `dismiss_purchase_dialog_if_present` (clear lingering dialog from first attempt) → `common_part` (retry buy) → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase`. Distinct from test_10559 (network drop **after** the success dialog is closed) and test_6695 (network already off **before** `request_buy_product` so the buy fails with `MARKET_ERROR`).
- **test_10559 (during_transaction_completion variant)** — network loss while StoreKit is processing the purchase: `authenticate_appstore` → `confirm_purchase(True)` → `simulate_delay(2s)` (wait for `MacPurchaseSuccessDialog` to appear; storeuid has no windows for the first ~2s after Buy click) → `common_part_set_network_connection` (disable/2s/enable) → `simulate_delay(5s)` (let storeuid recover) → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase`. **macOS divergence from QASE/iOS**: QASE-10559 step 3 ("Под самый конец покупки") expects the drop to interrupt in-flight transaction completion. On macOS the success dialog only materialises after StoreKit has finished server-side approval, so the disable/2s/enable window lands after the transaction is effectively done and does not exercise any recovery path (the engine's consumption callback fires only on OK click, after restore). Cutting earlier aborts the transaction entirely and the success dialog never appears. The assertions (`money=10`, payload SUCCESS/0) still pass. Marked with an in-code `# TODO: validate with QA`.
- **test_10559 (on_completion variant)** — network loss **after** success dialog is closed: `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_loss_network` (disable/2s/enable) → `common_part_verify_purchase`. Marked with an in-code `# TODO: validate if this test should also exist` — the network drop fires after consumption has already been recorded (`money=10`/payload SUCCESS), so it does not exercise any recovery path and does not match QASE-10559 ("Под самый конец покупки"). Likely a legacy duplicate of the `_during_transaction_completion` variant; ported for parity pending QA confirmation. **QASE/iOS divergence**: QASE-10559 describes the "during transaction" flow only; the `_on_completion` file is an extra iOS variant that was preserved on macOS for parity.
- **test_11737** — purchase with system date shifted to the future: `with mac_clock_shifted(today + 3d):` → `common_part` → `authenticate_appstore` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase(money=10, amount=0)` → `common_part` → `confirm_purchase(True)` → `close_success_purchase_dialog(with_ok_button=True)` → `common_part_verify_purchase(money=20, amount=10)`. NTP is restored by the context manager's `finally:`; per-test autouse fixture `_ensure_mac_ntp_enabled` catches any stale state before the next test. **QASE divergence carried from iOS**: QASE-11737 steps 4 (`DuplicateTransaction`) and 5 (restore date + restart) are not implemented — the macOS port mirrors the iOS test, not QASE. Marked with in-code `# TODO`. Requires `MAC_SUDO_PASSWORD` in `.env`.
- **test_11738** — Amplitude tracking of MarketError purchase: shared `common_part` (request_products → buy offline → restore network → request_products) with no system UI steps because the offline buy never reaches StoreKit's dialog. After the buy: `marketing_tracker.send_cached(tracker=amplitude_marketing_tracker, wait_for_event=True)` (waits until the Amplitude batch is captured by the local mitmproxy — required on macOS where the SDK takes >1s after `send_cached` to actually POST and the default 1s `log_collection_delay` is too short), then `step.common.check_substring_entries_in_network_logs` with `PurchaseResult.MARKET_ERROR` / `StoreKitPaymentDiagnostic.NS_URL_ERROR_OFFLINE` (= `"NSURLErrorDomain:-1009"`, NOT iOS's `SKErrorUnknown`) / `PLATFORM_PRODUCT_IDS[Platform.MAC][PRODUCT_1]`. The Amplitude SDK self-deletes its on-disk `*.events` cache after a successful flush, so no per-test storage cleanup is needed once `wait_for_event=True` keeps the flush deterministic — leftover `.events` files only accumulate when a previous test exits before the SDK finishes its flush, which is exactly what `wait_for_event=True` prevents.
- **test_11739** — Amplitude tracking of Canceled purchase: enable Amplitude tracker + set user → `common_part` (request_products + request_buy_product) → `authenticate_appstore` → `dismiss_purchase_dialog_if_present` (cancels the purchase dialog — this is the action that fires the Canceled event) → `check_product_purchase_payload_result(CANCELED, amount=0)` → `marketing_tracker.send_cached(tracker=amplitude_marketing_tracker, wait_for_event=True)` → `check_substring_entries_in_network_logs` with `PurchaseResult.CANCELED` / `StoreKitPaymentDiagnostic.PAYMENT_CANCELLED` (= `"SKErrorPaymentCancelled"`, same value as iOS) / `PLATFORM_PRODUCT_IDS[Platform.MAC][PRODUCT_1]`. Sister test to test_11738 (MarketError variant); shares the same Amplitude wiring but uses the `test_10549` cancel UI pattern instead of the offline buy.
