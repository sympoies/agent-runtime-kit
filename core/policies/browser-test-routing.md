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
unreliable for Chromium-family content. This route owns signed-in session state and its own artifact
directory; the desktop route owns native window chrome, cross-application
behavior, permission dialogs, and AX interaction. A desktop screenshot of a
browser window is never proof of rendered DOM state.

## Parent Workflow

1. Activate the `browser-test` intent and read this document.
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

## Product Capability Ceiling

Codex and Claude can receive selective intent cues and enforce active
`project-dev` state through shared hooks once the installed nils-cli exposes
durable session verification. Browser operation still depends on the tools
available to the active host.

Hermes resolves this policy from the selected docs home and runs the same
browser/evidence CLIs manually, but it has no runtime-kit hook or automatic
agent-docs injection path. Report the available browser/desktop transport; do
not claim hook parity.
