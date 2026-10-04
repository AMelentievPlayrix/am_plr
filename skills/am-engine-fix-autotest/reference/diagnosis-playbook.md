# Diagnosis playbook for broken VSO engine autotests

Method, evidence rules and the traps that have actually cost time on this project.

---

## Evidence levels

Label every non-trivial conclusion:

- **VERIFIED** — confirmed by code, by a log line, by a passing/failing run, or by the
  Qase case text.
- **INFERRED** — follows logically from several verified facts, but is not directly confirmed.
- **UNKNOWN** — insufficient data, a gap, or a contradiction.

Only **VERIFIED** conclusions may drive a code change. **INFERRED** ones belong in the report
as hypotheses. **UNKNOWN** becomes an open question or a blocker — never something a `sleep`,
a raised timeout or a fallback branch papers over.

Never present an inference as a fact. Phrases like "probably", "usually" and "looks like" in
a root-cause statement mean the investigation is not finished.

---

## Root-cause order

When the cause is not obvious, work through these in order. Stop at the first that explains
the **entire** observed symptom, not just part of it.

1. **Waiting and synchronisation** — the step ran before the state it needs existed.
2. **Element readiness** — present but not visible, enabled, or interactable; covered; mid-animation.
3. **Locator / identifier stability** — the id is not what the test assumes. See "Instance
   counters" below.
4. **Transient UI states** — loader, animation, popup, re-render between find and act.
5. **Test isolation** — leftover state from a previous test in the same session.
6. **Test data and preconditions** — the account, product, device or backend state differs.
7. **Parallelism and resource conflict** — two runs contending for one device or one account.
8. **External dependencies** — relay server, BrowserStack, store, SDK backend, certificates.
9. **Product defect** — the app is genuinely wrong.

---

## Local green is not proof

A local single-test run and a CI run differ in ways that hide bugs:

- **Session-scoped counters and indices** start at zero locally and do not on CI.
- **Test ordering** — leftover state only exists when other tests ran first.
- **Device** — BrowserStack hardware, OS version and locale differ from the local host.
- **Timing** — CI machines are slower and more contended.

So: a green local run after a fix proves **absence of a regression**, not that the fix works.
Say exactly that in the report rather than implying a stronger result.

### Worked example — instance counters (real, VSO-9585)

A test failed on CI with an element-not-found timeout. The framework's diagnostic printed the
ids it did find:

```
Cannot find element "...###/curveType/curve/SmoothSetter/ICSEditor_0_ICSPropertiesWidget" in time.
Possible similar ui_id(s) are: ['...###/curveType/curve/SmoothSetter/ICSEditor_2_ICSPropertiesWidget']
```

That single line eliminated two hypotheses at once — the panel *was* rendered and the node
*was* selected. Only one id segment differed. `ICSEditor_<N>` turned out to be an **instance
index** counting editors opened during the session: always `0` in a single-test local run,
`2` in a 965-test CI run. Every hardcoded `_0` locator missed.

Two transferable lessons:

- When a "not found" error also reports similar ids, that list is usually the whole answer.
  Read it before forming any other hypothesis.
- A constant embedded in an identifier may be a counter. Check what increments it and under
  which conditions it is non-zero.

---

## Reading failure artifacts

- Prefer the CI artifact bundle or ReportPortal entry for the specific failing run.
- Read the step log, not just the pytest traceback — the traceback shows where it gave up,
  the step log shows what the app was doing.
- Element dumps and screenshots taken at failure time show the real state; compare them
  against what the test assumed.
- BrowserStack sessions carry a video and a device log for iOS/Android failures.
- Note the build, the branch and the date of the failing run. A failure from a month-old
  build against a since-changed app tells you little.

---

## Test problem or product defect?

Treat it as a **product defect** — and do not weaken the test — when:

- an element never appears although the product logic says it should;
- a control stays disabled because of the app's functional state;
- data does not load, or is displayed inconsistently;
- the UI contradicts the Qase case;
- the behaviour reproduces deterministically, with no sign of a race.

Then: record the defect, keep the test honest, and limit changes to better diagnosability and
correct waits. Report it to the user; do not file a product task without their go-ahead.

Treat it as a **test problem** when the app behaves per the case and the test's assumption,
timing, locator, isolation or data is what is wrong.

---

## Forbidden fixes

Each of these makes the failure invisible instead of solved:

| Anti-fix | Why it is wrong |
|---|---|
| Raising a timeout with no established cause | Converts a real failure into a slow one |
| Adding `sleep` to "let it settle" | Hides a race; breaks again on a slower machine |
| Adding retries or a `while` until it passes | Hides non-determinism |
| Broadening an `except` | Swallows the actual signal |
| Weakening or removing an assertion | Silently reduces what the test guarantees |
| A fallback `if` for an unconfirmed UI state | Two code paths, neither verified |
| A broad or fuzzy locator | Matches the wrong element eventually |
| `skip` / `xfail` as the fix | Removes coverage without deciding anything |

A `sleep` is acceptable only as an explicitly temporary stabiliser: short, commented with its
reason, recorded as a residual risk, and only when no explicit wait exists.

---

## Stop conditions

Stop before the run budget is spent when:

- the same failure repeats and you have no new root-cause hypothesis;
- the failure is infrastructure — relay server, BrowserStack, certificates, device allocation;
- a required step or element does not exist and cannot be confirmed;
- the case itself is contradictory and needs a requirements decision;
- the remaining change would stop being local and become a refactor;
- the evidence points at a product defect.

Then produce the halt report from [delivery.md](../../am-engine-create-autotest/reference/delivery.md) and ask the user how to proceed.

---

## Before calling it fixed

- The root cause is stated in one sentence and is **VERIFIED**.
- The change addresses that cause, not the symptom.
- The test still verifies what the Qase case requires — compare against the case.
- No forbidden fix from the table above is present.
- You can say what the green run does and does not prove.
- Latent copies of the same bug elsewhere in the repo are searched for and reported:

  ```bash
  git grep -n '<the hardcoded pattern you just fixed>'
  ```

  Report them; fix them in the same PR only when they are the same defect and the user agrees.
