# Plan: Agent capability convergence

## Overview

Execute issue #562 as one L3 dispatch plan with four lanes. First turn the #561
ledger into reviewed placement decisions. Then land replacement behavior for
Browser/Evidence and the remaining skill families. A single manifest owner
retires replaced surfaces only after both migration lanes pass. Finally merge
to `main`, activate the managed runtime on the two runtime roles, and verify
fresh Codex CLI and Claude Code sessions against the macOS GUI target.

## Read First

- Primary source: docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-discussion-source.md
- Source type: discussion-to-implementation-doc
- Open questions carried into execution: none; required nils-cli gaps, if discovered, are implementation dependencies owned by the affected lane and must be released before consumption

## Scope

- In scope: the frozen 66-row disposition; selective intent loading; policy,
  hook/gate, CLI, and parent-workflow placement; Browser/Evidence migration;
  convergence of all remaining agent-only skills; active manifest and rendered
  surface retirement; compatibility and stale cleanup; portable runtime
  acceptance; private dual-role activation and fresh-session verification.
- Out of scope: publishing private host configuration; replacing released
  nils-cli primitives with repository scripts; retaining internal workflow
  fragments under hidden or unsupported exposure classes.

## Dispatch Model

- Plan branch: `feat/agent-capability-convergence`.
- Lane A (`disposition`): Tasks 1.1 and 3.1; sole owner of the disposition
  ledger, active skill manifest, final render/golden retirement, and active
  surface expectations.
- Lane B (`browser-evidence`): Task 2.1; owns Browser/Evidence replacement
  policy, intent, hook/gate, and focused tests; does not remove skills.
- Lane C (`remaining-skills`): Task 2.2; owns replacement/routing changes for
  all other domains; does not edit shared manifests or retire sources.
- Lane D (`deployment-acceptance`): Tasks 3.2 and 4.1; owns portable activation
  acceptance and private post-merge rollout evidence.
- Lane PRs target the plan branch. The final integration PR targets `main`.

## Sprint 1: Review the complete disposition ledger

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Decide all 66 placements and immediately admit only the active
user-outcome rows that can carry truthful reviewed/default metadata. Rows that
need replacement remain pending until Sprint 3 rather than receiving false
exposure metadata.

**Demo/Validation**:

- Command: `bash tests/skill-exposure-contract/run.sh`
- Verify: all 66 decisions are represented in the lane's dispatch packet,
  immutable ledger invariants hold, and every row actually changed to reviewed
  has truthful active invocation/exposure metadata.

### Task 1.1: Review all 66 disposition rows

- **Location**:
  - `manifests/skill-dispositions.yaml`
  - `manifests/skills.yaml`
- **Description**: Lane A reviews every frozen row using the landed #561
  vocabulary and required fields. Retained user-outcome skills receive complete
  invocation and default-exposure metadata. A row whose replacement is not yet
  live remains pending in the canonical ledger; its reviewed decision is passed
  to the assigned migration lane through the dispatch task packet and is
  committed atomically in Task 3.1. This packet must not become a second
  checked-in inventory. Record any required upstream nils-cli capability as a
  lane dependency rather than a private substitute.
- **Dependencies**:
  - none
- **Complexity**: 9
- **Acceptance criteria**:
  - Every baseline ID has one explicit reviewed decision in the dispatch packet
    and no alternate checked-in inventory is introduced.
  - Ledger rows changed to `reviewed` preserve baseline order/count/digest and
    have every schema-required decision field; rows waiting for replacement
    remain pending until Task 3.1.
  - Every reviewed active row has complete invocation and
    `exposure.profile: default`; no row uses unsupported `advanced` exposure.
  - Each rehome/merge/remove decision names its parent intent or workflow,
    enforcement point, migration sequence, compatibility need, and live cleanup
    requirement.
  - Product list-skills diagnostics agree with active manifest truth for Codex,
    Claude, and Hermes.
- **Validation**:
  - `bash tests/skill-exposure-contract/run.sh`
  - `bash scripts/ci/skill-governance-audit.sh`
  - `agent-runtime list-skills --source-root "$PWD" --product codex --format json`
  - `agent-runtime list-skills --source-root "$PWD" --product claude --format json`
  - `agent-runtime list-skills --source-root "$PWD" --product hermes --format json`

## Sprint 2: Land replacement behavior

**PR grouping intent**: `group`
**Execution Profile**: `parallel-x2`

**Goal**: Make Browser/Evidence and all remaining agent-only workflows operate
through the layered runtime while retaining old skill sources as temporary
compatibility surfaces.

**Demo/Validation**:

- Command: focused hook, intent, runtime-smoke, and policy contract tests from
  each lane.
