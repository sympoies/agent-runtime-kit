# Plan: Close the remaining Main Agent Mode blockers

- Source document: `docs/plans/2026-07-27-main-agent-mode-blockers/main-agent-mode-blockers-discussion-source.md`
- Date: 2026-07-27 (promoted to a plan bundle 2026-09-14)
- Tracking issue: not yet opened

## Why this is a plan and not an issue

The source is a 2044-line running inventory with a repair log, an execution
matrix, and per-item field-closure evidence for B1-B8, F25, F30, F36 and F37.
That volume is a plan bundle, not an issue body. It was written into
`docs/discussions/` and never left, so this promotion gives it the tracked home
it always needed. Opening the tracking issue is deferred to whoever picks the
work up, through `deliver-plan-tracking-issue`.

## Remaining scope

Everything below is quoted from the source's own execution matrix. Closed items
are explicitly out of scope and must not be re-run or re-used as evidence.

| Area | Status at promotion | Remaining acceptance |
| --- | --- | --- |
| C06 dependency wait | field-open; the dependency gate has deterministic integration coverage | Prove an intentional dependency wait, authenticated dependency delivery, and same-session continuation on both products |
| C07 account behavior | field-open | Codex: typed account-next binding and same-worker continuation without logout. Claude: clear unsupported behavior without damaging recovery |
| Residual C08 recovery | partly closed | Exercise the residual classifications the source enumerates, without reusing B2 or B3 evidence |
| Phase D parity | open | Repeat applicable A/B/C behavior on native Claude and disposition the remaining F-items |
| F34 | local topic candidate | Not integrated, installed, released, or field-closed; govern integration together with the runtime F47 consumer after final F47 acceptance |

## Non-scope

- B1-B8, F25, F30, F36 and F37 are field-closed. Do not re-open or re-prove.
- C01-C05 and C09 are closed on both products.
- The B2 claim-absent, claim-active-at-stage-1, and process-dead/tmux-live
  recovery forms are closed and must not be counted again toward C08.

## Execution boundaries

- The historical governed local-main authorization exercised for B2 is **not**
  standing authority. Any later delivery needs a fresh explicit user selection
  and must retain compare-and-swap, hooks, signing, and outside-repository
  receipts.
- Provider restart and resume canaries require explicit authority. Do not launch
  a canary merely to probe provider capacity.
- Prefer non-provider source and test work while provider capacity is unknown.

## Validation

- Local deterministic coverage may proceed for residual C08 classifications.
- Field closure for C06 and C07 requires real provider lanes on both products,
  which is gated on the authority and capacity notes above.
