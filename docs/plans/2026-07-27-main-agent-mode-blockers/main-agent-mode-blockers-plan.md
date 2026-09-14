# Plan: Close the remaining Main Agent Mode blockers

## Overview

Close the Main Agent Mode items that the blocker inventory still lists as open:
C06 dependency wait, C07 account behavior, the residual C08 recovery
classifications, Phase D parity on native Claude, and F34's integration with the
runtime F47 consumer.

The source is a 2044-line running inventory with a repair log, an execution
matrix, and per-item field-closure evidence. That volume is a plan bundle, not
an issue body. It sat in `docs/discussions/` from 2026-07-27 with no tracked
home; this bundle gives it one.

## Read First

- Primary source:
  `docs/plans/2026-07-27-main-agent-mode-blockers/main-agent-mode-blockers-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Open questions carried into execution: whether the source's 2026-08-01 status
  still holds, since nothing was re-verified when the bundle was promoted
- Open questions carried into execution also include the run-wide closeout
  macro design, whose capture was retired on 2026-09-14; the shipped
  `main-agent closeout` behaviour is the reference for it.

## Scope

Only the items the source's own execution matrix still marks open:

| Area | Status at promotion | Remaining acceptance |
| --- | --- | --- |
| C06 dependency wait | field-open; deterministic integration coverage exists | An intentional dependency wait, authenticated dependency delivery, and same-session continuation on both products |
| C07 account behavior | field-open | Codex: typed account-next binding and same-worker continuation without logout. Claude: clear unsupported behavior without damaging recovery |
| Residual C08 recovery | partly closed | The residual classifications the source enumerates, without reusing B2 or B3 evidence |
| Phase D parity | open | Applicable A/B/C behavior on native Claude, and disposition of the remaining F-items |
| F34 | local topic candidate | Integration governed together with the runtime F47 consumer after final F47 acceptance |

Out of scope: B1-B8, F25, F30, F36 and F37 are field-closed; C01-C05 and C09 are
closed on both products. The B2 claim-absent, claim-active-at-stage-1, and
process-dead/tmux-live recovery forms must not be counted again toward C08.

## Assumptions

- The source's 2026-08-01 status is still accurate. Nothing was re-verified when
  the bundle was promoted on 2026-09-14.
- The historical governed local-main authorization exercised for B2 is not
  standing authority. Any delivery here needs a fresh explicit user selection and
  must retain compare-and-swap, hooks, signing, and outside-repository receipts.
- Provider restart and resume canaries need explicit authority. A canary is never
  launched merely to probe provider capacity.

## Sprint 1: Non-provider closure

Work that can proceed without provider capacity or account authority.

### Task 1.1: Exercise the residual C08 recovery classifications

- **Location**:
  - `tests/runtime-smoke/`
  - `core/policies/`
- **Description**: Cover the residual C08 recovery classifications the source
  enumerates with local deterministic coverage, without reusing B2 or B3
  evidence for any of them.
- **Dependencies**:
  - none
- **Complexity**: 5
- **Acceptance criteria**:
  - Every residual classification named in the source has its own deterministic
    case, and none of them cites B2 or B3 evidence.
  - The closed B2 forms — claim-absent, claim-active-at-stage-1, and
    process-dead/tmux-live — are not re-run.
- **Validation**:
  - `bash scripts/ci/all.sh`

### Task 1.2: Advance Phase D parity by source and test work

- **Location**:
  - `core/skills/conversation/main-agent-mode/`
  - `tests/runtime-smoke/`
- **Description**: Repeat the applicable A/B/C behavior on native Claude
  wherever it can be proven without a provider lane, and disposition the
  remaining F-items the source lists.
- **Dependencies**:
  - none
- **Complexity**: 5
- **Acceptance criteria**:
  - Each applicable A/B/C behavior is either proven on native Claude or recorded
    as provider-gated with the reason.
  - Every remaining F-item has an explicit disposition.
- **Validation**:
  - `bash scripts/ci/all.sh`

### Task 1.3: Prepare F34 for governed integration

- **Location**:
  - `core/policies/`
- **Description**: F34 is a signed local topic candidate that is not integrated,
  installed, released, or field-closed. Keep its exact proof, revision-floor,
  owner, outcome, expiry, replay, and registry-access fencing intact, and stage
  it to land with the runtime F47 consumer rather than on its own.
- **Dependencies**:
  - none
- **Complexity**: 3
- **Acceptance criteria**:
  - F34's fencing is unchanged and its topic proof still verifies.
  - The integration is staged against F47 rather than delivered alone.
- **Validation**:
  - `bash scripts/ci/all.sh`

## Sprint 2: Provider-gated field closure

Blocked until provider capacity and account authority are available.

### Task 2.1: Close C06 in the field

- **Location**:
  - `core/skills/conversation/main-agent-mode/`
- **Description**: Prove an intentional dependency wait, authenticated
  dependency delivery, and same-session continuation on both products.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 8
- **Acceptance criteria**:
  - A dependency wait is entered intentionally, its delivery is authenticated,
    and the same session continues afterwards on both products.
  - No canary is launched merely to probe provider capacity.
- **Validation**:
  - Field evidence from a real provider lane on both products.

### Task 2.2: Close C07 in the field

- **Location**:
  - `core/skills/conversation/main-agent-mode/`
- **Description**: On Codex, prove typed account-next binding and same-worker
  continuation without logout. On Claude, prove clear unsupported behavior that
  does not damage recovery.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Codex binds account-next with a typed result and the same worker continues
    without a logout.
  - Claude reports the unsupported behavior clearly and recovery is undamaged.
  - Explicit account and provider authority was obtained first.
- **Validation**:
  - Field evidence from a real provider lane on both products.

### Task 2.3: Integrate F34 with the F47 consumer

- **Location**:
  - `core/policies/`
- **Description**: After final F47 acceptance, govern the F34 topic and the
  runtime F47 consumer together through one integration.
- **Dependencies**:
  - Task 1.3
- **Complexity**: 5
- **Acceptance criteria**:
  - F34 and F47 land through a single governed integration with F34's fencing
    retained.
  - A fresh explicit user selection authorized the delivery; the historical B2
    local-main authorization is not reused.
- **Validation**:
  - `bash scripts/ci/all.sh`

## Testing Strategy

Local deterministic coverage carries Sprint 1. Sprint 2 requires real provider
lanes on both products, so its acceptance is field evidence rather than a suite.
Prefer non-provider source and test work while provider capacity is unknown.

## Risks & gotchas

- Re-proving a closed item wastes a provider lane and pollutes the evidence
  record. Check the source's closed list before starting anything.
- B3 evidence must not be counted as B2 evidence, and neither may be counted
  toward residual C08.

## Rollback plan

Nothing here mutates a shipped surface on its own; each task lands through its
own reviewed delivery and rolls back with that delivery.