- Verify: natural-language parent workflows invoke replacement behavior without
  requiring bookkeeping skill names.

### Task 2.1: Migrate Browser and Evidence behavior

- **Location**:
  - `AGENT_DOCS.toml`
  - `AGENT_HOME.md`
  - `core/policies/`
  - `core/hooks/`
  - `core/policies/browser-test-routing.md`
  - `core/policies/evidence-control-plane.md`
  - `tests/hooks/`
  - `tests/runtime-smoke/cases/browser/`
  - `tests/runtime-smoke/cases/evidence/`
- **Description**: Lane B implements selective browser-test and relevant
  project-dev/task-tools intent procedures; moves test-first, browser
  escalation, evidence ownership, review/docs-impact/model-check/usage judgment
  to the correct policy and parent workflows; enforces observable ordering and
  completion in hooks or released gates; and preserves deterministic nils-cli
  records and diagnostics. This task does not remove skill sources or edit the
  shared skill manifests. Released v1.21.15 lacks durable selective-intent
  activation/status/verification, so this lane must open and deliver the
  product-neutral nils-cli primitive, release it, and pin it before runtime-kit
  consumption. Phase-aware test-first, workflow-usage, and docs-impact record
  gaps must be verified against the same upstream boundary and delivered there
  when required by acceptance.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 10
- **Acceptance criteria**:
  - A feature request activates project-dev and test-first behavior without the
    user naming an evidence skill.
  - A browser test selects the proper static HTTP, rendered browser, Playwright,
    or desktop path and creates verified session artifacts appropriate to the
    claim.
  - Code review, docs impact, web evidence, model cross-check, skill usage, and
    session closeout are owned by parent workflows without duplicate records.
  - Detailed intent documents load selectively; unrelated tasks do not receive
    every Browser/Evidence procedure.
  - Hooks block only deterministically observable violations and fixtures cover
    waivers, docs-only, generated-only, and unavailable-harness paths.
  - Existing Browser/Evidence skills remain temporarily operational until Task
    3.1 applies retirement.
  - Codex and Claude enforce equivalent supported hook decisions; Hermes uses
    shared policy/CLI verification and reports its declared no-hook capability
    ceiling without false parity.
- **Validation**:
  - `agent-docs preflight --docs-home "$PWD" --intent project-dev --strict`
  - `agent-docs preflight --docs-home "$PWD" --intent task-tools --strict`
  - `bash tests/hooks/run.sh`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain browser`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain evidence`

### Task 2.2: Converge all remaining agent-only skill families

- **Location**:
  - `core/skills/meta/`
  - `core/skills/conversation/`
  - `core/skills/code-review/`
  - `core/skills/issue/`
  - `core/skills/pr/`
  - `core/skills/dispatch/`
  - `core/skills/media/`
  - `core/skills/reporting/`
  - `core/skills/computer-use/`
  - `core/policies/`
  - `tests/runtime-smoke/`
- **Description**: Lane C applies the disposition model to Meta plumbing,
  Conversation execution modes, Code Review internals, Issue/PR/Dispatch
  lifecycle helpers, and bookkeeping embedded in Media, Reporting, and Computer
  Use. It retains distinct user outcomes and moves agent-only substeps under
  parent intents, policies, gates, or internal workflow control. This task lands
  replacement behavior and tests but does not edit shared manifests or retire
  skill source trees; lifecycle removal is centralized in Task 3.1.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 10
