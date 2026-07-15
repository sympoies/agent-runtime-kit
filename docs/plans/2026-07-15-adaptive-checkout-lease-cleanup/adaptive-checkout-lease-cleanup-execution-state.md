# Execution State: Adaptive checkout lease and workflow cleanup

## Execution State

- Source document: docs/plans/2026-07-15-adaptive-checkout-lease-cleanup/adaptive-checkout-lease-cleanup-plan.md
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/614>
- Current sprint: Sprint 3
- Status: in progress
- Current gate: delegated follow-up review and final provider convergence
- Plan branch: `feat/adaptive-checkout-lease-cleanup`
- Integration PR: <https://github.com/graysurf/agent-runtime-kit/pull/615>
- Next task: Task 3.1
- Blockers: none
- Last updated: 2026-07-15

## Task Ledger

| ID | Title | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | Capture the lease contract with failing tests | done | Meaningful red: checkout lease hook wiring absent; focused state-machine suite now 9/9 pass | v2 test-first pre-edit gate verified |
| 1.2 | Implement and render the shared checkout lease guard | done | Atomic lease, dirty/foreign/stale/recreated/operation/read-only/Stop tests 9/9 pass | Codex and Claude wired; Hermes capability ceiling retained |
| 2.1 | Add terminal workflow cleanup policy and workflow contracts | done | PR runtime smoke 6/6; dispatch runtime smoke 14/14 | PR, L2, and L3 terminal cleanup contracts aligned |
| 2.2 | Refresh generated product surfaces and documentation mirrors | done | Codex, Claude, and Hermes renders refreshed; nine governed skill goldens updated | Generated outputs match canonical templates |
| 3.1 | Run full validation and delegated pre-merge review | in-progress | Pinned full CI positions 1-16 pass at `d539e8a`; latest repairs pass focused lease tests 24/24, hooks 210/210, PR smoke 6/6, and dispatch smoke 14/14 | Review produced 59 provider-visible finding rows covering 49 unique issues; all are repaired locally and await final follow-up review |
| 3.2 | Deliver and merge the tracked PR | pending | pending | governed PR lifecycle |
| 3.3 | Activate both runtime roles and perform strict closeout | pending | pending | merged revision only |

## Validation Log

- 2026-07-15: `project-dev` and `task-tools` intents activated for the managed
  implementation worktree before production edits.
- 2026-07-15: the hook-wiring contract failed meaningfully before production
  edits. The completed lease suite passes 9/9, PR runtime smoke passes 6/6,
  dispatch runtime smoke passes 14/14, and governed product renders/goldens
  were refreshed.
- 2026-07-15: repository-pinned full CI passed positions 1-16 via
  `scripts/dev/with-nils-version.sh release:v1.22.3 -- bash scripts/ci/all.sh`.
  This includes all 187 hook tests and 99 runtime-smoke passes with one
  expected host-capability skip for screen recording.
