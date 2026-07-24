# Main Agent Mode Simplification Followups

## Status

- Status: open
- First observed: 2026-07-23
- Area: cli
- Severity: medium

## Signal

Local tracker (GitHub unavailable — 403 on the write path, so provider issues
cannot be opened) for the flow-improvement backlog surfaced by the main-agent-mode
simplified-flow acceptance run (2026-07-24, baseline `v1.25.9-39-g662b5479`). Full
analysis + rationale: `docs/discussions/2026-07-23-main-agent-mode-simplification-acceptance-test-plan.md`
Part F. Each item is fixed locally and checked off here; the entry is promoted
when the backlog is drained.

## Evidence

- Raw record: not captured (manual diagnosis from the acceptance run, 2026-07-24)
- Correctness itself PASSED (auto 721/0, `ci/all.sh` 1-17 OK); these are
  smoothness/ergonomics/diagnosability gaps, not correctness defects.

## Impact

Future operators hit avoidable friction (opaque errors, undiscoverable packet
schema, silent version skew) and Part C stays manually-tested unless these land.

## Backlog (fix locally; check off as done)

Owner legend: **NC** = nils-cli (Rust binary), **RK** = agent-runtime-kit
(hooks/tests/sync).

- [x] **PARTC** (NC) — hermetic `worker start --await-ready` e2e test (typed
  `readiness_failed` + `safe_state`) plus a `readiness_from_state` unit test.
  **High.** **LANDED** on nils-cli `main` at `48f57047` (2026-07-24). Confirmed F5
  already met: `readiness_failed` carries `assignment_state` + actionable
  `safe_state`.
- [x] **F2** (NC) — `coordination-unauthorized` now carries a remedy `hint`
  naming the missing precondition. **High.** Added an optional `hint` to
  agent-session `CliError` + wired it through both binaries' `render_error`
  (mirrors git-cli). **Authored + validated** (worktree `chore/main-agent-ergonomics-followups`,
  full agent-session suite green: 579 unit + 150 integration, 0 failed). Delivered via
  `deliver-nils-cli-ergonomics.sh`.
- [x] **F4** (NC) — added `main-agent packet-schema` (prints an example objective
  packet naming both nested `schema_version` constants) and made schema-mismatch
  errors name the expected `schema_version` and hint back at `packet-schema`.
  **High.** Authored + validated; delivered via the script.
- [x] **F7-doctor** (NC) — `activity doctor` now surfaces the running binary
  version (`binary_version`, git-describe form) so a stale/split install is
  diagnosable against source. **High.** Authored + validated; delivered via the
  script. **Remaining (RK):** a sync-time skew guard — still open below.
- [x] **F1** (NC) — `quick` defaults `--idempotency-key` from a digest of the
  assignment packet, so the fast-path needs only `--assignment-file`; an explicit
  key still wins. **Med.** Authored + validated; delivered via the script.
- [x] **F3** (NC) — `worker start` (and all) parse-errors now name the actual
  missing argument (pulled from clap's structured context) instead of an unnamed
  "required arguments were not provided" line. **Med.** Delivered via the script.
- [ ] **F6** (RK) — hook↔binary argv coupling has no binding contract test; add
  one asserting the `quick`/`rebind` allowlist matches the binary's argv. **Med.**
  Runtime-kit-local; still open.
- [ ] **F7-sync** (RK) — sync-time guard that the installed nils-cli binaries are
  not older than the paired runtime-kit policy/protocol. **High.** Runtime-kit-local;
  still open. (NC-side visibility shipped as F7-doctor above.)
- [x] **F8** (NC) — `activity doctor` gains an explicit `can_launch_worker` signal
  (`classification == "supported" && configured`), distinct from the
  config-presence `configured` axis, with clarified field docs. **Low.** Delivered
  via the script.

## Current Workaround

Operate with the friction (reverse-engineer errors, hand-author packets, re-run
install on skew). None are correctness-blocking.

## Promotion Criteria

Promote when the backlog above is drained (all High + Med landed and validated on
local `main` of the owning repo), with each fix's commit linked here. F8 (L2/Low)
may be split to a follow-up if it needs design.

## Blocker (2026-07-24) — nils-cli checkout contended — RESOLVED (workaround)

nils-cli `main` is continuously developed by another session (codex-cli
execution-capsule work; the tree is rarely clean), and with GitHub 403 the
agent-side commit paths fail closed: `semantic-commit local-default` needs a
clean tree, and worktree/branch commits need a resolvable remote default.
**Resolved** by (a) authoring + validating every nils-cli fix in an isolated
managed worktree (`chore/main-agent-ergonomics-followups`, base `48f57047`) so
the shared checkout is never touched, and (b) delivering through a user-run
script that commits ONLY the owned files with `git commit --only -- <paths>` —
so the other agent's staged/dirty work can never be swept in (as happened once
with PARTC's `48f57047`, which incidentally captured a codex-cli snapshot).

## Next Action

1. **nils-cli side (DONE, pending user run):** run
   `scratchpad/deliver-nils-cli-ergonomics.sh` (optionally `--install`) to land
   the F1/F2/F3/F4/F7-doctor/F8 batch on nils-cli `main` from
   `scratchpad/nils-cli-ergonomics-followups.patch` (6 agent-session files,
   +379/-14). PARTC already landed at `48f57047`.
2. **runtime-kit side (open):** F6 (hook↔binary argv contract test) and F7-sync
   (install-time skew guard) are runtime-kit-local and still to be authored.
   Update checkboxes + link commits as each lands; promote/archive this entry
   when F6 + F7-sync are drained.
