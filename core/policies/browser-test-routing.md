# Browser Test Routing

## Purpose

A browser-test request is one user outcome. The parent chooses the smallest
execution path that can prove the requested claim, operates that surface, and
retains verified evidence. Users should not need to choose a recorder skill or
translate the request into bookkeeping commands.

## Route By Claim

| Claim | Execution path | Evidence boundary |
| --- | --- | --- |
| HTTP availability, headers, status, or static response body | HTTP client or `web-evidence` | Supports only the captured HTTP response. |
| Rendered page state, navigation, or visual acceptance that can be exercised in an available browser | Browser operator plus `browser-session` | Initialize before operation, record meaningful interactions/assertions and artifacts, then verify. |
| Repeatable DOM interaction, selectors, network waits, or regression coverage | Project Playwright/browser test harness | Retain test output and, when useful, link screenshots/traces from the parent browser session. |
| Native macOS UI, browser chrome, cross-application behavior, permission dialogs, or accessibility-tree interaction | macOS desktop Computer Use outcome | Use the desktop safety/AX workflow and retain screenshot or recording evidence; do not describe this as a browser-only test. |
| Small local command that proves a service/test path | `canary-check` | Supports the command result only; it is not rendered-browser evidence. |

Static HTTP success must not be reported as proof that JavaScript rendered, a
visual assertion passed, or a desktop interaction occurred. Source inspection
alone is not browser execution.

## Parent Workflow

1. Activate the `browser-test` intent and read this document plus the shared
   evidence-control-plane policy.
2. State the target, acceptance claim, available execution environment, and
   chosen route.
3. Allocate one parent-owned artifact directory. Initialize `browser-session`
   before rendered browser work when session evidence is needed.
4. Execute the browser, Playwright, HTTP, or desktop path. Record only
   meaningful actions and assertions; link screenshots, traces, logs, or HTTP
   bundles that support them.
5. Verify the owning record and report the exact claim proved. If the required
   browser or desktop capability is unavailable, report a bounded blocker or a
   narrower verified claim instead of upgrading static evidence into success.

Public fixtures and provider records use generic runtime roles and redacted
artifact metadata. Machine names, users, local paths, connection details, and
credentials remain in private runtime evidence only.

## Product Capability Ceiling

Codex and Claude can receive selective intent cues and enforce active
`project-dev` state through shared hooks once the installed nils-cli exposes
durable session verification. Browser operation still depends on the tools
available to the active host.

Hermes can read this policy and run the same browser/evidence CLIs, but it has
no runtime-kit hook or agent-docs injection path. Report explicit CLI evidence
and the available browser/desktop transport; do not claim hook parity.
