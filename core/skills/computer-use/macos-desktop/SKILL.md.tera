---
name: macos-desktop
description: >
  Operate and test a local or SSH-reachable macOS desktop through nils-cli
  macos-agent, with AX-first actions, screenshots, guarded multi-step flows, explicit
  postconditions, guarded replay, and privacy-preserving journals.
---

# macOS Desktop Computer Use

## Contract

Use the released `macos-agent` adapter as the only mechanics layer. Peekaboo
owns native macOS observation and input. `macos-agent` owns the immutable
backend lock, install/verify/rollback, local and SSH transport, tool policy,
artifact transfer, redaction, journal integrity, and replay enforcement. This
skill owns intent, target selection, side-effect approval, postcondition
quality, visual interpretation, defect significance, and final acceptance.

Prerequisites:

- The target runs macOS 15 or newer with an active, unlocked graphical login.
- `macos-agent >=1.27.3` is installed on the controller and target. For SSH,
  both ends must report the same adapter version and Peekaboo lock.
- The locked backend is installed and verified. Do not install or select a
  floating Peekaboo release outside `macos-agent backend`.
- Accessibility, Automation, and Screen Recording permissions are granted to
  the effective runtime authority. `macos-agent` reports permission state but
  never mutates TCC.
- A trusted SSH alias and non-interactive authentication already exist when a
  remote target is used. Pass the alias only through runtime `--host`.
- Read [references/setup.md](references/setup.md) for install, permission,
  transport, and rollback checks.

Inputs:

- One named app/window or bounded desktop fixture, the desired outcome,
  allowed mutation scope, and stopping conditions.
- A local target or a runtime-only trusted SSH alias.
- Optional runtime mode, evidence mode, or MCP tool profile.
- Optional output directory. Allocate one internally when absent.

Outputs:

- A versioned adapter result for every non-MCP command. `macos-agent mcp`
  reserves stdout for JSON-RPC 2.0 frames only; session status is represented
  by its process exit and structural journal rather than an adapter envelope.
- One homogeneous adapter run directory per interface and execution tuple,
  containing `manifest.json`, `steps.jsonl`, `artifacts/index.json`,
  `summary.json`, and `redaction.json`; `review.json` appears after review. A
  broader workflow may retain several sibling run directories under one
  caller-owned session root.
- A pass/fail/blocked conclusion grounded in an observed postcondition, not
  merely process exit zero.
- Explicit residuals for skipped capabilities. Active Peekaboo v4.2.2
  readiness rejects any waived or reduced distribution result.

## Surface Selection

Prefer the most deterministic surface that can prove the outcome. GUI driving
is the last rung, not the default: published macOS GUI-agent benchmarks put
end-to-end task success far below what a scripted interface reaches, so skip a
rung only when it genuinely does not exist for this target.

| Rung | Surface | Use when |
| --- | --- | --- |
| 1 | App Intents / Shortcuts | The target publishes an action Shortcuts can run. |
| 2 | First-party CLI or API | The target ships a command line or local API that performs the outcome. |
| 3 | Scripting dictionary | The target exposes AppleScript/JXA terminology for the outcome. |
| 4 | Adapter AX interaction | Only a GUI exists and its accessibility tree is healthy. |
| 5 | Bounded coordinate fallback | The tree is degenerate and fresh observation proved the geometry. |

Rungs 1 to 3 run outside the adapter and are not adapter capabilities. They do
not widen the adapter surface. Adapter shell remains hard-disabled, and so do
browser, agent/analysis, audio, clipboard, and configuration tools; a
caller-side surface never reopens a denied adapter tool.

State the selected rung and why the rungs above it were rejected before the
first mutation, and carry that reason in the run intent so a reviewer can see
the outcome was not driven through pixels by default.

Choosing a higher rung buys determinism, never reduced approval. The Approval
Boundary below governs every rung equally: preferring Shortcuts, a first-party
CLI, or a scripting dictionary is not authorization to act outside the named
target or to take an action that would need approval through the GUI.

### Browser Claim Handoff

Hand a DOM, selector, or rendered-page claim to the `browser-test` route in
`core/policies/browser-test-routing.md`. This skill owns native window chrome,
cross-application behavior, permission dialogs, and AX interaction, and claims
no DOM or CDP capability of its own.