- **Acceptance criteria**:
  - Each remaining family has one or more clear user outcome entrypoints and no
    replacement design depends on users selecting lifecycle substeps.
  - Code-review routing automatically selects quick or specialist review while
    preserving delegated-review and evidence gates.
  - Issue, PR, and Dispatch lifecycle mechanics remain callable by parent
    workflows and preserve provider-visible record contracts.
  - Meta maintenance outcomes remain available where genuinely user-requested;
    internal primitives load through policy, intent, hook, or parent workflow.
  - Media, Reporting, and Computer Use retain real user outcomes while evidence
    and transport bookkeeping are not exposed as separate user choices.
  - Existing skills remain operational until Task 3.1 applies reviewed
    retirement decisions.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain meta`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain conversation`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain code-review`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain issue`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain pr`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain dispatch`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain media`
  - `bash tests/runtime-smoke/run.sh --mode deterministic --domain reporting`

## Sprint 3: Retire replaced surfaces and prove portable activation

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Apply the reviewed retirement atomically, then prove clean
render/install/prune/sync behavior without depending on private machine state.

**Demo/Validation**:

- Command: full render/governance/install/runtime-smoke stack.
- Verify: only reviewed user outcomes remain discoverable and stale managed
  skill files are pruned.

### Task 3.1: Apply manifest, render, compatibility, and cleanup retirement

- **Location**:
  - `manifests/skill-dispositions.yaml`
  - `manifests/skills.yaml`
  - `manifests/plugins.yaml`
  - `core/skills/`
  - `targets/codex/`
  - `targets/claude/`
  - `targets/hermes/`
  - `tests/golden/`
  - `tests/sandbox/`
  - `tests/runtime-smoke/`
  - `scripts/ci/skill-governance-audit.sh`
- **Description**: Lane A reads back Tasks 2.1 and 2.2, then uses the governed
  create/remove lifecycle to retire only skills whose replacements are live.
  Update disposition history, active manifest, plugins, generated surfaces,
  goldens, sandbox expectations, runtime smoke, compatibility aliases, and
  ownership-safe stale cleanup together. Rows remain in the immutable ledger
  after source retirement. Any unmet replacement leaves that row active and
  prevents task completion rather than weakening acceptance.
- **Dependencies**:
  - Task 2.1
  - Task 2.2
- **Complexity**: 10
- **Acceptance criteria**:
  - No skill retained in normal discovery exists only for bookkeeping,
    one-command wrapping, or an agent lifecycle substep.
  - Every removed source has reviewed replacement, compatibility, manifest,
    render, install expectation, and stale-prune evidence.
  - The frozen disposition ledger still contains all 66 original IDs as
    reviewed history and records active-retained versus source-retired outcomes
    accurately through destination, migration, and cleanup fields.
  - `migration.pending_disposition` is empty and every ledger row becomes
    reviewed only after its active/default or replacement/removal state is
    truthful.
  - Codex, Claude, and Hermes report the same active semantic set allowed by
    product capabilities, with no stale managed files after prune rehearsal.
  - Whole-plugin retirement removes stale managed Codex and Claude plugin
    registrations, including plugins no longer present in the new marketplace;
    a `review-needed` stale directory is not accepted as successful cleanup.
  - Skill create/remove fixtures and exposure governance fail closed on
    unreviewed additions or incomplete lifecycle edits.
- **Validation**:
  - `bash tests/skill-exposure-contract/run.sh`
  - `bash scripts/ci/skill-governance-audit.sh`
  - `bash scripts/ci/skill-governance-audit.sh --fixture remove`
  - `bash scripts/ci/sandbox-install-rehearsal.sh`
  - `bash tests/runtime-smoke/run.sh --mode install`
  - `bash scripts/ci/all.sh`

### Task 3.2: Add portable convergence deployment acceptance

- **Location**:
  - `scripts/setup.sh`
  - `scripts/sync-runtime-surfaces.sh`
  - `tests/runtime-smoke/`
  - `tests/sandbox/`
  - `manifests/surfaces.yaml`
  - `docs/source/harness-shape-codex.md`
  - `docs/source/harness-shape-claude.md`
  - `SUPPORT_MATRIX.md`
- **Description**: Lane D adds or strengthens product-neutral dry-run/apply,
  install, prune, doctor, revision provenance, and fresh-session smoke coverage
  for the converged surface. The harness identifies runtime roles generically
  and emits redacted, portable evidence. It must not contain live host names,
  connection material, personal paths, or credentials.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Clean and upgrade installs render, activate, and prune retired skills for
    Codex and Claude; Hermes surface diagnostics remain consistent.
  - Doctor/read-back proves the installed runtime revision and expected active
    skill IDs without reading real auth, history, sessions, logs, or caches.
  - Fresh-session smoke cases cover natural-language implementation, code
    review, browser evidence, and desktop-operation routing without naming
    bookkeeping skills.
  - Public fixtures and output contain only generic runtime roles and redacted
    artifact metadata.
  - Dry-run and ownership checks provide a tested rollback path.
- **Validation**:
  - `bash scripts/setup.sh --profile core --skip-homebrew-install --dry-run`
  - `bash scripts/sync-runtime-surfaces.sh --product codex --dry-run`
  - `bash scripts/sync-runtime-surfaces.sh --product claude --dry-run`
  - `bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only`
  - `bash tests/runtime-smoke/run.sh --mode product --product claude --probe-only`
  - `bash scripts/ci/product-leak-audit.sh --self-test`
  - `bash scripts/ci/product-leak-audit.sh`

## Sprint 4: Merge and run private dual-role acceptance

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Merge the reviewed plan branch, synchronize the official `main`
runtime to both roles, and prove future sessions use the completed convergence.

**Demo/Validation**:

- Command: private dry-run/apply sync followed by fresh Codex CLI and Claude
  Code session probes.
- Verify: both products use the merged revision, route outcomes automatically,
  operate the macOS GUI target, retain redacted evidence, and survive a fresh
  session restart.

### Task 4.1: Activate and verify both runtime roles from merged main

- **Location**:
  - `scripts/sync-runtime-surfaces.sh`
  - `tests/runtime-smoke/`
  - `docs/plans/2026-07-11-agent-capability-convergence/agent-capability-convergence-execution-state.md`
- **Description**: After the integration PR merges, Lane D synchronizes the
  public runtime source and any private environment repositories through their
  ownership-safe workflows, previews then applies managed surfaces on the
  remote agent and macOS GUI roles, and starts fresh Codex CLI and Claude Code
  sessions. Validate implementation/test-first routing, delegated code review,
  rendered-browser evidence, and a bounded macOS GUI operation with screenshot
  or recording evidence. Keep machine-specific commands and artifacts in the
  private runtime out tree; post only redacted status, versions, merged revision,
  and generic evidence classes to the dispatch record.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 9
- **Acceptance criteria**:
  - Both runtime roles are synchronized from the merged integration revision;
    doctor and list-skills read-back are clean for installed products.
  - Fresh Codex CLI and Claude Code sessions invoke user-outcome entrypoints and
    automatically apply test-first, review, browser/evidence, and closeout
    contracts without explicit bookkeeping-skill names.
  - The remote agent role completes a bounded operation on the macOS GUI role
    and retains redacted screenshot/session/validation evidence.
  - A second fresh session after activation sees the same managed surface and no
    retired skill files.
  - Public provider evidence passes privacy/leakage checks; private connection
    and machine details remain outside tracked source and public comments.
- **Validation**:
  - `agent-runtime doctor --product codex --profile core`
  - `agent-runtime doctor --product claude --profile core`
  - `agent-runtime list-skills --product codex --format json`
  - `agent-runtime list-skills --product claude --format json`
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`

