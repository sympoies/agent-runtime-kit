# Agent Policy Simplification Implementation Handoff

- **Status**: implemented and validated locally; retained as the acceptance
  source
- **Date**: 2026-07-25
- **Source**: In-session review of the runtime-kit policy, documentation,
  evidence, validation, and workflow surfaces
- **Intended next step**: implement the bounded core-policy slice in a managed
  worktree, validate it locally, and deliver one signed commit to local `main`
  without GitHub or provider mutation

## Purpose

Reduce prompt and process overhead now that the target models can plan and
execute competently from outcomes, constraints, and acceptance criteria.
Preserve rules that protect authority, user work, secrets, repository
integrity, external state, and deterministic quality gates. Move procedural
detail out of always-loaded policy and let the agent choose the smallest
effective execution path unless a repository, tool, or high-risk workflow
requires a specific one.

## Confirmed Facts

- `AGENT_HOME.md` says it contains invariants and routing, but currently also
  carries tier announcements, source-tag syntax, evidence choreography, exact
  Git tool selection, execution-capsule rules, and session-closeout steps. [F1]
- The rendered home prompts exceed the nominal 4 KiB budget. The context audit
  permits product-specific overrides instead of enforcing the stated target.
  [F2]
- The `project-dev` edit preflight currently requires `DEVELOPMENT.md`,
  `files-hooks-validation.md`, `evidence-control-plane.md`, and the docs
  placement policy for every edit in this repository. This is materially
  broader than the two-file context surface measured by the current 20 KiB
  edit-phase budget. [F3]
- `project-dev` declares both `bash scripts/ci/all.sh` and
  `bash tests/hooks/run.sh`, while `scripts/ci/all.sh` already invokes the hook
  suite. The declared finish gate therefore repeats the same expensive suite.
  [F3] [F4]
- `evidence-control-plane.md` defines a detailed eight-step test-first record
  lifecycle and a universal closeout owner. The heuristic-system policy also
  prescribes closeout steps after every achieved goal, even though the same
  policy says not to record everything. [F5] [F6]
- Advisory session coordination is non-authorizing and non-blocking, and its
  hook already performs automatic advice for recognized mutations. Requiring
  the full coordination and evidence policies before ordinary edits duplicates
  that mechanical path. [F7]
- Exact commit, worktree, provider-delivery, signing, and protected-branch
  constraints are partly enforced by governed CLIs and hooks. Removing their
  safety contract would weaken behavior; keeping every command sequence in the
  home prompt is unnecessary. [F8]

## Decisions

1. Treat policy as three layers:
   - **always-on invariants**: authority, safety, user-work preservation,
     quality floor, and routing;
   - **conditional policy**: loaded only for the relevant intent, phase, path,
     or risk;
   - **owned runbooks and CLIs**: exact state machines, command syntax, evidence
     schemas, and recovery.
2. Rewrite `AGENT_HOME.md` as a compact constitution. It states outcomes and
   non-negotiable boundaries, not routine planning choreography.
3. Enforce the 4 KiB rendered home-policy target for every product without
   product-specific budget exceptions.
4. Measure the actual resolved required document set for the `project-dev`
   edit phase. The budget must not rely on a manually maintained approximation.
5. Make general repository orientation and docs-placement guidance optional
   and on demand. They remain canonical references, but are not required
   reading for every edit.
6. Reduce required edit policy to a compact engineering contract. The contract
   requires inspection, an explicit behavior delta for behavior changes,
   regression-first proof when practical, and scoped final validation. A
   durable evidence record is required only when a repository gate, high-risk
   workflow, or explicit request requires one.
7. Keep waivers honest but lightweight. If meaningful red is impractical, state
   why and name substitute validation; do not require recorder ceremony for
   docs-only, generated-only, refactor-only, or otherwise non-testable work.
8. During iteration, run the smallest stable checks that answer the current
   question. At completion, run each canonical declared validation gate once.
9. Keep L0 classification internal. Surface a tier decision only when work
   needs durable follow-up, a plan, dispatch, provider state, or a material user
   choice.
10. Keep advisory coordination automatic. Manual context, claims, leases, and
    recovery are conditional on useful overlap information or explicit
    enforcement.
11. Retain exact Git, signing, protected-branch, provider, destructive-action,
    secrets, and concurrency safety contracts. Route their detailed mechanics
    to `git-delivery.md`, tool help, hooks, and workflow-owned runbooks.
12. Make evidence retention and session closeout event-driven. Retain durable
    evidence for audits, handoffs, deferred defects, or workflow gates; do not
    open, migrate, or archive a record merely because a session ended.
13. Preserve a compact Hermes fallback for boundaries that Codex and Claude
    hooks enforce mechanically. Hermes resolves conditional and follow-on
    runbooks explicitly from the selected docs home; do not make all products
    load the maximal common procedure.
