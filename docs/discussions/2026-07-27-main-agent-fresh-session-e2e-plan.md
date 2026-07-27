# Main Agent Fresh-session E2E Plan

Status: ready for execution  
Date: 2026-07-27  
Products: Codex and Claude Code  
Delivery mode: local main, local build/install, local runtime-surface deploy

## Purpose

Prove the locally delivered nils-cli and agent-runtime-kit surfaces from clean
new sessions. The test must verify both expected success paths and hook/authority
denials, while retaining enough evidence and improvement notes to make a fix and
rerun straightforward.

## Preconditions

- Both repositories have one verified signed local `main` delivery commit.
- Neither repository has been pushed.
- nils-cli `1.25.11` release-default binaries are built and installed locally.
- Runtime surfaces were previewed and applied from the local runtime-kit source
  with `--no-pull`.
- `agent-session activity doctor` reports supported executable helpers for
  Codex and Claude.
- Primary repositories are clean before scenario fixtures are created.
- Test repositories and receipts live outside the primary repositories.

Record before testing:

- nils-cli local-main SHA
- runtime-kit local-main SHA
- installed `semantic-commit`, `agent-session`, `main-agent`, `agent-hook`, and
  `forge-cli` versions
- Codex and Claude Code versions
- runtime-surface source digest or deploy evidence

## Isolation And Safety

- Create fresh managed Codex and Claude sessions; do not reuse the development
  workers.
- Use disposable repositories and managed worktrees under an isolated test run
  directory.
- Never use a real provider mutation, remote push, PR, issue, release, or
  GitHub Actions workflow.
- Never disable hooks, signing, coordination, protected-branch behavior, or
  checkout guards.
- Serialize default-branch mutation scenarios and assert exact HEAD immediately
  before and after them.
- A scenario may fail without stopping the rest of the matrix unless it exposes
  a blocking authority or data-integrity defect.

## Evidence Record

For every scenario record:

| Field | Required value |
| --- | --- |
| Scenario | Stable ID below |
| Product | Codex or Claude |
| Session | Session ID and incarnation |
| Versions | Product and nils-cli versions |
| Preconditions | Relevant repo HEAD, branch, worktree, claim, and hook state |
| Action | Exact redacted command or high-level operation |
| Expected | Expected state, exit class, and mutation boundary |
| Actual | Observed typed result |
| Verdict | pass, blocking-fail, or follow-up |
| Improvement | Concrete usability, automation, diagnostic, or performance note |
| Rerun | Smallest command or scenario selector that reproduces it |

Do not retain terminal transcripts, prompts, secrets, or raw credentials.

## Phase A — Installed Surface

### E2E-A01 — Version and doctor

For each product:

- Read installed CLI versions.
- Run `agent-session activity doctor --agent <product> --format json`.
- Require one supported provider record and an executable helper.
- Run `agent-hook doctor` through the deployed surface.

### E2E-A02 — Command replacement

- `semantic-commit default-branch --help` succeeds.
- `semantic-commit local-default --help` is an unknown subcommand.
- Bash and Zsh completion expose `default-branch` and contain no active
  `local-default` command or flags.
- `forge-cli` uses the default-branch receipt contract.

### E2E-A03 — Deployment convergence

- Run runtime-surface sync without `--apply`.
- Require a converged/no-change preview for Codex and Claude.
- Run drift/doctor checks for both products.

## Phase B — Hook And Commit Matrix

Run the same matrix from a fresh Codex session and a fresh Claude session
against separate disposable repositories.

### E2E-B01 — Ordinary default-branch commit remains blocked

- Prepare one staged change on the disposable primary default branch.
- Attempt the ordinary commit path.
- Require hook denial with an actionable owner message.
- Require unchanged HEAD and staged content preserved.

### E2E-B02 — `default-branch` dry-run is admitted

- Run the exact supported `semantic-commit default-branch` dry-run as one bare
  tool call with an absolute `--repo`, the exact `--expect-head`, `--dry-run`,
  and a body-valid message. `--receipt-out` is forbidden with `--dry-run`, so
  the dry-run names no receipt destination.
- Require a `cli.semantic-commit.default-branch.preview.v1` envelope with
  `ok:true`, `network_observed:false`, and no mutation.
- Do not compose the call with `cd`, a pipe, or a redirect: the default-delivery
  hook parses the surrounding shell text as CLI arguments and denies it.

### E2E-B03 — One signed local default-branch commit

- Reconfirm exact HEAD and clean unstaged/untracked state.
- Execute the authorized command once.
- Require one signed child commit, unchanged parent identity, and a valid final
  receipt outside the repository.
- Require no remote contact or push.

