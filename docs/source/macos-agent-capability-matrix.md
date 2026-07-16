# macos-agent Capability Matrix

## Purpose

This is the canonical runtime-kit claim for the Peekaboo-backed
`computer-use.macos-desktop` route. It describes nils-cli `macos-agent` adapter
v2, introduced by the planned v1.22.6 cutover and locked to Peekaboo v3.9.3.
The adapter implementation was reviewed and merged in
[sympoies/nils-cli#1234](https://github.com/sympoies/nils-cli/pull/1234); the
runtime cutover is tracked in
[graysurf/agent-runtime-kit#610](https://github.com/graysurf/agent-runtime-kit/issues/610).

Status meanings:

- `supported`: normal skill path and part of functional acceptance.
- `adapter`: mechanics owned and enforced by nils-cli rather than the skill or
  Peekaboo alone.
- `optional`: available only with an explicit non-default mode or tool profile.
- `disabled`: exists upstream but is blocked by adapter policy.
- `unsupported`: outside the product claim; do not improvise a workaround that
  silently widens the boundary.

Evidence names are public summaries only. Raw desktop captures, host identity,
paths, AX values, and typed data remain in private `agent-out` journals.

## Matrix

| Capability | Status | Contract / option | Evidence |
| --- | --- | --- | --- |
| macOS 15+ active GUI session | supported | Local or SSH target must be unlocked with an active graphical login. | Adapter platform guard; live Calculator acceptance summarized on #610. |
| macOS before 15 | unsupported | No compatibility claim. | `capabilities` minimum macOS plus negative platform guard tests in nils-cli#1234. |
| Local execution | supported | `doctor`, `exec`, `scenario`, and stdio `mcp` operate locally. | Deterministic transport suite and live local Calculator acceptance. |
| Local / SSH execution | adapter | `--host <trusted-alias>` uses fixed remote commands and typed stdin; no remote shell surface. | Fake-SSH suite, controller-side live acceptance, and privacy scan. |
| Exact backend pin, verification, and rollback | adapter | Immutable tag/commit/assets/digests/signatures with one allowlisted previous release. | Lock/provenance tests plus isolated install → verify → rollback → verify drill. |
| App-held TCC authority | supported | `--runtime app` is the stable default. | Bridge handshake tests and live foreground/background acceptance. |
| Daemon/auto/process runtimes | optional | `daemon` and `auto` use verified digest-scoped authority; `process` is diagnostic `--no-remote`. | Runtime selection/lease/transition tests in nils-cli#1234. |
| Permission diagnosis | supported | `doctor` and `capabilities` report readiness; strict doctor gates live mutation. | Deterministic doctor matrix and live strict-doctor result. |
| Permission mutation or TCC bypass | disabled | Adapter never grants, resets, or bypasses TCC. | Hard-disabled capabilities output and policy-negative tests. |
| Apps/windows list, focus, move, and resize | supported | Use reviewed Peekaboo argv through `exec`; mutations require `--expected`. | Peekaboo contract tests and local/SSH live target exercises. |
| AX/UI inspection and stable element targeting | supported | Prefer fresh UI maps/snapshots and stable target descriptions. | Peekaboo contract tests plus fresh observation acceptance. |
| Displayless element-ID targeting | unsupported | `display_count=0` does not support the snapshot element-ID claim. | Live residual reproduced during Task 3.2 and recorded on #610. |
| Fresh-observation coordinate fallback | optional | Allowed only inside the declared app with an explicit postcondition. | Live displayless global-coordinate canary passed with 0→3 postcondition. |
| Action-first click/set-value/named action | supported | Mutations require an observable `--expected` result. | Policy tests and live Calculator action acceptance. |
| Coordinate click, button, count, modifiers | supported | Last-resort bounded input after current geometry observation. | Peekaboo CLI contract plus synthetic input acceptance. |
| Type, press, and hotkey | supported | Values are redacted; sensitive values are never replayable. | Sensitive journal/redaction tests and live synthetic fixture. |
| Move, drag, scroll, and swipe | supported | Atomic gesture followed by state verification; no blind retry. | Deterministic family tests and repeated no-retry acceptance. |
| Background-process input | supported | Explicit target and postcondition required; foreground behavior must remain explicit. | Live background input acceptance with observed 0→3 state change. |
| Full/window/region screenshot and UI map/OCR | supported | Use the narrowest target; evidence mode governs retention. | Peekaboo contract and adapter artifact-index tests. |
| Menus and menubar | supported | Observation is normal; activation remains approval- and postcondition-governed. | Peekaboo command-family tests and adapter policy classification. |
| Dialog, Dock, and Spaces | optional | Requires the `extended` MCP profile or explicit CLI operation. | Tool-profile allowlist tests and `capabilities` output. |
| Clipboard paste | optional | `extended` profile plus sensitive handling; no retained payload or replay. | MCP profile tests and sensitive replay-negative tests. |
| Multi-step `.peekaboo.json` scenario | supported | Reviewed, private staged copy; partial failure remains journaled. | Scenario staging/integrity tests and partial-failure smoke review. |
| Waits and postconditions | supported | Engine waits plus caller-owned observable acceptance; exit zero alone is insufficient. | Mutation-policy tests and live postcondition assertions. |
| Versioned JSON and debug diagnostics | supported | `macos-agent.adapter.v2`; debug retains only sanitized result artifacts. | CLI contract and journal artifact-index tests. |
| Execution journal | adapter | Manifest, append-only steps, artifact index, summary, and redaction are mandatory. | Journal recovery/integrity suite and private schema audits. |
| Guarded replay | adapter | `safe`, `conditional`, or `never`; remote journals and sensitive input are never locally replayed. | Replay derivation/tamper tests and live never-replay refusal. |
| Failure review and ownership | adapter | `journal review` proposes explicit owners without provider mutation. | Significant-class clustering tests and seeded wrong-target smoke review. |
| Artifact transfer and cleanup | adapter | Private remote staging, bounded transfer, hash validation, and cleanup audit. | Fake-SSH fault matrix and live controller privacy scan. |
| MCP stdio | optional | Local/SSH proxy with `observe`, `interact`, or `extended` profiles. | JSON-RPC framing, cancellation, shutdown, SSH status, and profile tests. |
| MCP HTTP/SSE | unsupported | Upstream stubs are not exposed. | Capabilities ceiling and negative interface tests. |
| Natural-language agent / AI analysis | disabled | Calling agent owns planning and interpretation. | `agent`/`analyze` hard-deny tests and capabilities output. |
| Browser DOM/CDP | disabled | Use a separately governed browser route; no unpinned package fallback. | `browser` hard-deny tests and hostile upstream-config tests. |
| Dia DOM/page automation | unsupported | Native AX only; no DOM claim. | Boundary review in #610; no adapter command family. |
| Shell and audio | disabled | Never available through CLI or MCP profiles. | `shell`/`audio` hard-deny tests and negative MCP calls. |
| Configuration and credentials management | disabled | Provider configuration, keys, and credential tools are stripped/denied. | Environment-clearing and hostile-config MCP tests. |
| Secret/private-key entry | optional | Only an explicitly approved sensitive fixture; no real credential in acceptance, screenshot, value, or replay material. | Synthetic sensitive canary scan and `never` replay classification. |
| Locked/logged-out desktop | unsupported | SSH cannot create a usable WindowServer session. | Strict doctor/runtime readiness failure classification. |

## Acceptance Boundary

Functional correctness and usability are hard gates: fresh observation,
explicit postconditions, local/SSH behavior where claimed, independent reruns,
fresh-session discovery, journal validity, privacy suppression, and rollback
readiness must pass. Wrong target, false success, unusable interaction, leaked
sensitive data, or non-repeatable mutation blocks acceptance.

The exact v3.9.3 standalone-CLI notarization waiver is a disclosed
distribution-security residual, not a claim of success. It may remain
non-blocking only while app notarization, Gatekeeper, signatures, archive and
executable hashes, architecture, version, locked capabilities, and functional
acceptance remain green. Any broader or silent bypass is outside this matrix.
