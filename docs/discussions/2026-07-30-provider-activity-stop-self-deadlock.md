# Provider Activity Stop Self-Deadlock Implementation Handoff

Status: implementation, governed local-main integration, deployment, and
installed-product field contract closed; end-to-end provider-runner
termination remains a residual observation
Date: 2026-07-30
Source: retained real-product Codex Stop-hook loop from session
`20260729-131513-codex`
Intended next step: retain one natural provider-runner termination as residual
F39 evidence; do not block B2's separately constrained field boundary on it

## Purpose

Preserve the field diagnosis and accepted repair boundary for F39: an
`agent-session.activity.v1` failure on `Stop` must not prevent the provider
runner from terminating indefinitely.

## Confirmed facts

- The same Codex Stop hook
  `stop:6:$HOME/.codex/config.toml` was injected repeatedly without a terminal
  result.
- Hook reasons repeatedly included
  `coord.activity.prompt-stop:capability-failure-closed`.
- Ordinary Bash and `apply_patch` calls were also denied after activity
  recording failed, including an authenticated attempt to inspect the activity
  CLI.
- Waiting, completing or interrupting reviewer agents, and retrying Stop did
  not converge the old session.
- The old session was later terminated externally. Its activity status now
  reports `session-not-found`.
- A fresh session can execute ordinary tools and reports its own activity
  state normally.
- `owner-active-self` is an allow classification in `agent-hook`; it was
  visible in the aggregate reasons but was not the blocking decision.
- `agent-hook` currently invokes
  `agent-session activity event --stdin <session>` for the activity capability.
  A nonzero child result becomes a capability error, and the locked activity
  rule's closed failure posture blocks `Stop`.
- A raw `Stop` observation is journal evidence only. It does not fabricate the
  activity state as waiting or release coordination authority.
- The repair is signed on nils-cli managed branch
  `fix/f39-stop-activity-failure` at
  `4a282e1f2f4129151eec3594691790e6ac9d677d`.
- The same repair is integrated on signed nils-cli local `main`
  `949b92c188ca8b74f70d1259eb8825ec1b1ce3c2`.
- The installed binary reports
  `agent-hook 1.25.11 (v1.25.9-93-g4a282e1f)`.
- Codex and Claude hook doctors are converged with no legacy residue.
- An isolated installed-binary fixture forced the activity child to exit 65:
  Codex `Stop` returned normalized `warn` with
  `activity-stop-reconciliation-required` and provider `{}` at exit zero;
  Claude `Stop` returned supported warning context at exit zero; Codex
  `PreToolUse` retained `capability-failure-closed` at exit one.

## Decisions

- Preserve fail-closed activity admission for `UserPromptSubmit`,
  `PreToolUse`, and every other non-terminal event.
- When the activity capability itself fails for `Stop`, return the stable
  warning `activity-stop-reconciliation-required` and allow provider
  termination.
- Apply the same terminal-only decision to the config-independent emergency
  recovery manifest path.
- Preserve the normalized warning for audit, but render Codex `Stop` as the
  provider-native neutral `{}` response because that event does not support
  additional context. Claude retains its supported warning context.
- Keep `agent-session.coordination.v1` independent. An active or uncertain
  admitted operation may still block or require typed reconciliation under its
  existing contract.
- Do not release or mutate claims, leases, operations, brokers, worktrees,
  assignments, or session state from the terminal activity degradation path.
- Treat the retained activity state as uncertain until a later authenticated
  controller reconciles or retires it.
- Do not solve this problem by disabling hooks, broadening folder trust,
  accepting arbitrary recovery commands, force-deleting sessions, killing
  processes, or sending provider input.

## Scope

- `nils-agent-hook` activity capability evaluation.
- Stable typed terminal warning.
- Regression coverage proving the Stop-only boundary.
- Agent-hook contract documentation.
- Installed binary and provider-hook convergence validation.
- One bounded real-product validation that proves a failed Stop activity child
  cannot create another infinite prompt loop.

## Non-scope

- General automatic reconciliation of every stale activity snapshot.
- Weakening ordinary tool or prompt admission.
- Changing semantic-conflict or owner-liveness classification.
- Releasing orchestration authority during Stop.
- F38 active-run selection or B2 ambiguous-stop implementation.

## Implementation boundaries

The terminal degradation belongs in the compiled
`agent-session.activity.v1` capability evaluator, not in user configuration or
the runtime-kit policy manifest. The policy remains locked and fail-closed.
Only the `Stop` event converts a capability execution error into a warning.

The warning must be generated without exposing child stderr, capability
material, session paths, provider payload, prompt content, or transcript
content.

## Requirements

