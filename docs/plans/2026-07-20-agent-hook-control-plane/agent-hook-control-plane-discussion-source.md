# Agent Hook Control Plane Implementation Handoff

## Document Control

- Status: approved for implementation and deployment
- Date: 2026-07-20
- Owner repository: `graysurf/agent-runtime-kit`
- Implementation repositories: `sympoies/nils-cli`,
  `graysurf/agent-runtime-kit`, and `serenvia/local-scripts`
- Source issue: <https://github.com/graysurf/agent-runtime-kit/issues/686>
- Coordination dependency: <https://github.com/graysurf/agent-runtime-kit/issues/676>
- Work tier: L3, one shared dispatch issue
- Decision owner: maintainer
- Open questions: none; the maintainer explicitly authorized implementation,
  release, installed-surface deployment, and completion reporting

## Requested Outcome

Replace runtime-kit's independently registered Codex and Claude rule handlers
with one nils-cli-owned `agent-hook` control plane. Provider-native hooks remain
only as lifecycle ingress. Host behavior is selected through one
`$XDG_CONFIG_HOME/agent-hook/config.toml`, while versioned runtime-kit policy
bundles define stable rules and defaults. Integrate the already-merged
`agent-session` coordination mechanism, finish its unreleased downstream work,
and deploy the resulting surfaces. [U1]

The completed report must state exactly which provider-native or unrelated
hooks remain, why they remain, and how an operator can inspect, temporarily
bypass, disable, remove, restore, or recover the runtime-kit hook layer. [U1]

## Source Register

- [U1] Maintainer request in this session: execute issue #686 through
  deployment, integrate agent-session coordination, and report remaining hooks
  plus escape-hatch and disable behavior.
- [F1] Issue #686 contains the accepted architecture, XDG boundaries, override
  classes, registration-owner decision, liveness model, break-glass contract,
  reversible sequence, and acceptance criteria.
- [F2] `core/hooks/shared/`, `core/hooks/codex/`, and `core/hooks/claude/`
  currently implement and register runtime-kit rules as independent provider
  handlers.
- [F3] `sympoies/nils-cli:crates/agent-session/src/activity.rs` already owns
  reversible Codex and Claude lifecycle registration, provider normalization,
  drift detection, rollback, and doctor behavior; it must become a compatibility
  façade instead of a competing registration owner.
- [F4] `sympoies/nils-cli` main already contains the #676 work-context,
  conflict-claim, broker, mailbox, and privacy-safe projection mechanism, but
  the installed v1.24.4 surface does not yet expose it because that commit has
  not been released.
- [F5] The #676 tracker has passed mechanism review and records the remaining
  release, runtime-kit policy/admission, private skill, activation, and
  acceptance tasks.
- [I1] #676 should be consumed, released, and closed as a dependency rather
  than reimplemented inside `agent-hook`.
- [I2] Deterministic ordering can be guaranteed only for runtime-kit-owned
  rules evaluated by one dispatcher; unrelated provider, user, project, and
  plugin hooks remain outside that guarantee.

## Frozen Decisions

1. `agent-hook` is a new publishable nils-cli binary and crate. It owns config,
   policy loading, provider adapters, dispatch, aggregation, setup, doctor,
   trace, shadow mode, state, and break-glass capability lifecycle.
2. Runtime-kit owns a versioned product-neutral policy bundle containing stable
   rule IDs, matchers, modes, failure posture, override class, recovery text,
   and implementation capability bindings.
3. `$XDG_CONFIG_HOME/agent-hook/config.toml` is the only user-facing host
   behavior config for runtime-kit-owned hooks in v1. There is no repository
   config layer and no arbitrary config-defined command execution.
4. `agent-hook setup` is the only nils-cli/runtime-kit writer of owned provider
   hook registrations. It installs one dispatcher command per required provider
   event or matcher group and preserves unrelated hooks.
5. `agent-session activity setup` forwards to the new owner or becomes
   read-only compatibility/doctor behavior. It may not leave a second managed
   registration representation after cutover.
6. A verified active foreign writer on the same physical checkout remains a
   hard block. Definite semantic conflict uses #676 and blocks; possible,
   unknown, or incomplete semantic evidence is advisory in v1.
7. Break-glass bypasses all runtime-kit rule decisions only for a displayed,
   authorized, exact one-shot operation or short repair window. It does not
   bypass OS/provider authorization, third-party hooks, or lower-level
   `git-cli`/`forge-cli` transaction and privacy invariants.
8. Break-glass verification occurs before ordinary config and policy loading.
   Persistent environment bypasses, blanket config disables for locked rules,
   state-file deletion, and raw authorization retention are prohibited.
9. Shadow mode is side-effect-free. Stateful rules cut over only after fixture,
   concurrency, crash, privacy, latency, rollback, and live doctor evidence.
10. Release and deployment are authorized by [U1], but their repository-owned
    exact-version, preview/apply, review, and read-back gates remain mandatory.

## Required End State

- Codex and Claude provider configs contain only the minimal runtime-kit-owned
  dispatcher ingress required by provider capability, plus unrelated hooks that
  setup preserved.
- The dispatcher loads one validated config and an installed versioned policy
  bundle, evaluates runtime-kit rules deterministically, and emits the exact
  provider contract.
- Agent-session coordination and heartbeat/liveness evidence participate in
  semantic and physical writer decisions without exposing mailbox bodies,
  authorization text, raw session identifiers, or machine-local paths.
- Doctor and inventory commands distinguish dispatcher ingress, runtime-kit
  rules, unrelated provider hooks, unsupported provider capabilities, legacy
  residue, policy/config digests, and safe recovery actions.
- Legacy runtime-kit and agent-session registrations are removed only after
  rollback rehearsal and converged live read-back.
- #676 and #686 are closed only after merged-revision deployment and bounded
  fresh-session acceptance.

## Non-Goals

- Eliminating provider-native event delivery.
- Managing or deleting unrelated user, project, plugin, or provider-owned
  hooks.
- Claiming deterministic ordering outside `agent-hook`-owned rules.
- Treating hooks as a security sandbox.
- Replacing formal L3 dispatch with the #676 mailbox.
- Adding repository-local hook configuration or executable user-defined rules
  in v1.

## Execution and Retention

- Recommended plan:
  `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-plan.md`
- Recommended execution state:
  `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-execution-state.md`
- Retain the source, plan, and terminal execution state under `docs/plans/` as
  the durable cross-repository implementation record. Keep machine-specific
  deployment and acceptance artifacts in the private runtime evidence tree.
