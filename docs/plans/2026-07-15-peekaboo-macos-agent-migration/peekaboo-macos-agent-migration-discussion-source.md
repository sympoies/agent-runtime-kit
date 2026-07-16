# Implementation Source: Replace the macOS automation engine with pinned Peekaboo

## Status

- Status: ready for L2 plan-tracking execution
- Date: 2026-07-15
- Plan owner: `graysurf/agent-runtime-kit`
- Implementation repositories: `sympoies/nils-cli` and `graysurf/agent-runtime-kit`
- Live acceptance: one private macOS GUI role, locally and through SSH; host identity and raw artifacts stay private
- Open questions carried into execution: none

## Goal

Replace the custom `macos-agent` UI engine with official Peekaboo while retaining
a thin owned control plane. Peekaboo owns native UI behavior; `nils-cli
macos-agent` owns the exact upstream pin, install/verification, local/SSH
transport, MCP stdio, redaction, journaling, guarded replay, and rollback; the
`computer-use.macos-desktop` skill owns intent, approvals, postconditions,
privacy judgment, and defect routing.

Completion requires deterministic, security, local/SSH live, rollback, and
fresh-agent acceptance; a released nils-cli; and one runtime-kit cutover that
updates the skill and exact nils-cli pin. The released binary does not retain the
old Hammerspoon/AppleScript/cliclick engine as a second path.

## Inputs And Evidence

- [U1] The maintainer approved Peekaboo behind a thin transport/version layer.
- [U2] The maintainer requires the implementation, complete tests and retained
  evidence, supported/unsupported capability matrix, operating options,
  runtime-kit skill migration, and exact nils-cli pin update.
- [U3] Every computer-use run must leave useful debugging/self-improvement
  evidence so diagnosis can resume near the failure instead of repeating the
  whole UI journey; material defects must be reviewable later.
- [U4] After reviewing the distinction between functional correctness and
  Apple distribution assurance, the maintainer approved one transparent
  notarization waiver for the exact locked v3.9.3 standalone CLI. The waiver
  must not weaken digest, Developer ID, Team ID, architecture, version, app
  Gatekeeper/notarization, live usability, or future-release review gates; no
  Peekaboo fork is introduced for this delivery.
- [F1] The current `crates/macos-agent` has about 15,600 Rust source lines and
  7,400 Rust test lines implementing native backends, AX, input, screenshot,
  wait, scenario, retry, and profile behavior.
- [F2] The current skill adds a Python local/SSH wrapper that writes
  `session.jsonl`, transfers artifacts, redacts the SSH target, and records
  permission gaps.
- [F3] Runtime-kit currently requires `macos-agent >=1.21.13`; its exact
  nils-cli tag is independently pinned in `docs/source/nils-cli-pin.yaml`.
- [F4] Coupled nils-cli behavior must be developed/tested off-pin, released
  first, then consumed through `meta:nils-cli-bump`.
- [A1] Read-only target inventory found a supported Apple-silicon Mac on a
  macOS release newer than Peekaboo's macOS 15 floor, with the custom agent
  installed and Peekaboo absent.
- [W1] Peekaboo `v3.9.3` (2026-07-15) is the reviewed candidate. Its tag points
  to verified commit `3cfd612adbcb1b43e8431a7a1f3b02ec45d01269`; the
  universal CLI SHA256 is
  `793251fd3fd3b3f1ba5e61095c1204aa1cfcd6eae19a4d46fdb443b547a8cccf`
  and app ZIP SHA256 is
  `660fe5a25636edbb5b3f42fd817fa5948b60a1e9cb6a9c0994b6f105dc73ece9`.
  Source: <https://github.com/openclaw/Peekaboo/releases/tag/v3.9.3>.
- [W2] Peekaboo requires macOS 15+, provides native CLI and stdio MCP, and
  supports action-first AX, synthetic input, screenshots/UI maps, background
  input, apps/windows/menus/dialogs/Dock/Spaces, and scripts. Source:
  <https://github.com/openclaw/Peekaboo/tree/v3.9.3>.
