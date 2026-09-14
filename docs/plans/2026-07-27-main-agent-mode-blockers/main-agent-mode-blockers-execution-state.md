# Execution State: Close the remaining Main Agent Mode blockers

## Execution State

- Source document: `docs/plans/2026-07-27-main-agent-mode-blockers/main-agent-mode-blockers-discussion-source.md`
- Plan: `docs/plans/2026-07-27-main-agent-mode-blockers/main-agent-mode-blockers-plan.md`
- Tracking issue: none yet — open through `deliver-plan-tracking-issue` when the
  work is picked up
- Status: open; not started as a tracked plan
- Current task: none
- Next task: C06 or the residual C08 deterministic coverage, whichever has
  authority first
- Blockers: C06 and C07 field closure need provider capacity and explicit
  account/provider authority
- Last updated: 2026-09-14

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | C06 dependency wait, field | open | deterministic integration coverage exists | Needs an intentional wait, authenticated delivery, and same-session continuation on both products |
| 1.2 | C07 account behavior, field | open | none | Needs explicit account/provider authority |
| 1.3 | Residual C08 recovery classifications | partly closed | B2/B3 forms closed and excluded | Local deterministic coverage may proceed without new authority |
| 1.4 | Phase D parity on native Claude | open | none | Prefer non-provider source/test work while capacity is unknown |
| 1.5 | F34 integration with the F47 consumer | open | signed nils-cli topic `26ed88f8`; local gate 7,898 tests green; specialist review clean | Local topic candidate only: not integrated, installed, released, or field-closed |

## Validation Log

- 2026-09-14: promoted from the main-agent-mode blocker-inventory capture
  during the docs/discussions lifecycle sweep. No scope was re-verified in this
  pass; every status above is carried over verbatim from the source's own
  execution matrix as of its 2026-08-01 update.

## Session Notes

- 2026-09-14: the capture had accumulated in `docs/discussions/` since
  2026-07-27 with no tracked home. It is a plan, not a discussion: B1-B8, F25,
  F30, F36 and F37 are field-closed inside it, and C06, C07, residual C08,
  Phase D and F34 remain. Promoting it preserves that state under
  `docs/plans/`, where the L2 lifecycle can retire it properly.
- The historical governed local-main authorization recorded in the source was
  exercised for B2 only and is not standing authority for any further delivery.