1. Successful activity recording remains `allow` with the configured policy
   reason code.
2. Failed activity recording on `Stop` returns exit zero, aggregate
   `action:"warn"`, and
   `code:"activity-stop-reconciliation-required"`.
3. The same failed child on `PreToolUse` returns nonzero and the existing
   capability-failure-closed block.
4. The terminal warning does not bypass the separate coordination transaction
   rule.
5. Codex and Claude use the same terminal boundary.
6. No provider input or session deletion is part of implementation or field
   validation.

## Acceptance criteria

- A meaningful regression fails against the pre-repair evaluator and passes
  after the production change.
- Focused agent-hook activity, contract, API, and security tests pass.
- `cargo fmt --all -- --check`, `git diff --check`, and agent-hook clippy pass.
- The nils-cli repository gate is invoked once; any clean-baseline failure is
  reported separately.
- Specialist security, API-contract, testing, and maintainability review has no
  unresolved actionable finding.
- The signed managed-branch commit has an outside-repository receipt.
- The changed runtime binary is installed and both provider hook doctors
  converge.
- A bounded real-product Stop failure returns once instead of reinjecting the
  same hook indefinitely.

## Delivered result

- The normal evaluation and emergency recovery paths share one event-exact
  terminal activity failure decision.
- Nonterminal activity failures remain fail-closed.
- A failed activity observation cannot override an authoritative coordination
  block; the aggregate decision retains both typed reasons.
- Provider rendering is event-native for both Codex and Claude.
- The first-wave specialist review found three valid issues: recovery-path
  parity, Codex provider rendering, and coordination composition coverage.
  All were fixed and the original reviewers returned no remaining finding.
- Security and performance review reported no verified finding. The required
  red-team review reported no added finding.
- Focused validation passed: activity 4/4, recovery 9/9, API contract 11/11,
  coordination ingress 5/5, and security review 19/19. Clippy, formatting, and
  diff checks passed.
- The full nils-cli gate was invoked once and stopped only at the known
  clean-baseline publish-order failure where `nils-claude-cli` precedes its
  `nils-scrub` dependency. That failure is not attributed to F39.
- Outside-repository evidence is retained under
  `$AGENT_HOME/out/projects/sympoies__nils-cli/20260730-131419-f39-stop-activity-failure`.
- Nils-cli local `main` and `origin/main` later aligned at the signed F39
  integration commit. Provider delivery provenance is not attributed to this
  workflow.
- F38 subsequently integrated on signed nils-cli local `main`
  `02ac792bb10c0b4d921141869831ec3223f08988`, and the combined F38/F39
  `agent-session` and `main-agent` binaries were rebuilt and installed from
  that canonical tree.

## Residual observation

The installed-product contract is field-proven without mutating an unrelated
live session. A future natural provider-runner termination with an unavailable
activity child may add end-to-end observation evidence, but it is not required
to resume F38 review because the exact installed ingress decisions and provider
payloads are already proven.

## Validation plan

- Run the exact Stop-versus-PreToolUse regression.
- Run all `nils-agent-hook` activity tests.
- Run agent-hook contract and security suites.
- Run formatting, diff, clippy, and the declared repository gate.
- Inspect the installed version and hook doctor output.
- Use a disposable managed session or fixture for field validation; preserve
  raw typed output before cleanup.

## Risks and guardrails

- Allowing every activity failure would weaken admission. The degradation must
  remain event-exact to `Stop`.
- A Stop warning could hide an active operation if it bypassed transaction
  handling. The coordination capability remains separately selected and
  authoritative.
- Repeated warnings without retained state could erase evidence. Existing
  activity and coordination state must remain untouched.
- Field validation must not intentionally corrupt an unrelated live session.

## Relationship to the blocker queue

- F39 no longer blocks specialist review or a later real-product worker.
- F38 implementation, specialist review, governed local-main integration, and
  installed deployment are closed at nils-cli local `main` `02ac792b`.
- B2 retains its live-claim proof, but full field closure remains open until the
  process-dead/tmux-live classifier produces a non-`healthy_progress` result.
- B3 remains closed.

## Retention intent

Retain this discussion until the F39 result is folded into the Main Agent Mode
blocker inventory. Then retire it according to the repository documentation
retention policy.

## Read first

- `core/policies/agent-hook/runtime-kit-v1.toml`
- `core/policies/agent-hook/README.md`
- nils-cli `crates/agent-hook/src/evaluator.rs`
- nils-cli `crates/agent-hook/tests/activity.rs`
- nils-cli `crates/agent-hook/docs/specs/agent-hook-v1.md`
- `docs/discussions/2026-07-27-main-agent-mode-blocker-inventory.md`