- [W3] Permission-bound execution can use a daemon, Peekaboo.app Bridge, or
  process-local MCP; the Bridge is a local UNIX socket, not SSH. Source:
  <https://github.com/openclaw/Peekaboo/blob/v3.9.3/docs/ARCHITECTURE.md>.
- [W4] MCP stdio is implemented; HTTP/SSE are stubs. Source:
  <https://github.com/openclaw/Peekaboo/blob/v3.9.3/docs/commands/mcp.md>.
- [W5] The browser tool starts unpinned `chrome-devtools-mcp@latest`, requires
  Chrome remote-debugging approval, and can expose session-backed page data.
  Source: <https://github.com/openclaw/Peekaboo/blob/v3.9.3/docs/browser-mcp.md>.
- [W6] Peekaboo supplies allow/deny filters and documents AI, shell, dialog,
  capture, permission, clipboard, and input risks. Source:
  <https://github.com/openclaw/Peekaboo/blob/v3.9.3/docs/security.md>.
- [I1] Peekaboo replaces native UI behavior, but not SSH, exact dependency
  control, the privacy/evidence contract, or agent approval policy.
- [I2] A raw transcript is insufficient for improvement; records need failure
  signatures, state references, replay safety, redaction state, and routing.

## Resolved Architecture

### Ownership

| Layer | Owns | Must not own |
| --- | --- | --- |
| Peekaboo | Native AX/capture/input/app/window/menu/dialog/Dock/Space behavior, snapshots, scripts, native CLI/MCP JSON | SSH, nils/runtime-kit pins, approval policy, public evidence |
| `nils-cli macos-agent` | Exact lock, install/verify, local/SSH execution, stdio MCP proxy, transfer, timeouts, redaction, journal/replay/review mechanics, doctor, rollback | Native UI reimplementation, natural-language planning, arbitrary shell, silent TCC mutation |
| `computer-use.macos-desktop` | Outcome scope, approvals, strategy, postconditions, sensitivity, significant-defect judgment/routing | Duplicate transport/install/journal code or copied upstream command reference |

### Pin, install, and runtime

- Add a machine-readable lock under `crates/macos-agent` containing repository,
  tag, immutable commit, assets/SHA256, macOS floor, executable names, observed
  signing identity, and required capability probes.
- `v3.9.3` is the initial candidate, never a floating `latest`. Execution begins
  with a freshness/security recheck; any candidate change is a reviewed lock
  diff and reruns all candidate tests.
- Install the official universal CLI archive plus signed/notarized app. The
  standalone v3.9.3 CLI's missing notarization ticket is accepted only through
  a machine-readable waiver that repeats and matches the exact repository,
  tag, commit, archive/executable digests, Developer ID authority, and Team ID.
  Do not use `npx`, floating Homebrew, or a source build as production
  authority.
- Use user-scoped versioned backend storage, a stable app path, atomic current
  receipt, and one previous receipt. Refuse conflicting/unowned installs.
- Verify SHA256 before extraction, then architecture/version, `codesign
  --verify --deep --strict`, and exact signing metadata. App
  Gatekeeper/notarization remains mandatory. The CLI notarization command still
  runs under strict verification and must report either `pass` or the exact
  lock-owned `waived` status; any identity drift or undeclared/future waiver
  fails before action.
- Fast receipt/version/digest checks precede normal actions; `doctor --strict`
  runs full signature, app, Bridge, permission, and capability checks.
- `--runtime app` is the production default TCC authority. `daemon`, `auto`,
  and `process` are explicit diagnostics and the effective runtime is journaled.
- Upgrades never happen automatically; only a reviewed nils-cli release changes
  the upstream lock.

### Stable adapter surface

The adapter passes Peekaboo arguments verbatim after `--`; it does not remap
the full upstream grammar or preserve the old selector grammar.

