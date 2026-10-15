# Browser Test Routing

## Purpose

A browser-test request is one user outcome. The parent chooses the smallest
execution path that can prove the requested claim, operates that surface, and
retains durable evidence only when the claim, a repository gate, an audit, or a
handoff requires it. Users should not need to choose a recorder skill or
translate the request into bookkeeping commands.

## Route By Claim

| Claim | Execution path | Evidence boundary |
| --- | --- | --- |
| HTTP availability, headers, status, or static response body | HTTP client or `web-evidence` | Supports only the captured HTTP response. |
| Rendered page state, navigation, or visual acceptance that can be exercised in an available browser | Browser operator | Use ordinary assertions/output; initialize `browser-session` before operation only when the claim or owning gate requires a durable record. |
| Repeatable DOM interaction, selectors, network waits, or regression coverage | Project Playwright/browser test harness | Retain test output and, when useful, link screenshots/traces from the parent browser session. |
| Native macOS UI, browser chrome, cross-application behavior, permission dialogs, or accessibility-tree interaction | macOS desktop Computer Use outcome | Use the desktop safety/AX workflow and retain screenshot or recording evidence; do not describe this as a browser-only test. |
| Small local command that proves a service/test path | `canary-check` | Supports the command result only; it is not rendered-browser evidence. |

Static HTTP success must not be reported as proof that JavaScript rendered, a
visual assertion passed, or a desktop interaction occurred. Source inspection
alone is not browser execution.

Routing is reciprocal. The `computer-use.macos-desktop` route
hands DOM-level, selector, and rendered-page claims back here
rather than driving a browser through the accessibility tree, which is
unreliable for Chromium-family content. This route owns signed-in session state
and its own artifact directory; the desktop route owns native window chrome,
cross-application behavior, permission dialogs, and AX interaction. A desktop
screenshot of a browser window is never proof of rendered DOM state.

## Parent Workflow

1. Read this document.
2. State the target, acceptance claim, available execution environment, and
   chosen route.
3. Use ordinary test output for a routine claim. Before launching a browser
   surface that can emit files, allocate one parent-owned artifact directory
   outside the repository. When using Playwright MCP, configure it with
   `--output-dir <artifact-directory>`. Give the selected screenshot, trace,
   log, and report tools absolute paths inside that directory. Never leave a
   relative screenshot path or a tool-default output directory pointed at the
   active checkout. A repository-owned browser fixture is the only exception.
4. Initialize `browser-session` only when a durable record is required, then
   execute the browser, Playwright, HTTP, or desktop path. Record only
   meaningful actions and assertions; link screenshots, traces, logs, or HTTP
   bundles that support them.
5. Verify the selected output or owning record and report the exact claim
   proved. If the required browser or desktop capability is unavailable, report
   a bounded blocker or a narrower verified claim instead of upgrading static
   evidence into success.

Public fixtures and provider records use generic runtime roles and redacted
artifact metadata. Machine names, users, local paths, connection details, and
credentials remain in private runtime evidence only.

## UI Change Evidence

When a change alters what a user sees or interacts with, put the following
evidence in the PR or MR's Test plan. Use the project's browser harness for
repeatable headless checks; screenshots support the measured assertions.

- List every affected view, including each consumer of a shared component.
  For each view, record viewport width and height and the layout tier it hits.
  Check both sides of every affected breakpoint and documented user sizes.
- Capture before/after screenshots at the base and changed commits with the
  same fixture/data and interaction state, including relevant focus, hover
  and open-menu states.
  Use immutable evidence links tied to those commits.
- Assert the property that was wrong with a repeatable check: for example
  clipping, overlap, offset, horizontal overflow or page errors. For a defect,
  show the check fail on the base and pass on the change. State the assertion
  and result for each applicable view and viewport.
- Use project fixtures; include production-like volume or long values when
  they trigger the defect. Keep private data out of public evidence.
- State the browser or packaged client version checked and which client
  versions contain the change. A web build does not establish a packaged
  client's shipped version.
- List unverified native shells, devices and physical displays with the reason
  and remaining acceptance. Headless success does not verify those surfaces.

### PR / MR Evidence Template

Copy these tables into the Test plan. Add one row per affected view and
viewport; identify a shared fixture/state once when it applies to every row.

| View / component consumer | Viewport and layout tier | Fixture / interaction state | Browser / client version |
| --- | --- | --- | --- |
| Affected view | Width × height; breakpoint side | Fixture, volume, focus / hover / menu state | Tested version; versions containing the change |

| View and viewport | Before / after images at fixed commits | Measured assertion | Base / changed result |
| --- | --- | --- | --- |
| Matching matrix row | Immutable baseline and change links | Repeatable check and relevant measurement | Failure / pass, or the observed results |

| Unverified surface | Reason | Remaining acceptance |
| --- | --- | --- |
| Native shell, device or display | Capability unavailable | Claim still to be checked |

## Product Capability Ceiling

Codex and Claude run the shared runtime-kit hooks; browser operation still
depends on the tools available to the active host.

Hermes reads this policy from the runtime kit and runs the same
browser/evidence CLIs manually, but it has no runtime-kit hook path. Report the
available browser/desktop transport; do not claim hook parity.
