# Execution State: Harden macOS desktop surface selection and rerunnable flows

<!-- plan-issue-record:v2 role=state profile=tracking -->
## Execution State

- Source document: `docs/plans/2026-08-26-macos-desktop-routing-hardening/macos-desktop-routing-hardening-plan.md`
- Tracking issue: <https://github.com/sympoies/agent-runtime-kit/issues/49>
- Current sprint: Sprint 4 stability, freshness, and delivery
- Status: in progress
- Current gate: merge PR #50 after the combined review outcome and the
  issue-side review checkpoint, then strict closeout
- Current task: 4.4
- Next task: none
- Plan branch: `feat/macos-desktop-routing-hardening`
- Backend: unchanged; Peekaboo `v4.2.2` behind `macos-agent` adapter v3, nils-cli
  floor `>= 1.27.3`
- Blockers: none
- Last updated: 2026-08-26
- Branch/commit/PR: <https://github.com/sympoies/agent-runtime-kit/pull/50> on
  `feat/macos-desktop-routing-hardening`; plan bundle `6922380`, implementation
  `1243989`, lock-ignore `082d7b7`, review repairs `6be6bbd`

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
| 1.1 | done | Declare the contract delta and capture meaningful red | computer-use.surface-routing-contract failed with skill_count=0 while the two pre-existing computer-use cases stayed green; test-first record holds the classification, contract delta, impact, and observed red | Probe must fail on the intended missing markers only |
| 2.1 | done | Add the deterministic-first surface selection ladder | Surface Selection ladder published in the source .tera and all three rendered products; rungs 1-3 declared outside the adapter with the shell hard-deny restated | Higher rungs run outside the adapter; shell hard-deny unchanged |
| 2.2 | done | Make the browser-test handoff reciprocal | Browser Claim Handoff section plus reciprocal paragraph in browser-test-routing.md; matrix Browser DOM/CDP row now names the browser-test route | Matrix names the route; skill claims no DOM capability |
| 3.1 | done | Add the AX-degeneracy gate and negative application classes | Accessibility Health Gate section plus Degenerate-AX application classes and Accessibility health gate matrix rows | Reuses the existing bounded coordinate fallback |
| 3.2 | done | Define the declarative flow fixture and its runner | references/flow-fixtures.md added with fixture shape, chained-exec runner, stability sampling, and privacy rules; renders byte-identical into codex, claude, and hermes | Runner is the existing chained exec shape, not a scenario runner |
| 4.1 | done | Add the stability convergence threshold | Acceptance Standard item 4 now requires at least three independent runs, a recorded postcondition success rate, and an unattended-safe classification | Repeated independent runs, never blind retry |
| 4.2 | done | Add the upstream backend freshness audit | Backend freshness audit matrix row plus a network-free mirror-agreement assertion across the matrix, nils-cli-pin.yaml, and nils-cli-surface.md | Deterministic and network-free mirror agreement |
| 4.3 | done | Validate, review, and merge the delivery | deterministic runtime-smoke suite exits 0 with all three computer-use cases passing; canonical gate rerun pending after commit; PR #50 delivered with --no-merge; testing, maintainability, and red-team lenses each found one defect; all three repaired at head 6be6bbd and the review-loop ledger closed with no open rows; canonical gate exits 0 across 17 positions on the repaired head | Canonical gate once against the final change |
| 4.4 | pending | Close the tracker and route archive maintenance | | Archive apply stays confirmation-gated |

## Validation Log

- 2026-08-26: Bundle authored on `feat/macos-desktop-routing-hardening` in a
  managed worktree. Backend freshness confirmed against the upstream releases
  API: Peekaboo `v4.2.2` published 2026-08-20 is the current latest, so the
  repository pin is current and no pin change enters this plan.
- 2026-08-26: Meaningful red captured before any production edit.
  `bash tests/runtime-smoke/run.sh --mode deterministic` exited 1 with
  `computer-use.surface-routing-contract status=fail skill_count=0`, while
  `computer-use.macos-desktop` and `computer-use.capability-contract` stayed
  `pass`, proving the failure came from the intended missing contract rather
  than setup or environment.
- 2026-08-26: After implementing Sprints 2-4 and refreshing the render goldens,
  the same deterministic command exits 0 and all three computer-use cases pass.
- 2026-08-26: `bash scripts/ci/all.sh` positions 1-5 passed on the uncommitted
  tree; position 6 correctly reported the refreshed-but-uncommitted goldens, so
  the canonical gate is rerun once against the committed change.
- 2026-08-26: Canonical gate exits 0 across all 17 positions on committed head
  `1243989`, and again on repaired head `6be6bbd`. Provider CI on the delivered
  branch reports success for both required lanes.
- 2026-08-26: Full review gate ran three lenses. `review-specialists scope`
  forced testing and maintainability and required red-team on a 1514-line diff.
  Each lens produced one finding: a lexicographic backend-version reduction that
  could pick the wrong release, a rendered-reference assertion that depended on
  case ordering, and a surface ladder that named caller-side surfaces without
  restating the Approval Boundary. All three were repaired in-branch and the
  review-loop ledger closed with no open rows.

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