```text
macos-agent backend install|status|verify|rollback [--host <target>] [--dry-run] [--strict] [--format json]
macos-agent doctor|capabilities [--host <target>] [--strict] [--format json]
macos-agent exec [--host <target>] --out-dir <dir> [--intent <text>]
  [--expected <text>] [--evidence-mode minimal|debug|sensitive]
  [--runtime app|daemon|auto|process] -- <peekaboo arguments>
macos-agent scenario [--host <target>] --out-dir <dir> --file <local .peekaboo.json>
  [--evidence-mode minimal|debug|sensitive] [--runtime app|daemon|auto|process]
macos-agent mcp [--host <target>] --out-dir <dir>
  [--tool-profile observe|interact|extended] [--runtime app|daemon|auto|process]
macos-agent journal summarize|review|replay-plan --out-dir <dir> [--step <id>] [--format json]
macos-agent journal replay-step --out-dir <dir> --step <id> [--confirm-conditional]
```

- `--host` is runtime-only and never persisted; omission means local.
- `minimal` always writes structural evidence and only necessary artifacts.
- `debug` additionally keeps sanitized JSON, focused screenshots, timings, and
  diagnostics. All redaction still applies.
- `sensitive` suppresses typed/clipboard/AX values, titles, raw payloads, and
  screenshots unless one narrowly scoped capture is separately approved. It
  records only type, length, and keyed digest when useful.
- MCP supports stdio only. The proxy keeps stdout protocol-clean and journals
  method/tool, correlation, timing, result, and sanitized artifact references,
  never complete sensitive payloads.
- Versioned JSON envelopes and distinct usage/backend/transport/permission/
  policy/upstream/journal exit classes are mandatory.

### Execution journal and improvement loop

Every `exec`, `scenario`, and `mcp` session writes a crash-safe append-only
journal under one caller-owned `agent-out` directory. It is not a screen
recording and not a secret transcript.

| Artifact | Required content |
| --- | --- |
| `manifest.json` | Journal/run schema, adapter/nils/Peekaboo versions/digests, runtime/transport without host identity, profile, sensitivity, open/closed state |
| `steps.jsonl` | Sequence/correlation/parent IDs, intent, sanitized argv shape, precondition refs, snapshot lineage, status/failure class, duration/retries, postcondition refs, replay class, artifact refs |
| `artifacts/index.json` | Hash, MIME/kind, producing step, sensitivity/redaction/retention class, relative path; no host paths |
| `summary.json` | Assertions, failed/skipped capabilities, failure signatures, unknown outcomes, replay and defect candidates, residual user actions |
| `review.json` | Deterministic clustering and proposed owner from `journal review`; the agent makes the final disposition |
| `redaction.json` | Applied rules, suppressed fields, redaction failures, and private-identifier/secret negative evidence |

Replay classes are `safe` (observation/setup), `conditional` (idempotent
mutation with validated pre/postconditions), and `never` (non-idempotent,
external, destructive, credential/clipboard, unknown-after-timeout,
policy-blocked, or unguarded). Replay reruns doctor and state guards, rejects
stale snapshots/state/backend digests, requires `--confirm-conditional`, and
creates a child step without overwriting history.

A run is a significant-defect candidate for privacy/redaction failure,
wrong-target action, false success with failed postcondition, unknown mutation
after timeout, held-input/remote-temp cleanup failure, journal/replay integrity
failure, unexpected backend/TCC drift, or the same normalized non-environment
failure in two independent sessions.

At closeout the skill runs `journal review` and classifies candidates as an
application/test issue, Peekaboo upstream issue, adapter defect, runtime-kit
skill/policy heuristic, TCC/environment gap, or transient. Raw journals remain
local. Only a reviewed sanitized minimal reproduction/summary may enter a
provider issue or `heuristic-inbox`, through its owning workflow and never
silently.

### Tool profiles

| Profile | Default tool families | Boundary |
| --- | --- | --- |
| `observe` | see, inspect UI, screenshot, list apps/windows/screens/menus, sleep | Narrow app/window/region; no AI |
| `interact` | observe + click/type/press/hotkey/scroll/swipe/drag/move/set-value/perform-action/bounded app/window/menu | Skill default; current target and postcondition required |
| `extended` | interact + dialog/Dock/menubar/Spaces/capture/paste | Admitted per operation; paste is sensitive |

The first release always denies Peekaboo agent/AI analysis, browser, shell,
audio, config/credential management, permission mutation, and `mcp_agent`.
Permission status remains observable. Set
`PEEKABOO_VISUALIZER_MASK_TYPED_TEXT=true` and disable AI providers.