- 2026-07-15: testing, maintainability, performance, security, and mandatory
  red-team specialists posted 14 provider-visible findings. Review repairs
  captured a meaningful focused red with seven failures, then passed 18/18
  focused tests, 196/196 hook tests, PR smoke 6/6, and dispatch smoke 14/14.
  Follow-up specialist read-back then reported eight finding rows covering four
  unique boundary issues: slug shadowing, nested checkout collapse, compound
  removal scope, and incomplete read-only Git query families. A second
  meaningful red captured ten failures; the repaired suite passes 20/20
  focused tests, 198/198 hook tests, PR smoke 6/6, and dispatch smoke 14/14.
  A third read-back caught four final parser/lifecycle issues: option-value
  target confusion, multiple-remove partial claim, failed-removal lease
  retention, and an unresolved nested-boundary fail-open. Four meaningful red
  failures were captured; the repaired suite passes 24/24 focused tests,
  202/202 hook tests, PR smoke 6/6, and dispatch smoke 14/14. Convergence
  security review then found one shared wrapper-parser bypass affecting
  `command --`, `exec --`, option-bearing GNU `time`, and separator-free
  `agent-run exec`. Four meaningful red failures were captured; the shared
  parser now consumes each supported wrapper's real option grammar, recursively
  unwraps nested invocations, and treats ambiguous wrapper syntax as opaque
  mutation. Security convergence passed, then maintainability convergence found
  that valid combined `time` / `exec` options could still become opaque and
  that only the lease consumer handled the opaque marker. Eleven meaningful
  red failures captured the combined-option, forge-wrapper, and cross-consumer
  boundaries. The shared parser now handles value-bearing short-option
  clusters, retains opaque candidate tokens, and the direct commit, worktree,
  PR/MR, Python, lease, and forge-reminder consumers fail closed for candidates
  they govern. Subsequent maintainability and security passes found GNU `time`
  attached-value / unique-abbreviation boundaries, GNU `env` lone-dash,
  attached-value, and signal-option forms, recursive opaque suffixes, and a
  fail-open sixth nested-shell layer. Twenty-seven meaningful red failures
  captured those cross-consumer cases. The parser now follows left-to-right
  short-option semantics, resolves unique GNU long options, shares one `env`
  implementation with the forge reminder, recursively inspects opaque suffixes,
  and emits an unresolved-nesting marker at its bound. Five-layer read-only and
  unrelated opaque commands remain allowed. The final bounded read-back found
  three remaining GNU `env` disagreements: attached unset values broke valid
  authorization markers, combined/abbreviated option values could masquerade
  as an emergency worktree override, and exhausted split-string recursion
  dropped the governed command. Focused red assertions reproduced each family.
  One normalized env-prefix parser now preserves option/value boundaries,
  applies reset and unset effects in order, and emits an opaque unresolved
  marker at the recursion bound. The focused lease suite remains 24/24, hooks
  then passed 209/209. A further ordered-state review found seven issues across
  nested/process-inherited marker reset, wrapper option values, wrapper-hidden
  env reset, assignments after `env --`, GNU split-string variable expansion,
  and a depth test that used separate env processes instead of one recursively
  split invocation. Eighteen meaningful red failures captured the combined
  boundary. One shared marker-environment walker now follows the same wrapper
  target grammar as command classification, applies assignment/reset/unset in
  execution order, ignores wrapper option values, accepts post-`--` assignment
  operands, and fails closed on GNU split expansion syntax that cannot be
  resolved statically. The corrected single-process depth case and variable
  expansion case cover every governed consumer. The focused lease suite remains
  24/24, hooks pass 210/210, PR smoke passes 6/6, and dispatch smoke passes
  14/14. The next target-aware read-back found that an opaque dynamic or
  depth-exhausted split invocation could conceal managed removal of a
  foreign-leased worktree while the guard leased only shell CWD. It also found
  GNU split escape divergence and an overbroad quoted-dollar fallback. Nine
  meaningful red assertions captured hidden target scope, active escape
  boundaries, and harmless single-quoted dollars. The lease guard now rejects
  unresolved mutation scope before base-checkout fallback. The following
  bounded read-back proved that outer-shell quote provenance is unavailable,
  so an apparently single-quoted dollar may already have expanded; it also
  found that an active GNU split-string comment can hide appended argv. Four
  focused tests produced fourteen meaningful red assertions across the direct
  guards, forge enforcement, lease mutation identity, and foreign-worktree
  targeting. The scanner now conservatively marks every split-string dollar
  and active unquoted comment as opaque. This intentionally accepts a narrow
  literal-dollar false positive to prevent a cross-consumer fail-open. Fully
  resolved managed removal remains target-aware. The next new-head read-back
  found the equivalent legacy backtick substitution gap and an avoidable false
  positive for embedded hashes that GNU `env` does not treat as comments. Five
  focused tests produced ten meaningful failures across every governed
  consumer, lease mutation identity, foreign-worktree scope, and harmless hash
  data. The scanner now treats every backtick as unresolved while tracking GNU
  split-word boundaries so only an unquoted word-leading `#` becomes opaque.
  Both maintainability and security then identified the same final precision
  issue: Python Unicode whitespace is broader than GNU split separators. Three
  meaningful red assertions captured the NBSP false positive across the direct
  guards. A named ASCII separator set now preserves GNU word boundaries while
  form feed and vertical tab retain their conservative opaque classification.
  The mandatory final red-team pass then found two checkout-lease bypasses:
  shell control words could occupy command position ahead of a known mutator,
  and dynamic executable expansion could run before static classification.
  Two focused tests produced sixteen meaningful failures across missing session
  identity, target-aware foreign removal, conditionals, loops, function bodies,
  nested shells, variables, backticks, and command substitution. Shared
  invocation parsing now skips supported shell control prefixes, while dynamic
  command positions become opaque mutations and cause unverifiable managed
  removal scope to fail closed. The bounded follow-up found that Bash's
  `function name { ...; }` form still kept its declaration header in executable
  position and that wrapper targets were incorrectly reinterpreted as outer
  shell control words. Three focused tests produced six meaningful failures.
  Invocation parsing now explicitly tracks whether it is at a shell boundary:
  only outer shell commands consume control syntax, wrapper targets retain
  literal executable names, and Bash function headers expose their bodies.
  Focused tests, the 24/24 lease suite, hooks 210/210, PR smoke 6/6, and dispatch
  smoke 14/14 pass. Final specialist read-back and full CI remain before the
  owner decision.

## Session Notes

- 2026-07-15: classified as L2 because the change spans shared enforcement,
  multiple product render surfaces, delivery workflows, provider review, and
  dual-role activation. The user selected the adaptive lease design and
  requested end-to-end delivery.
- 2026-07-15: the primary checkout contains another active agent's edits. It is
  intentionally preserved; this plan executes in a separate managed worktree.