The browser route owns signed-in session state and its own artifact directory.
Link its output from the parent session instead of re-observing the same page
through AX, and never report a desktop screenshot of a browser window as proof
of rendered DOM state.

## Outcome Routing

Infer local versus SSH from the named reachable target, select the narrowest
evidence mode and runtime that satisfy the outcome, and allocate the journal
root without asking the user to choose transport or evidence substeps. Ask only
when the target is ambiguous or an action crosses the approval boundary.

Allocate one caller-owned session root. Each child run directory is homogeneous
for one interface and `(backend_digest, runtime, transport, evidence_mode,
tool_profile)` tuple; reuse that child only while every dimension remains
unchanged and the 512-step journal rotation bound is not reached. Allocate a
new sibling child before switching between `exec` or `mcp`, before
changing any tuple dimension, or after any backend install, rollback, or
replacement:

```bash
session_root="$(agent-out project --topic macos-computer-use --repo "$PWD" --mkdir)"
exec_out="$session_root/local-exec-minimal-app"
mkdir -p "$exec_out"
```

Add `--host "$MACOS_SSH_HOST"` to `backend`, `doctor`, `capabilities`, `exec`,
or `mcp` for an SSH target. Never copy SSH, transfer, or redaction
logic into the skill; the adapter owns those mechanics.

## Readiness And Backend Lifecycle

Inspect status before mutation. Install only when the locked backend is absent,
after first reviewing the dry-run:

```bash
macos-agent backend status --format json
macos-agent backend install --dry-run --strict --format json
macos-agent backend install --strict --format json
macos-agent backend verify --strict --format json
macos-agent doctor --strict --format json
macos-agent capabilities --strict --format json
```

For SSH, pass the runtime alias to each command. `doctor --strict` is a hard
readiness gate for a live mutation. Report-only doctor may be used to inventory
degraded capabilities. The v4.2.2 CLI and app require notarization and must
report `security_posture=full`; an active waived or reduced result is not ready.

A strict doctor result whose only blocked check is `bridge` with
`Peekaboo GUI Bridge exact build is unavailable`, while backend verification,
runtime, permissions, and capability probes pass, is a cold app-runtime state,
not a terminal blocker. Bootstrap it autonomously with one bounded read-only
`exec --runtime app` observation of the named target. The adapter launches the
owned stable app when needed and verifies its exact GUI Bridge handshake:

```bash
macos-agent exec \
  --out-dir "$exec_out" \
  --intent "Bootstrap the verified GUI Bridge and inspect the target" \
  --runtime app \
  -- see --app "$TARGET_APP" --json
macos-agent doctor --strict --format json
macos-agent capabilities --strict --format json
```

For SSH, pass the same runtime alias to all three commands. After the read-only
bootstrap, rerun strict doctor and capabilities before any mutation. Do not
reinstall an already verified backend for this state, do not use a floating
Peekaboo build, and do not treat a backend mismatch, permission denial, failed
observation, or still-blocked strict result as cold-start recovery.

## Accessibility Health Gate

Judge accessibility health before the first mutation. Read the fresh `see`
result and decide whether the tree actually exposes the declared target and
actionable elements, or is degenerate: empty, collapsed into one opaque
container, or a window whose visible controls never appear as elements.

Chromium-family web content, Qt, OpenGL and canvas-drawn surfaces, and other
non-native toolkits routinely report a degenerate tree. On that result:

- Take the bounded coordinate fallback of rung 5 only inside the declared
  application, only when a fresh observation proved the current geometry, and
  only with an explicit postcondition.
- Otherwise stop and report a blocker that names the application class, rather
  than continuing to search the tree for a target it does not publish.

Continuing to probe a degenerate tree is a false-success risk, and a false
success is always a functional blocker under the acceptance standard below.
Never widen the target, retry blindly, or substitute a screenshot description
for an observed postcondition.

## Execute And Prove Postconditions

Peekaboo arguments follow `--` unchanged, and each verb's argument shape
differs (for example `app launch <name>` takes a positional name while
`app quit --app <name>` requires the flag), so read `-- <verb> --help` through
the adapter before guessing. Read-only observation may omit `--expected`:

