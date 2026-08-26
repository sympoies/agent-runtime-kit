# Execution State: Harden macOS desktop surface selection and rerunnable flows

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-08-26-macos-desktop-routing-hardening/macos-desktop-routing-hardening-plan.md`
- Tracking issue: pending open
- Current sprint: Sprint 1 contract freeze and red baseline
- Status: in progress
- Current gate: capture meaningful red in the computer-use smoke probe before
  any production `.tera` edit
- Current task: 1.1
- Next task: 2.1
- Plan branch: `feat/macos-desktop-routing-hardening`
- Backend: unchanged; Peekaboo `v4.2.2` behind `macos-agent` adapter v3, nils-cli
  floor `>= 1.27.3`
- Blockers: none
- Last updated: 2026-08-26
- Branch/commit/PR: pending

## Validation Plan

- Per task: update this ledger with command and evidence paths, pass, fail, or
  waiver, provider links, and residual gaps before advancing.
- Focused floor: `bash tests/runtime-smoke/run.sh --mode deterministic` plus the
  affected `agent-runtime render --product <target>` calls.
- Canonical floor: `bash scripts/ci/all.sh` run exactly once against the final
  change, including render, golden refresh, drift, smoke, and hook layers.
- Delivery floor: verified test-first evidence, provider current-head checks,
  full specialist review with at least testing and maintainability lenses, zero
  unresolved review threads and tasks, and a merged PR.
- Closeout floor: strict `close-ready --expect-visible`, provider read-back,
  visible closeout audit, and dry-run-first archive routing.

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | pending | Declare the contract delta and capture meaningful red | | Probe must fail on the intended missing markers only |
| 2.1 | pending | Add the deterministic-first surface selection ladder | | Higher rungs run outside the adapter; shell hard-deny unchanged |
| 2.2 | pending | Make the browser-test handoff reciprocal | | Matrix names the route; skill claims no DOM capability |
| 3.1 | pending | Add the AX-degeneracy gate and negative application classes | | Reuses the existing bounded coordinate fallback |
| 3.2 | pending | Define the declarative flow fixture and its runner | | Runner is the existing chained exec shape, not a scenario runner |
| 4.1 | pending | Add the stability convergence threshold | | Repeated independent runs, never blind retry |
| 4.2 | pending | Add the upstream backend freshness audit | | Deterministic and network-free mirror agreement |
| 4.3 | pending | Validate, review, and merge the delivery | | Canonical gate once against the final change |
| 4.4 | pending | Close the tracker and route archive maintenance | | Archive apply stays confirmation-gated |

## Validation Log

- 2026-08-26: Bundle authored on `feat/macos-desktop-routing-hardening` in a
  managed worktree. Backend freshness confirmed against the upstream releases
  API: Peekaboo `v4.2.2` published 2026-08-20 is the current latest, so the
  repository pin is current and no pin change enters this plan.

## Session Notes

- The maintainer reviewed alternatives to Peekaboo and chose to keep it.
  `cua-driver` remains an optional future second backend and is out of scope
  here; its dependency on a private SkyLight API, pre-1.0 status, default-on
  telemetry, and absent postcondition concept are the recorded reasons it is
  not adopted as a sole backend.
- The `lume` macOS VM fixture is deferred as a separate environment decision.
  It remains the strongest reason to touch the cua ecosystem later, because it
  would convert the `Locked/logged-out desktop` limitation into a configuration
  choice without adopting the private-API input path.
- `core/policies/browser-test-routing.md` already existed and already routed
  native and cross-application claims to the desktop skill. Only the reverse
  direction was missing, so this plan adds the reciprocal pointer rather than a
  new browser route.

## Handoff

- Nothing is handed off yet. On completion this bundle is routed through
  `plan-archive discover` and a dry-run `plan-archive migrate`, with apply
  gated on explicit confirmation.