## Target Capability Matrix

`supported` is default, `adapter` is owned by nils-cli, `optional` needs a
non-default option/profile, `disabled` exists upstream but is blocked, and
`unsupported` is outside the claim.

| Capability | Current | Peekaboo v3.9.3 | New contract / option |
| --- | --- | --- | --- |
| macOS platform | dependency-defined | macOS 15+ | supported on 15+; older unsupported |
| Local / SSH execution | helper | local only | supported / adapter via `--host`; no remote shell |
| Exact pin/signature/rollback | n/a | signed release assets | adapter lock, verify, one previous version |
| TCC authority | terminal/Hammerspoon | app/daemon/process | app default; other runtimes diagnostic |
| Permission diagnosis/mutation | preflight/manual | both available | status supported; mutation disabled |
| Apps/windows and focus/move/resize | partial | supported | supported; destructive operations governed |
| AX inspection and stable element targeting | custom | inspect UI/see/snapshots | supported; opaque IDs and lineage journaled |
| Action-first click/set-value/named action | custom AX | supported | supported; postcondition required |
| Coordinate click/buttons/count/modifiers | supported | supported | supported as last resort |
| Type/press/hotkey | supported | supported | supported; values redacted; secrets never replayed |
| Move/drag/scroll/swipe | partial | supported | supported; atomic gesture + state verification |
| Background process input | no stable contract | supported | supported; foreground explicit |
| Full/window/region screenshot and UI map/OCR | partial | supported | supported; evidence modes control retention |
| Menus/menubar | limited | supported | supported; observation vs activation policy |
| Dialog/Dock/Spaces | not first-class | supported | optional `extended` |
| Clipboard paste | limited | supported | optional `extended` + sensitive |
| Multi-step scenario | custom JSON | `.peekaboo.json` run | supported; partial failure result retained |
| Waits/postconditions | custom | action waits/scripts | supported by engine + skill assertion |
| JSON/debug diagnostics | supported | supported | versioned adapter envelope + debug mode |
| Execution journal | basic `session.jsonl` | script step result | adapter, always on |
| Guarded replay and defect review | no | whole-script rerun | adapter + skill judgment |
| Artifact transfer/cleanup | helper | no | adapter, 0700/0600 remote temp + audit |
| MCP stdio | no | supported | optional local/SSH proxy with tool profiles |
| MCP HTTP/SSE | no | stubs | unsupported |
| Browser DOM/CDP | separate tools | browser broker | disabled; no unpinned `@latest` |
| Dia DOM/page automation | no | not guaranteed | unsupported; native AX only |
| Natural-language agent / AI analysis | no | supported | disabled; calling agent owns planning |
| Shell / audio | no | available | disabled |
| Locked/logged-out desktop or TCC bypass | unsupported | GUI session required | unsupported |
| Secret/private-key entry | policy-gated | technically possible | explicit sensitive action; no value/screenshot/replay retention; acceptance creates no real credential |

Implementation publishes this as canonical
`docs/source/macos-agent-capability-matrix.md`, populated from the tested pin and
linked from the skill. Disabled/unsupported rows require negative assertions.

## Contract Delta

- **Retain:** one `macos-agent` dependency; local/SSH active GUI targets;
  AX-first plus bounded synthetic fallback; screenshots/input/scenarios;
  structured results, permission degradation, timeouts, and postconditions;
  local redacted evidence.
- **Change:** native behavior moves to pinned Peekaboo; old top-level
  `preflight/apps/windows/window/input/input-source/ax/observe/debug/wait/
  scenario/profile` grammar becomes the thin adapter plus `exec --`; the Python
  helper moves into the CLI; supported macOS floor becomes 15; every run gets a
  v2 journal.
- **Add:** supply-chain lock/install/doctor/capabilities/rollback; app-held TCC;
  native snapshots/background input/menu/dialog/Dock/Spaces/MCP/scripts;
  guarded replay, failure clustering, redaction report, improvement routing,
  and a visible reduced-security posture when the exact CLI notary waiver is
  exercised.