### E2E-B04 — Reuse and legacy rejection

- A second attempt from the already-ahead default branch fails before mutation.
- `local-default` remains unknown.
- Removed flags remain unknown.

### E2E-B05 — Feature worktree remains normal

- Create a managed feature worktree with `git-cli worktree`.
- Commit through ordinary `semantic-commit`.
- Require hook admission, signed commit, and no default-branch exception
  receipt.

## Phase C — Main Agent Lifecycle

### E2E-C01 — Fresh activation

- Start a new managed main session.
- Run version and doctor gates.
- Initialize one private objective packet.
- Require authenticated `main-agent self show` and `rehydrate` with
  `rebind_required=false`.

### E2E-C02 — Worker startup

- Start one bounded worker through `main-agent worker start --await-ready`.
- Require exact session/incarnation/cwd/enforce identity and authenticated
  checkpoint proof.
- If submit-key recovery is needed, require exactly one runtime-owned Enter and
  no prompt replay.

### E2E-C03 — Supervision and claims

- Observe working progress through `worker supervise`.
- Require active broker-owned claim, fresh edit authority, zero uncertain
  operations, and a useful typed next action.
- Allow automatic claim renewal without Main Agent ceremony.

### E2E-C04 — Authenticated mailbox

- Send one private worker message.
- Require authenticated sender, exact recipient, worker consumption, and no
  prompt or body exposure in public projections.

### E2E-C05 — Request changes and automatic same-session resume

- Submit a bounded candidate.
- Request one deterministic revision.
- Require the exact existing worker to resume automatically, reacquire any
  required claim, consume guidance, and continue.
- Fail if manual Enter, prompt replay, logout, account switch, restart, new
  worker, or worktree replacement is required.

### E2E-C06 — Dependency wait

- Put the worker behind an explicit accepted-SHA dependency.
- Verify intentional wait is represented cleanly.
- Deliver the dependency through authenticated mailbox.
- Require same-session continuation and a healthy supervision classification.
- Record any remaining shell-polling or activity-staleness behavior under
  FUP-03.

### E2E-C07 — Account next and auto-resume

Codex only:

- Exercise account-next selection and binding for a subsequent resume.
- Require no logout.
- Require the selected account to bind to the resumed incarnation.
- Require durable worker/run/worktree preservation.

Claude:

- Verify unsupported account-switch behavior fails clearly without affecting
  session recovery.

### E2E-C08 — Graceful recovery boundary

- Diagnose a provider/session mismatch without mutation.
- If a restart is genuinely required, use the Agent Console owner workflow and
  explicit restart authorization.
- Resume, rebind with revision fencing, and require
  `rebind_required=false`.
- Do not restart merely to make the scenario pass.

### E2E-C09 — Acceptance and retirement

- Accept the candidate only after the bounded validation evidence passes.
- Release and retire the worker through the folded lifecycle.
- Require claim release, zero active/uncertain operations, logical deletion,
  and fresh-list exact-session absence.
- Close the run only after every assignment is terminal.

## Phase D — Product Parity

The Claude run must use the installed Claude Code executable, not a simulated
adapter. Repeat all applicable A, B, and C scenarios and compare:

- hook event ingress and denial shape
- prompt delivery and readiness proof
- mailbox consumption
- claim and operation behavior
- fresh-session runtime-surface discovery
- retirement and fresh-list absence

Provider-specific differences are acceptable only when they are explicit,
typed, tested, and do not weaken the shared authority boundary.

## Blocking Defects

Stop deployment acceptance only for:

- hook bypass or unauthorized default-branch commit
- wrong session, incarnation, account, claim, repository, or worktree mutation
- data loss or unrecoverable partial mutation
- prompt replay or multiple automatic Enter injections
- secrets or private packet/message bodies in public output
- fresh Codex or Claude session unable to load the deployed runtime surface
- worker retirement that hides a still-active or uncertain operation

Everything else is recorded as a follow-up with evidence, impact, suggested
owner, acceptance test, and rerun selector.

## Improvement Log

Append one row for every non-blocking observation:

| ID | Scenario | Product | Observation | Impact | Suggested improvement | Acceptance | Rerun |
| --- | --- | --- | --- | --- | --- | --- | --- |

Promote stable findings into
`2026-07-27-main-agent-local-delivery-follow-ups.md`. Keep raw temporary
evidence outside the repository.

## Completion

The E2E run is complete when:

- both product matrices finish;
- all blocking defects are absent or repaired and rerun;
- non-blocking findings are recorded as follow-ups;
- deployed surfaces remain converged;
- test sessions/worktrees are retired with fresh-list absence proof; and
- primary repositories remain clean and unpushed.