## Integration And Review Strategy

- Each lane PR targets `feat/agent-capability-convergence` and is reviewed
  through `review-dispatch-lane-pr` before merge.
- Task 1.1 merges first. Tasks 2.1 and 2.2 branch from that plan-branch head and
  may execute in parallel because neither may edit shared manifests or retire
  skill sources.
- Task 3.1 starts only after both replacement PRs merge; it is the single
  retirement integration point.
- Task 3.2 follows the final active surface and can update portable activation
  coverage without private host data.
- The final plan-branch PR targets `main` and receives testing,
  maintainability, API-contract, data-migration, security, and red-team review
  as applicable.
- Task 4.1 runs only after that PR merges. Dispatch closeout requires its live
  acceptance, merged lane/integration PRs, clean review threads, passing checks,
  and a strict `tracking close-ready --profile dispatch --expect-visible` result.

## Testing Strategy

- Contract: skill disposition schema, immutable baseline, invocation/exposure,
  intent catalog, and policy ownership assertions.
- Hook: selected-intent state, pre-edit test-first ordering, final validation,
  docs impact, review/delivery evidence, idempotency, and product parity.
- Render/install: Codex, Claude, Hermes, goldens, plugin manifests, sandbox
  expectations, stale-prune, and doctor.
- Runtime smoke: each retained outcome, removed bookkeeping entrypoint, parent
  workflow routing, direct CLI diagnostics, and product-equivalent results.
- Live: fresh Codex CLI and Claude Code sessions from merged `main`, rendered
  browser assertions, and bounded desktop Computer Use with redacted artifacts.

## Risks And Gotchas

- A reviewed decision is not proof that replacement behavior exists. Task 3.1
  must inspect merged implementation evidence before retiring each source.
- Selective intent state or a pre-edit gate may require nils-cli work. Do not
  create a runtime-kit-only state engine; v1.21.15 has no durable selective
  activation contract, so deliver, release, pin, and consume the upstream
  primitive before Browser/Evidence retirement.
- Broad policy or hook files can become merge hot spots. Lane B owns
  Browser/Evidence-specific policy and hooks; Lane C uses separate family docs
  and adapters; Lane A owns shared manifest integration.
- Product smoke must not read real runtime auth or session state. Live private
  acceptance uses explicit operator-owned environments after merge.
- Static HTTP evidence cannot prove rendered JavaScript or desktop behavior.
- Removing plugin entries without ownership-safe live prune leaves stale skill
- Hermes does not currently expose runtime-kit hooks or agent-docs activation;
  preserve semantic policy and CLI verification while recording that declared
  capability ceiling instead of asserting mechanical hook parity.

## Rollback Plan

- Before retirement, revert a replacement lane independently while old skills
  remain active.
- After retirement, revert the plan integration commit, rerender, reinstall,
  prune stale managed paths, and run doctor on each role.
- Keep the dispatch issue open on any private rollout failure; publish only a
  redacted blocker and restore the prior merged runtime revision.
