# Execution State: Align deliver-plan-tracking-issue to deliver-pr's native bot code review

## Execution State

- Source document: docs/plans/2026-07-01-plan-tracking-native-review-gate/2026-07-01-plan-tracking-native-review-gate-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/491>
- Current sprint: Sprint 2 (complete)
- Status: complete; shipped into the tracking skill
- Branch: feat/plan-tracking-native-review-gate
- Last updated: 2026-09-14

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Update the Contract (floor, prereqs, references, policy) | done | commit b4adf4d4 | forge-cli 1.17.0 + review-specialists; references gate + posting contract; single-author exception removed |
| 1.2 | Rewrite the Entrypoint + Workflow PR/Review steps to Shape 1 | done | commit b4adf4d4 | pr deliver --no-merge -> gate -> pr review --submit-review -> sweeps -> review checkpoint -> pr merge; adapted from review-dispatch-lane-pr |
| 1.3 | Render three products + refresh goldens | done | commit b4adf4d4 | rendered on-pin v1.20.1; golden diff scoped to the 3 tracking goldens; git diff --exit-code clean |
| 2.1 | Bump the deliver-dispatch-plan forge-cli floor | done | commit 6e7350ba | 1.17.0; behavior unchanged; 3 dispatch goldens refreshed on-pin |
| 2.2 | Full declared validation | in-progress | on-pin substitute: governance OK, audit-drift clean, dispatch runtime-smoke pass, hooks 91 OK | full scripts/ci/all.sh blocked until host agent-runtime is on-pin (v1.20.1); host is 1.20.5 |
| 2.3 | Testbed live review-event round trip | done (core) | plan-tracking-testbed PR #77 (closed): 2 native review events — COMMENTED by review-testing-bot[bot], APPROVED by dobi-bot[bot] | Native-event mechanism confirmed (the exact gap #1000 had). Full native-URL -> close-ready round trip + record-audit ordering deferred to #491 real closeout (opaque URL, low-risk; Shape 1 does not depend on the audit-ordering answer) |

## Validation Log

- 2026-07-01: bundle authored from the deliver-plan-tracking-issue vs deliver-pr feasibility discussion (trigger: sympoies/nils-cli#1000 had no native review event). Decisions locked: Shape 1, single-author always runs the full gate, dispatch-family consistency in scope.
- 2026-07-01: on-pin substitute validation via `scripts/dev/with-nils-version.sh release:v1.20.1` (host is 1.20.5, off-pin) — `skill-governance-audit.sh` repo OK (desc 237/240); `agent-runtime render --product {codex,claude,hermes}` succeeded; golden refresh scoped to exactly the 6 expected files; `git diff --exit-code -- tests/golden/` clean; `audit-drift` clean (20 findings, all documented); `runtime-smoke --mode deterministic --domain dispatch` all pass incl. `dispatch.deliver-plan-tracking-issue`; `tests/hooks/run.sh` 91 tests OK.
- 2026-07-01: PR #492 opened on graysurf/agent-runtime-kit (Refs #491). Full `scripts/ci/all.sh` positions 1-15 ran green on-pin in the pre-push gate (pushed under `with-nils-version.sh release:v1.20.1`); remote CI re-runs it on-pin. test-first waiver record verified and accepted by the create-time gate.
- 2026-07-01: Task 2.3 testbed run on graysurf/plan-tracking-testbed PR #77 (chore probe, now closed, branch deleted). `forge-cli pr review --submit-review` produced 2 native review events: `COMMENTED` (review-testing-bot[bot]) + `APPROVED` (dobi-bot[bot]) — confirming the native-event behavior #1000 lacked. The native-URL -> `tracking run update --review-outcome-comment` -> `close-ready` round trip and the `record audit` pre-merge ordering are deferred to #491's real closeout (opaque-URL evidence, low-risk; Shape 1 is independent of the audit-ordering answer).
- 2026-07-01: full `scripts/ci/all.sh` local run — Position 2 version-alignment fails closed on the off-pin host (1.20.5 vs pin v1.20.1) unless run under the pinned-binary PATH; the on-pin pre-push run is the authoritative local pass. Deferred to Task 2.2 once the host is on-pin (or the pin is bumped to the released line via meta:nils-cli-bump — a separate decision). Test-first waiver: skill-contract (orchestration prose) change; mechanical validation is render-golden + governance (done on-pin); behavioral validation is the deferred Task 2.3 testbed live run.

## Session Notes

- 2026-07-01: Confirmed no CLI capability gap — pin `v1.20.1` / `forge-cli 1.17.0` already exposes every surface `deliver-pr` uses; `review-dispatch-lane-pr` is the proven native-review template. Shape 1 chosen because it sidesteps `deliver-pr`'s pre-merge linked-issue audit ordering tension (`forge-cli pr merge` only fails closed on unresolved threads / unchecked tasks, not on the lifecycle audit).
- 2026-07-01: Host toolchain observed off-pin at authoring time (`agent-runtime 1.20.5`, `plan-tooling 1.20.3` vs pin `v1.20.1`); must be brought on-pin before the position-2 version-alignment gate in `scripts/ci/all.sh`. All on-pin content gates were run via the `with-nils-version.sh release:v1.20.1` wrapper.
- 2026-07-01: Sprint 1 (1.1-1.3) + Task 2.1 implemented on branch `feat/plan-tracking-native-review-gate` in two commits (b4adf4d4 tracking review gate; 6e7350ba dispatch floor bump). Next: bring host on-pin for the full gate (Task 2.2), then the testbed live run (Task 2.3), then PR delivery through the newly-aligned deliver-plan-tracking-issue itself.

## Closeout

- 2026-09-14: reconciled during the plan-archive sweep. The tracking issue
  `graysurf/agent-runtime-kit#491` and PR #492 are unrecoverable — that
  repository was retired and the project was re-created as
  `sympoies/agent-runtime-kit` with restarted issue numbering, so no provider
  closeout record can be read back. Completion is established from the shipped
  tree instead:
  `core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera` now carries
  the Shape 1 flow this plan specified — `forge-cli pr deliver --no-merge`,
  then the review gate, then `forge-cli pr merge` — together with the
  `review-specialists` floor and the review-outcome posting contract.
- Task 2.2 (full `scripts/ci/all.sh` on-pin) was blocked at authoring time only
  by an off-pin host; the on-pin pre-push gate recorded in the Validation Log
  is the authoritative pass, and the pin has since moved on many times.
- Task 2.3 shipped its core outcome (native review events confirmed on the
  testbed). The deferred native-URL round trip and record-audit ordering were
  explicitly scoped out of this plan and were not blockers for Shape 1.
