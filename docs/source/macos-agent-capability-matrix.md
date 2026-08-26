# macos-agent Capability Matrix

## Purpose

This is the canonical runtime-kit claim for the Peekaboo-backed
`computer-use.macos-desktop` route. It describes nils-cli `macos-agent` adapter
v3, introduced by the v1.27.3 migration and locked to Peekaboo v4.2.2.
The adapter implementation was reviewed and merged in
[sympoies/nils-cli#1478](https://github.com/sympoies/nils-cli/pull/1478); live
v4.2.2 cutover evidence is retained by the consumer delivery for this matrix.

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
| macOS 15+ active GUI session | supported | Local or SSH target must be unlocked with an active graphical login. | Adapter platform guard plus consumer-delivery live Calculator acceptance. |
| macOS before 15 | unsupported | No compatibility claim. | `capabilities` minimum macOS plus negative platform guard tests in nils-cli#1478. |
| Local execution | supported | `doctor`, `exec`, and stdio `mcp` operate locally. | Deterministic transport suite and live local Calculator acceptance. |
| Local / SSH execution | adapter | `--host <trusted-alias>` uses fixed remote commands and typed stdin; no remote shell surface. | Fake-SSH suite, controller-side live acceptance, and privacy scan. |
| Exact backend pin and verification | adapter | Immutable tag/commit/assets/digests/signatures; v3.9.3 is transition-only for in-place upgrade and cannot be reactivated. | Lock/provenance tests plus transition-only upgrade regression. |
| Backend freshness audit | adapter | This matrix, `docs/source/nils-cli-pin.yaml`, and `docs/source/nils-cli-surface.md` must name the same pinned Peekaboo release. Adopting a newer upstream release stays a separate reviewed decision. | Network-free mirror-agreement assertion in the surface-routing contract probe. |
| App-held TCC authority | supported | `--runtime app` is the stable default. | Bridge handshake tests and live foreground/background acceptance. |
| Daemon/auto/process runtimes | optional | `daemon` and `auto` use verified digest-scoped authority; `process` is diagnostic `--no-remote`. | Runtime selection/lease/transition tests in nils-cli#1478. |
| Permission diagnosis | supported | `doctor` and `capabilities` report readiness; strict doctor gates live mutation. | Deterministic doctor matrix and live strict-doctor result. |
| Permission mutation or TCC bypass | disabled | Adapter never grants, resets, or bypasses TCC. | Hard-disabled capabilities output and policy-negative tests. |
| Apps/windows list, focus, move, and resize | supported | Use reviewed Peekaboo argv through `exec`; mutations require `--expected`. | Peekaboo contract tests and local/SSH live target exercises. |
| AX/UI inspection and stable element targeting | supported | Prefer fresh UI maps/snapshots and stable target descriptions. | Peekaboo contract tests plus fresh observation acceptance. |
| Displayless element-ID targeting | unsupported | `display_count=0` does not support the snapshot element-ID claim. | Live residual retained in the consumer-delivery acceptance evidence. |
| Accessibility health gate | supported | Judge tree health on the fresh `see` result before any mutation, then take the bounded coordinate fallback or stop with a named blocker. | Accessibility health gate in the skill plus the surface-routing contract probe. |
| Degenerate-AX application classes | unsupported | Chromium-family web content, Qt, OpenGL and canvas-drawn surfaces, and other non-native toolkits that publish no usable tree. Continuing to probe one is a false-success risk, not a retry case. | Negative-class row asserted by the surface-routing contract probe. |
| Deterministic surface preference | supported | App Intents/Shortcuts, a first-party CLI/API, or a scripting dictionary outranks GUI driving. Those rungs run outside the adapter and never reopen a denied adapter tool. | Surface selection ladder asserted for source and every rendered product. |
| Rerunnable flow fixtures | supported | Declare a repeatable flow in a tracked fixture and run it as chained `exec`; `journal replay-plan` is not the rerun mechanism. | `references/flow-fixtures.md` rendered-reference equality plus fixture-shape assertions. |
| Cold app-runtime bootstrap | supported | A strict doctor blocking only `permissions` and `bridge` under `required capability probe failed` is cold start; one bounded read-only observation clears both. Anything still blocked afterwards is a real fault. | Live cold-runtime bootstrap on an SSH target plus the live-recovery contract probe. |
| Outcome envelope interpretation | supported | Read `mutation_dispatched`, `effect`, `escalation`, and `refusal_reason` as dispatch metadata. `unverifiable` with a dispatched mutation is judged on the observed postcondition, never on `effect` alone. | Live three-run Calculator fixture at a 3/3 observed postcondition rate plus the live-recovery contract probe. |
| Partial-inventory identity retargeting | supported | When a process without process-generation identity fails name resolution, re-resolve `pid` and `process_start_identity` from `app list` and retarget with `--pid`, binding a destructive verb with `--expected-process-start-identity`. | Live recovery of a refused mutation on an SSH target plus the live-recovery contract probe. |
| SSH journal step accumulation | unsupported | Each SSH `exec` replaces the journal in `--out-dir` instead of appending, so a chained SSH flow cannot read its own stability rate back from `steps.jsonl`. Track the rate outside the journal until [sympoies/nils-cli#1512](https://github.com/sympoies/nils-cli/issues/1512) ships. | Controlled three-call repro against an SSH target; adapter defect filed upstream. |
| Fresh-observation coordinate fallback | optional | Allowed only inside the declared app with an explicit postcondition. | Live displayless global-coordinate canary passed with 0→3 postcondition. |
| Action-first click/set-value/named action | supported | Mutations require an observable `--expected` result. | Policy tests and live Calculator action acceptance. |
| Coordinate click, button, count, modifiers | supported | Last-resort bounded input after current geometry observation. | Peekaboo CLI contract plus synthetic input acceptance. |
| Type and press | supported | Values are redacted; sensitive values are never replayable. | Sensitive journal/redaction tests and live synthetic fixture. |
| Move, drag, and scroll | supported | Atomic gesture followed by state verification; no blind retry. | Deterministic family tests and repeated no-retry acceptance. |
| Background-process input | supported | Explicit target and postcondition required; foreground behavior must remain explicit. | Live background input acceptance with observed 0→3 state change. |
| Full/window/region screenshot and UI map/OCR | supported | Use the narrowest target; evidence mode governs retention. | Peekaboo contract and adapter artifact-index tests. |
| Menus and menubar | supported | Observation is normal; activation remains approval- and postcondition-governed. | Peekaboo command-family tests and adapter policy classification. |
| Dialog, Dock, and Spaces | optional | Requires the `extended` MCP profile or explicit CLI operation. | Tool-profile allowlist tests and `capabilities` output. |
| Clipboard paste | optional | `extended` profile plus sensitive handling; no retained payload or replay. | MCP profile tests and sensitive replay-negative tests. |
| Multi-step flow | supported | Chain individually reviewed `exec` calls; stop and re-observe after any failed step. No scenario runner or shell fallback is exposed. | Chained-exec partial-failure smoke review. |
| Waits and postconditions | supported | Engine waits plus caller-owned observable acceptance; exit zero alone is insufficient. | Mutation-policy tests and live postcondition assertions. |
| Versioned JSON and debug diagnostics | supported | `macos-agent.adapter.v3`; debug retains only sanitized result artifacts. | CLI contract and journal artifact-index tests. |
| Execution journal | adapter | Manifest, append-only steps, artifact index, summary, and redaction are mandatory. | Journal recovery/integrity suite and private schema audits. |
| Guarded replay | adapter | `safe`, `conditional`, or `never`; remote journals and sensitive input are never locally replayed. | Replay derivation/tamper tests and live never-replay refusal. |
| Failure review and ownership | adapter | `journal review` proposes explicit owners without provider mutation. | Significant-class clustering tests and seeded wrong-target smoke review. |
| Artifact transfer and cleanup | adapter | Private remote staging, bounded transfer, hash validation, and cleanup audit. | Fake-SSH fault matrix and live controller privacy scan. |
| MCP stdio | optional | Local/SSH proxy with `observe`, `interact`, or `extended` profiles. | JSON-RPC framing, cancellation, shutdown, SSH status, and profile tests. |
| MCP HTTP/SSE | unsupported | Upstream stubs are not exposed. | Capabilities ceiling and negative interface tests. |
| Natural-language agent / AI analysis | disabled | Calling agent owns planning and interpretation. | `agent`/`analyze` hard-deny tests and capabilities output. |
| Browser DOM/CDP | disabled | Route DOM, selector, and rendered-page claims to the `browser-test` route in `core/policies/browser-test-routing.md`; no unpinned package fallback. | `browser` hard-deny tests and hostile upstream-config tests. |
| Dia DOM/page automation | unsupported | Native AX only; no DOM claim. | Consumer-delivery boundary review; no adapter command family. |
| Shell and audio | disabled | Never available through CLI or MCP profiles. | `shell`/`audio` hard-deny tests and negative MCP calls. |
| Configuration and credentials management | disabled | Provider configuration, keys, and credential tools are stripped/denied. | Environment-clearing and hostile-config MCP tests. |
| Secret/private-key entry | optional | Only an explicitly approved sensitive fixture; no real credential in acceptance, screenshot, value, or replay material. | Synthetic sensitive canary scan and `never` replay classification. |
| Locked/logged-out desktop | unsupported | SSH cannot create a usable WindowServer session. | Strict doctor/runtime readiness failure classification. |

## Acceptance Boundary

Functional correctness and usability are hard gates: fresh observation,
explicit postconditions, local/SSH behavior where claimed, independent reruns,
fresh-session discovery, journal validity, privacy suppression, and release
transition readiness must pass. Wrong target, false success, unusable interaction, leaked
sensitive data, or non-repeatable mutation blocks acceptance.

Peekaboo v4.2.2 requires notarized CLI and app artifacts and reports full
distribution-security posture. The v3.9.3 waiver is retained only inside the
transition-only tuple needed to authenticate an installed predecessor; it does
not authorize execution or rollback under adapter v3. Any broader or silent
bypass is outside this matrix.