```bash
macos-agent exec \
  --out-dir "$exec_out" \
  --intent "Inspect Calculator controls" \
  --runtime app \
  -- see --app Calculator --json
```

Every mutation requires a fresh, externally observable postcondition. A click
resolves against the latest `see` snapshot, so observe first: `--on`/`--id`
take the opaque element ID that `see`/`inspect_ui` reported (a human label is
the positional `[query]`, never an `--on` value), while `type`/`press` drive
the focused app with no element ID:

```bash
macos-agent exec \
  --out-dir "$exec_out" \
  --intent "Clear Calculator" \
  --expected "Calculator display is zero" \
  --runtime app \
  -- click --app Calculator --on "$clear_button_id" --json
```

Prefer stable app/window/AX descriptions and fresh snapshot lineage. Use
coordinates only after fresh observation proves the target geometry and the
coordinate remains inside the declared app. Re-observe after every mutation.
When a displayless controller reports `display_count=0`, do not claim snapshot
element-ID targeting; a fresh-observation coordinate fallback is acceptable
only with an explicit postcondition on the active GUI target.

Treat timeout or signal termination during a mutation as unknown. Observe the
current UI before deciding what to do and never blindly retry a non-idempotent
action. Exit zero confirms adapter execution, not user-visible success.

## Multi-step Flows

Peekaboo v4 removed the `.peekaboo.json` runner. Build a repeatable flow from
individually reviewed `exec` calls in one homogeneous exec journal. Check each
result and its postcondition before continuing; never use a shell fallback or
send an unreviewed command bundle:

```bash
flow_out="$session_root/local-flow-minimal-app"
mkdir -p "$flow_out"
macos-agent exec \
  --out-dir "$flow_out" \
  --intent "Observe the first flow state" \
  --runtime app \
  -- see --app "$TARGET_APP" --json
macos-agent exec \
  --out-dir "$flow_out" \
  --intent "Perform the reviewed next step" \
  --expected "The target reports the next state" \
  --runtime app \
  -- click --app "$TARGET_APP" --on "$target_id" --json
```

Keep setup/reset steps and assertions explicit so each run is independent.
After partial failure, inspect the journal and resume only from a newly observed
state; never assume all prior steps completed.

A flow worth rerunning is a tracked fixture, not transcript prose. Declare it
with [references/flow-fixtures.md](references/flow-fixtures.md) and run it as
the same chained `exec` calls in one homogeneous journal. `journal replay-plan`
is not the rerun mechanism: its `never` classification and ineligible SSH rows
are deliberate safety ceilings, not a limitation to work around.

## MCP Tool Profiles

Use stdio MCP only when an interactive agent needs a bounded tool catalog:

```bash
mcp_out="$session_root/local-mcp-sensitive-app-observe"
mkdir -p "$mcp_out"
macos-agent mcp --out-dir "$mcp_out" --runtime app --tool-profile observe
```

Profiles are monotonic:

| Profile | Admitted capability families |
| --- | --- |
| `observe` | `see`, `inspect_ui`, `permissions`, `sleep`, `verify_state` |
| `interact` | observe plus click/type/press/scroll/drag/move, AX value/action, and bounded app/window/menu operations |
| `extended` | interact plus dialog, Dock, Spaces, capture, and paste |

Choose `observe` by default, `interact` for a declared mutation, and `extended`
only for a named extended operation. Agent/analysis, audio, browser, clipboard,
configuration/credentials, image, `mcp_agent`, permission mutation, shell, HTTP
MCP, and SSE MCP remain hard-disabled. Do not attempt a different interface or
upstream configuration to recover a denied tool.

## Evidence And Runtime Choices

Evidence modes:

| Mode | Use |
| --- | --- |
| `minimal` | Default structural journal and sanitized upstream response. |
| `debug` | Diagnose a reproducible failure; additionally retain a sanitized upstream result artifact. |
| `sensitive` | Suppress values, titles, paths, and payload fields; retain no replay material or screenshots for sensitive input. |

Runtime modes:

| Mode | Use |
| --- | --- |
| `app` | Stable default and preferred TCC authority. |
| `daemon` | Verified CLI daemon when a GUI Bridge is not the intended authority. |
| `auto` | Reuse an exact compatible Bridge, otherwise start the verified daemon. |
| `process` | Diagnostic direct process with `--no-remote`; not the normal acceptance path. |

