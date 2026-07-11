# Implementation Source: Agent capability convergence

## Status

- Status: ready for L3 dispatch execution
- Date: 2026-07-11
- Source issue: <https://github.com/graysurf/agent-runtime-kit/issues/562>
- Dependency: issue #561 completed through PR #565 and nils-cli v1.21.15

## Problem

The runtime currently exposes agent bookkeeping, lifecycle mechanics, and thin
CLI wrappers beside user-facing outcome skills. Users should be able to ask for
an outcome such as implementing a change, reviewing a PR, testing a browser, or
operating a desktop without selecting evidence-record or workflow-substep skill
names.

Issue #561 supplied the machine-auditable exposure and disposition contract but
intentionally left all 66 baseline skill rows pending. Issue #562 must now apply
that contract: move judgment to policy, task procedures to selectively loaded
intent documents, observable enforcement to hooks or provider gates, and
deterministic mechanics to nils-cli. Only reviewed user outcomes should remain
in normal skill discovery.

The requested completion boundary also includes runtime activation. The work is
not complete merely because source and tests pass: fresh Codex CLI and Claude
Code sessions on the remote agent environment must be able to use the converged
runtime against a macOS GUI target. Public source and provider records remain
portable and must not contain private host names, addresses, user names,
credentials, or machine-local paths.

## Inputs And Evidence

- [U1] The user requested complete convergence and required four lanes:
  disposition, Browser/Evidence migration, remaining-skill convergence, and
  dual-machine deployment acceptance.
- [U2] The user requires future sessions in both environments to use all
  delivered capabilities, not merely a design or inventory.
- [U3] `agent-runtime-kit` is public; personal environment details and private
  machine information must not be committed or posted to public provider
  records.
- [F1] `manifests/skill-dispositions.yaml` freezes the 66 baseline IDs, order,
  count, and digest, with every row currently `pending`.
- [F2] `manifests/skills.yaml` exposes the same pending set as visible migration
  debt and requires reviewed active skills to carry complete invocation and
  default-exposure metadata.
- [F3] The #561 handoff requires replacement behavior before source removal,
  uses `agent-runtime list-skills --product ... --format json` as product truth,
  and disallows an `advanced` exposure until a real cross-product opt-in
  mechanism exists.
- [F4] `DEVELOPMENT.md` defines render, install, prune, sync, doctor, product
  smoke, and full validation paths for the managed runtime.
- [I1] The migration lanes must not independently edit the shared manifest and
  generated surfaces. A single disposition/integration owner must apply final
  retirement after both replacement lanes land, or parallel work will create
  avoidable conflicts and can remove skills before their replacements exist.
- [I2] Live dual-machine acceptance must run only from merged, released or
  otherwise pinned source on `main`; activating a temporary plan branch would
  make future-session evidence misleading.

## Resolved Architecture

### User interface

- Natural-language requests are the default interface.
- Retained skills represent distinct user outcomes with explicit invocation
  metadata and `exposure.profile: default`.
- Agent-only workflow steps are not retained as hidden or pseudo-advanced
  skills.

### Runtime layering

1. `AGENT_HOME.md` carries only concise always-on invariants and routing.
2. Product-neutral policy documents own durable judgment and safety rules.
3. `agent-docs` intents selectively load task procedures.
4. Hooks and released provider gates enforce only mechanically observable
   requirements.
5. nils-cli owns schemas, state transitions, evidence records, redaction,
   verification, installation, and runtime diagnostics.
6. Product adapters isolate protocol-specific activation without changing the
   shared contract.

### Migration sequencing

1. Decide all 66 disposition rows. Commit reviewed metadata immediately only
   where the active surface can remain truthful; rows waiting for replacement
   stay pending until the atomic retirement pass rather than receiving a false
   default exposure. The dispatch task packet is temporary execution context,
   not a second durable inventory.
2. Land Browser/Evidence and remaining-family replacement behavior while old
   skills remain available.
3. Apply retirement, compatibility, manifest, render, golden, install, and
   stale-prune changes in one integration-owned pass.