14. Validate the redesign behaviorally, not by byte count alone.
15. Treat provider delivery as separate authority. An implementation request
    permits scoped local work; it does not by itself authorize a PR, MR, push,
    issue, or other provider mutation.
16. Keep active-goal blocked-audit fallback, exact-target resolution,
    per-worktree identity/signing prohibitions, and the supervised Execution
    Capsule recovery route in the compact safety plane.
17. Browser execution proves the requested claim. A durable browser-session
    record is conditional on a claim, gate, audit, or handoff that needs it.

## Scope

- Rewrite the always-on home policy and regenerate product render/golden
  surfaces.
- Simplify `AGENT_DOCS.toml` edit-phase routing and remove duplicate validation.
- Make the context-budget audit measure the actual resolved edit-phase
  requirement set and enforce the home-prompt target uniformly.
- Refactor the core policies that define test-first/evidence, files/hooks/
  validation, tier visibility, session coordination, browser routing, Git
  routing, and closeout.
- Add acceptance coverage for ordinary autonomous work and retained safety
  boundaries.
- Update directly affected canonical docs and tests.

## Non-Scope

- No GitHub issue, pull request, Actions, release, or other provider mutation.
- No weakening of hook or CLI enforcement for secrets, destructive actions,
  signing, direct raw commits, protected branches, checkout ownership, or
  provider compare-and-swap.
- No blanket rewrite of every PR, dispatch, release, deployment, browser, or
  memory skill in the first slice. Workflow-specific state machines remain
  conditional runbooks and can be simplified later against the new core
  contract.
- No installed-home sync or live disposable-session acceptance without a
  separate explicit request.

## Implementation Boundaries

- Source policy lives in `AGENT_HOME.md`, `AGENT_DOCS.toml`, and
  `core/policies/**`; rendered `build/**` and `tests/golden/**` are generated
  acceptance surfaces.
- `agent-docs` remains the intent router and finish-line source of declared
  validation. This change alters the catalog, not the external CLI schema.
- `context-budget-audit.py` may invoke `agent-docs` to resolve the source
  catalog. Its self-test must stay deterministic and independent of the live
  user home.
- Exact mutation commands remain owned by the released governed CLIs and hook
  rules. Natural-language policy describes the contract and routes to those
  owners.
- Development happens in the managed
  `refactor/policy-simplification` worktree. The user-authorized terminal state
  is one local-only signed commit on local `main`.

## Requirements

- R1: Every rendered `AGENT_HOME.md` is at most 4096 bytes without an override.
- R2: The always-on policy retains authority, exact-target resolution, safety,
  user-work preservation, active-goal fallback, relevant inspection,
  validation, secret handling, signing provenance, and governed Git/provider
  boundaries.
- R3: Ordinary L0 work does not require a user-facing tier announcement,
  durable evidence record, manual coordination claim, or closeout archive.
- R4: Testable behavior changes still define the contract delta and normally
  capture a meaningful regression failure before production edits. An explicit
  practical waiver and substitute validation remain valid.
- R5: The `project-dev` edit-phase required set is resolved from
  `AGENT_DOCS.toml`, fits the declared budget, and excludes general orientation
  or docs-placement material unless relevant.
- R6: `project-dev` completion declares one canonical validation command; the
  hook suite is not declared twice.
- R7: `task-tools`, `browser-test`, and ordinary `session-coordination` do not
  force-load the full evidence control plane.
- R8: Delivery and high-risk workflows can still route to complete Git,
  evidence, review, and recovery runbooks; Hermes resolves those paths through
  the selected docs home.
- R9: Universal closeout language is replaced by event-triggered retention.
- R10: Generated surfaces, catalogs, support docs, and tests remain consistent.

## Acceptance Criteria

- A1: `python3 scripts/ci/context-budget-audit.py check` reports every rendered
  home prompt at or below 4096 bytes and measures the resolved `project-dev`
  edit requirement set.
- A2: `agent-docs preflight --intent project-dev --phase edit --format json`
  returns only documents needed for ordinary implementation judgment and the
  set fits the edit budget.
- A3: The catalog declares `bash scripts/ci/all.sh` once for `project-dev` and
  does not separately declare `bash tests/hooks/run.sh`.
- A4: Policy tests prove that ordinary L0 work is internally classified,
  evidence/closeout are conditional, and external/destructive/Git safety gates
  remain explicit.
- A5: Render and golden checks pass for Codex, Claude, Hermes, and neutral
  products.
- A6: The full declared local validation passes once after focused checks.
- A7: A focused review finds no new ambiguity that would let an agent infer
  external authority, overwrite user work, skip relevant validation, expose a
  secret, or bypass governed Git/provider boundaries.

## Validation Plan

1. Add focused policy/context-budget assertions and capture a meaningful red
   before changing production policy or audit code.