- **Remove:** released custom native backends, coordinate profiles, duplicate
  skill transport/evidence mechanics, and exit-zero-as-success claims.

## Test And Evidence Boundary

Each edited repo uses durable test-first evidence. Meaningful red precedes
production edits for command, lock, transport, journal, replay, redaction, and
skill contracts. Raw screenshots, AX values, host/user paths, credentials,
browser data, and typed private values stay in private local evidence. Tracked
and provider records contain only generic roles, versions/digests, counts,
sanitized signatures, and artifact hashes.

## Release And Cutover

1. Implement in an isolated nils-cli branch/worktree while production stays on
   the old installed binary.
2. Pass deterministic, provenance, private local/SSH live, privacy/security,
   specialist review, full CI, and install/rollback acceptance.
3. Obtain the explicit release-time consent required by the nils-cli release
   workflow, merge/release one nils-cli tag, and verify published assets.
4. In one runtime-kit PR, update skill, canonical matrix, generated products,
   goldens, `required_clis`, surface docs, and exact pin through
   `meta:nils-cli-bump`; remove the Python helper and old examples.
5. Merge, sync managed surfaces, install the backend on the private macOS role,
   and prove fresh Codex/Claude/Hermes discovery, a bounded desktop journey,
   journal review, and rollback readiness.

## Acceptance Criteria

- Adapter source contains no replacement native UI engine.
- Tag/commit/assets/SHA256/signing/version/architecture/capability probes verify
  and drift fails closed. App notarization remains a hard gate; CLI
  notarization is either `pass` or an explicit exact-artifact `waived` result
  and is never silently represented as passing.
- Local/SSH outputs and journals are equivalent and contain no host, user/home,
  key, secret, or raw remote command.
- Journals survive interruption and replay cannot cross secret, destructive,
  external, stale, or unknown-outcome boundaries. Conditional replay receives
  live acceptance only when the host can produce valid snapshot lineage;
  otherwise deterministic coverage and a recorded residual are sufficient.
- Seeded privacy, wrong-target, false-success, cleanup, drift, and repeated
  failures are identified and routed correctly.
- Every supported matrix row has deterministic or live evidence; every
  disabled/unsupported row has a negative test/capability ceiling.
- The private macOS role passes a repeatable local and controller-side SSH
  critical path: fresh AX observation, foreground action, synthetic background
  input, explicit postconditions, privacy-clean journaling, guarded no-replay,
  and rollback, without creating a real credential merely for testing.
- Displayless element-ID snapshot targeting is not claimed as supported. When
  the engine reports `display_count=0`, a fresh-observation coordinate fallback
  may satisfy the active-GUI canary only with an explicit postcondition; a
  future requirement for displayless element targeting triggers a separate
  controlled Peekaboo-fork decision, not an upstream scheduling dependency.
- Full nils-cli/runtime-kit validation and specialist review pass; the released
  nils tag is pinned; fresh sessions use the replacement.
- Old engine/helper sources and installed managed surfaces are absent after
  cutover; rollback uses the prior release, not an in-process fallback.

## Non-Goals

- Forking/vendoring Peekaboo for a capability that is not part of the current
  active-GUI contract, or reproducing its command grammar in Rust.
- Exposing Peekaboo AI, browser MCP, shell, audio, or permission mutation now.
- Unlocking/logging into a Mac, bypassing TCC, uploading telemetry, recording
  the whole desktop, retaining secrets, or filing every transient as an issue.

## Rollback

- Before release, discard the isolated backend/worktree; production is unchanged.
- Before runtime-kit cutover, keep the pin unchanged and supersede a bad release.
- After cutover, restore the previous nils-cli pin and run `backend rollback`,
  resync runtime-kit, then run doctor and a read-only smoke test.
- Privacy failures quarantine local evidence and require review; rollback never
  replays a non-idempotent action or restores leaked data.

## Execution

- Recommended plan: docs/plans/2026-07-15-peekaboo-macos-agent-migration/peekaboo-macos-agent-migration-plan.md
- Recommended execution state: docs/plans/2026-07-15-peekaboo-macos-agent-migration/peekaboo-macos-agent-migration-execution-state.md