Never promote raw screenshots, window titles, typed values, host identities,
home paths, or provider payloads into source, issues, PRs, or durable evidence.

## Journal Review And Replay

Close every run by rebuilding the summary and reviewing failures:

```bash
run_out="$exec_out" # select the completed homogeneous child to inspect
macos-agent journal summarize --out-dir "$run_out" --format json
macos-agent journal review --out-dir "$run_out" --format json
macos-agent journal replay-plan --out-dir "$run_out" --format json
```

Use replay classifications as hard ceilings:

- `safe`: replay only a reconstructable read-only local step when it still
  serves the same intent.
- `conditional`: require explicit confirmation, a fresh matching current
  snapshot, and a fresh `--expected` postcondition.
- Steps classified as `never` are not replayable. Sensitive input, typed/pasted
  values, policy blocks, unknown mutations, destructive/external actions,
  tampered metadata, and changed backend digests stay in this class.
- SSH steps retain the derived `safe|conditional|never` classification for
  review, but every SSH replay-plan row is `eligible=false` and remote
  `replay-step` is refused. Classification never implies remote eligibility.

For a conditional local replay, supply every guard explicitly:

```bash
macos-agent journal replay-step \
  --out-dir "$run_out" \
  --step step-000001 \
  --confirm-conditional \
  --current-snapshot snapshot-current \
  --expected "The newly observed postcondition"
```

Significant review classes include privacy/redaction, wrong target, false
success, unknown mutation, held input, remote cleanup, journal/replay integrity,
backend drift, and permission drift. Reproduce safely, assign one explicit
owner (`adapter`, `Peekaboo/adapter`, `runtime skill policy`, or `TCC
environment`), and retain sanitized evidence. Never create an issue automatically.
Use the active issue-backed workflow only after the user selects
that outcome. Do not open an upstream issue merely to unblock scheduling; if a
required native capability has no acceptable workaround, evaluate a controlled
fork as a separate implementation decision.

## Acceptance Standard

A functional claim passes only when all applicable checks hold:

1. Readiness and exact backend verification succeeded through the real local or
   SSH transport.
2. The target was freshly observed before mutation and the action stayed inside
   the declared scope.
3. An explicit postcondition was observed after mutation; exit zero alone is
   insufficient.
4. The same fixture completed at least three independent runs, each with its
   own setup, reset, and fresh observation, and the observed
   postcondition success rate is read back from those journals. A flow
   converges and may be called unattended-safe only at a full success rate
   across those independent runs; a lower rate is reported as not
   unattended-safe with the observed rate and the failing step. Repeated
   independent runs are never a blind mutation retry, which remains forbidden.
5. Required journal files validate, sensitive suppression is clean, and every
   significant review candidate has an owner.
6. For installed-surface acceptance, a fresh product session discovers this
   skill, uses direct `macos-agent`, and never invokes retired mechanics or a
   disabled tool.
7. Release transition recovery is proven without changing the accepted live
   state: an authenticated v3.9.3 predecessor can upgrade in place and recover
   after interruption, but it cannot be reactivated or selected as rollback;
   rollback dry-run refuses deterministically and a subsequent status read-back
   reports the unchanged v4.2.2 receipt.

The canonical status/evidence inventory is
[`docs/source/macos-agent-capability-matrix.md`](https://github.com/sympoies/agent-runtime-kit/blob/main/docs/source/macos-agent-capability-matrix.md).
Do not infer support beyond that matrix. Active v4.2.2 acceptance requires full
distribution-security posture; the historical v3.9.3 notarization waiver is
transition-authentication metadata only and never an accepted runtime
residual. Privacy leaks, wrong targets, false success, or unusable behavior are
always functional blockers.

## Approval Boundary

Normal interaction inside an explicitly declared disposable fixture may
proceed without per-click confirmation. Ask before sending messages, submitting
external forms, deleting persistent data, purchasing, changing accounts or
permissions, entering real credentials, exposing unrelated private content, or
leaving the named test target. This skill does not unlock or log into a Mac,
bypass TCC, expose a remote shell, or widen scope silently.