2. Run the focused context-budget, catalog, render, and policy-contract tests
   while iterating.
3. Run `bash scripts/ci/all.sh` once as the canonical completion gate.
4. Run a focused specialist review of safety, testing, and maintainability;
   repair accepted findings and repeat affected checks.
5. Verify the final worktree diff, signed local-main receipt, and clean
   post-commit checkout. No provider validation is attempted.

## Behavioral Acceptance Matrix

| Scenario | Expected behavior |
| --- | --- |
| Read-only explanation | Inspect enough to answer; no tier speech, plan, evidence record, or closeout archive |
| Small local edit | Inspect target and callers, edit autonomously, run focused checks and the declared final gate |
| Testable behavior change | State the contract delta, capture meaningful red when practical, implement, then validate by risk |
| Non-testable/docs/generated change | Use a concise reason and substitute validation; no fake red or recorder ceremony |
| Ambiguous scope or authority | Ask only the decision that materially changes outcome or permission |
| Active goal needs a decision | Use the blocking question tool when available; otherwise follow the injected blocked-audit contract without a premature plain-text stop |
| Destructive, external, sensitive, or costly action | Resolve exact targets and obtain required authorization; fail closed where authority is absent |
| Dirty or concurrent checkout | Preserve user work, use isolation or coordination information, and never erase or overwrite unrelated changes |
| Provider delivery | Require explicit current-task authority, then use the governed Git/provider owner and its complete runbook |
| Routine browser claim | Use the smallest browser/test output that proves the claim; retain a browser-session record only when a durable record is required |
| Authorized operation cannot run locally | Resolve the Execution Capsule runbook from the selected docs home; supervised host access never waives repository controls |
| Memory or unstable external fact | Load the matching conditional policy and use authoritative/current evidence |

## Findings And Fix Locations

| Priority | Issue | Evidence | Fix location | Acceptance |
| --- | --- | --- | --- | --- |
| P0 | Always-on policy mixes invariants with procedure | [F1] [F2] | `AGENT_HOME.md` | R1-R3 |
| P0 | Required edit context and measured context differ | [F2] [F3] | `AGENT_DOCS.toml`, `scripts/ci/context-budget-audit.py` | R5 |
| P0 | Validation declares the hook suite twice | [F3] [F4] | `AGENT_DOCS.toml` | R6 |
| P1 | Test-first record mechanics are universal rather than risk-driven | [F5] | `core/policies/evidence-control-plane.md` | R4, R8 |
| P1 | L0 tier and coordination ceremony leak into routine collaboration | [F1] [F7] | `AGENT_HOME.md`, tier and coordination policies | R3 |
| P1 | Closeout retention is prescribed after every goal | [F5] [F6] | evidence and heuristic policies | R9 |
| P1 | Git safety and Git procedure are co-located in prompt text | [F1] [F8] | home policy and `git-delivery.md` | R2, R8 |

## Risks And Guardrails

- **Oversimplification**: concise wording may hide a safety requirement.
  Guardrail: retain explicit negative boundaries for authority, secrets,
  destructive/external actions, user work, signing, and protected branches,
  backed by behavioral assertions and review.
- **Prompt savings move into mandatory docs**: a smaller home prompt would not
  help if every edit loads equally large required policy. Guardrail: measure
  the resolved required set rather than hand-picked files.
- **Test-first becomes optional by convenience**: “when practical” can be
  abused. Guardrail: require an explicit reason plus substitute validation and
  keep repository/high-risk gates able to require durable records.
- **Generated drift**: source and product surfaces may diverge. Guardrail:
  renderer/golden validation remains part of the canonical gate.
- **Provider outage**: local completion can be mistaken for delivery.
  Guardrail: the final receipt and response must state that local `main` was
  committed and provider state was not mutated.

## Retention Intent

Coordination material; cleanup-eligible after the redesign is implemented and
its durable rules are reflected in canonical policy. Retain temporarily as the
read-first acceptance source for review and follow-up simplification waves.

## Read-First References

- `[F1]` `AGENT_HOME.md`
- `[F2]` `scripts/ci/context-budget-audit.py`
- `[F3]` `AGENT_DOCS.toml`
- `[F4]` `scripts/ci/all.sh`
- `[F5]` `core/policies/evidence-control-plane.md`
- `[F6]` `core/policies/heuristic-system/HEURISTIC_SYSTEM.md`
- `[F7]` `core/policies/session-coordination.md`
- `[F8]` `core/policies/git-delivery.md`
- `core/policies/files-hooks-validation.md`
- `core/policies/work-tier-levels.md`
- `core/policies/intent-cards.md`

## Recommended Next Artifact

The implemented diff and its local validation/review evidence. No separate plan
bundle or provider tracker is needed for this bounded, same-session execution.
