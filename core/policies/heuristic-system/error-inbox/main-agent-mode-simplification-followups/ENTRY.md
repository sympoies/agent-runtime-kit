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

- [ ] **PARTC** (NC) — Add a hermetic `worker start --await-ready` e2e test
  (typed `ready` + `readiness_failed`+`safe_state`) and a full
  `quick → ready → accept → retire` lifecycle test via the seed-broker /
  fake-tmux harness. Converts Part C from manual to auto; subsumes F5. **High.**
- [ ] **F2** (NC) — `coordination-unauthorized` returns no remedy `hint`; add one
  naming the missing precondition (mirror `git-cli worktree remove`'s hint). **High.**
- [ ] **F4** (NC) — objective-packet schema undiscoverable; add
  `init --print-packet-schema` (or example) and make the first validation error
  name the expected `schema_version`. **High.**
- [ ] **F7** (NC doctor + RK sync) — no guard against a split/stale install
  (this session's root cause: `main-agent`@b6abfa35 vs source@a8b83732,
  `agent-docs` missing); add a doctor check for mutually-consistent nils-cli
  binaries not older than the paired runtime-kit policy/protocol. **High.**
- [ ] **F1** (NC) — `quick` needs both `--assignment-file` and
  `--idempotency-key`; default the key from the packet digest → one required arg. **Med.**
- [ ] **F3** (NC) — `worker start` parse-error lists an empty required-arg set;
  name the missing arguments in the JSON error envelope. **Med.**
- [ ] **F6** (RK + NC) — hook↔binary argv coupling has no binding contract test;
  add one asserting the `quick`/`rebind` allowlist matches the binary's argv. **Med.**
- [ ] **F8** (NC) — `activity doctor` `configured:false` semantics ambiguous for
  worker-launch readiness; clarify or add a `can-launch-worker` signal. **Low / L2.**

## Current Workaround

Operate with the friction (reverse-engineer errors, hand-author packets, re-run
install on skew). None are correctness-blocking.

## Promotion Criteria

Promote when the backlog above is drained (all High + Med landed and validated on
local `main` of the owning repo), with each fix's commit linked here. F8 (L2/Low)
may be split to a follow-up if it needs design.

## Next Action

Fix in priority order: PARTC → F2 → F4 → F7 → F1 → F3 → F6 → F8. nils-cli fixes
land on nils-cli local `main` (target-rooted `semantic-commit local-default`);
runtime-kit fixes land here. Update the checkboxes and link commits as each lands.