4. Merge the plan branch to `main`, synchronize managed runtime surfaces, and
   prove fresh-session behavior on both products and both runtime roles.

## Four Dispatch Lanes

### Lane A — Disposition and retirement integration

Own all 66 disposition decisions and the shared manifest/render retirement
pass. The first pass may leave rows pending when their replacement is not yet
live, because active reviewed rows require truthful default exposure. This lane
is the only lane allowed to mutate
`manifests/skill-dispositions.yaml`, `manifests/skills.yaml`, shared render
goldens, or final active-surface expectations. It runs twice: first for reviewed
decisions, then after replacement lanes land for source retirement and cleanup.

### Lane B — Browser/Evidence migration

Move Browser and Evidence judgment and procedures into policy and selective
intent documents, add observable hook/gate enforcement, retain nils-cli record
mechanics, and prove parent workflows create and verify evidence without the
user naming bookkeeping skills. This lane lands replacement behavior but does
not remove skill sources or mutate the shared manifests.

### Lane C — Remaining skill convergence

Apply the same placement model to Meta, Conversation execution modes, Code
Review, Issue, PR, Dispatch, and any bookkeeping inside Media, Reporting, and
Computer Use. Retain real user outcomes and rehome lifecycle internals. This
lane lands replacement behavior but leaves shared retirement to Lane A.

### Lane D — Portable and private deployment acceptance

Add portable acceptance coverage for render/install/prune/sync/doctor and
fresh-session routing. After the integration PR reaches `main`, activate the
managed surfaces on the remote agent host and macOS GUI target, then run Codex
CLI and Claude Code session tests. Public evidence reports only generic roles,
versions, pass/fail status, redacted artifact classes, and provider links;
machine-specific details remain in private local evidence.

## Acceptance Criteria

- Every frozen disposition row is `reviewed` or `retired`; the pending set is
  empty and the original 66 IDs/order/count/digest remain unchanged.
- No normal-discovery skill exists solely for bookkeeping, a one-command CLI
  wrapper, or an agent lifecycle substep.
- Retained active skills map to direct user outcomes and carry complete
  invocation/default-exposure metadata.
- Browser/Evidence behavior is automatically routed through parent intents and
  workflows without losing ordering, schemas, redaction, verification, or
  direct CLI diagnostics.
- Detailed procedures load only for selected intents; unrelated sessions do
  not receive every runbook.
- Test-first, docs-impact, review evidence, delivery, and closeout requirements
  are enforced at observable boundaries without hooks inventing semantic
  judgment.
- Codex, Claude, and Hermes render, governance, drift, install, runtime-smoke,
  and stale-prune checks pass against equivalent intent and exposure rules.
- Any required nils-cli change is merged, released, installed, and pinned before
  runtime-kit consumes it.
- After the integration PR merges, fresh Codex CLI and Claude Code sessions on
  the remote agent role can use the converged entrypoints and operate the macOS
  GUI role with retained screenshot/session/validation evidence.
- A restart-safe read-back proves the installed surfaces come from the merged
  revision and retired skills are absent from live managed homes.
- Public tracked files, issues, PRs, and comments contain no private host,
  account, connection, credential, or absolute machine-path information.

## Non-Goals

- One universal skill containing every workflow.
- Removing direct nils-cli diagnostics.
- Reimplementing released nils-cli behavior in repository shell or Python.
- Treating hooks as the source of semantic engineering judgment.
- Publishing private runtime configuration or live-machine evidence.
- Claiming desktop automation support when only static HTTP or source-level
  tests ran.

## Rollback

- Replacement behavior lands before retirement, so a failed convergence slice
  can retain the existing skills while the replacement is corrected.
- Runtime activation is dry-run first and ownership-safe; rollback restores the
  previous merged runtime-kit revision, rerenders, reinstalls, and runs stale
  prune plus doctor.
- Private host state is never committed. A failed live test records a redacted
  blocker and leaves the dispatch issue open rather than weakening public
  acceptance.

## Execution

- Recommended plan: docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-plan.md
- Recommended execution state: docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-execution-state.md
