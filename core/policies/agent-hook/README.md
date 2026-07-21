# Runtime-kit agent-hook policy

This directory is the canonical runtime-kit policy source for `agent-hook`.
Provider-native configuration remains lifecycle ingress, but it does not own
runtime-kit rule behavior. The installed dispatcher evaluates the selected,
digest-pinned bundle under the user's
`${XDG_CONFIG_HOME:-$HOME/.config}/agent-hook/config.toml`.

`runtime-kit-v1.toml` is the first strict policy bundle. Its matching inventory
is `manifests/hook-rules.yaml`, stored as JSON-compatible YAML so the repository
can validate it without an additional parser dependency. The inventory records
every policy rule's behavior owner, recovery class, documentation, and test
owner. It freezes all 68 legacy Codex and Claude registrations across 22
shared handlers as the parity baseline, adds 18 typed coordination/liveness
rules, adds eight locked transaction rules, and adds one shared read-only
capability shadow rule for 95 rules total. Each
migrated handler remains a distinct ordered rule so the cutover proves provider
parity without changing grouped matchers or handler order.

## Evaluation boundary

Rules use only the built-in capability IDs frozen by the `agent-hook` v1
contract. Runtime-kit handler rules select one basename from the compiled
allowlist; policy cannot provide a path, interpreter, command, environment,
timeout, or arbitrary argument. Matchers are either one exact literal or an
anchored `|` alternation. The same expression represents one provider group.

The policy preserves the existing handler scripts as behavior owners.
`agent-hook` owns normalization, deterministic ordering,
aggregate decision precedence, rendering, redacted tracing, configuration
overrides, and governed recovery. The scripts continue to own their existing
state and output contracts until a separately tested typed capability replaces
them.

The shared Bash `execution.read-only.v1` rule is shadow-only. It asks the
released same-version verifier for evidence from exact `builtin command`
invocations of an absolute `agent-run`, `agent-docs`, or `forge-cli` producer,
but its result is trace evidence only. Legacy handlers remain the sole
production admission authority in this policy version. Raw local exploration
that mismatches the capability routes to `agent-run inspect`; managed queries
route through the exact tool-owned operation-effect contracts. No mismatch may
expand the legacy allowlist.

Priority ranges are local to a product/event/matcher group:

- `10`: authenticated agent-session activity recording.
- `20`: semantic-conflict admission from trusted coordination state.
- `30`: writer owner-liveness admission from trusted coordination state.
- `100` and above: legacy handlers in their current provider order, in steps
  of ten.
- `900`: locked `agent-session.coordination.v1` transaction lifecycle,
  after every ordinary rule in the selected group.

On `PreToolUse`, a blocking aggregate decision performs no coordination
admission. An allowed aggregate performs exactly one `admit`. Terminal
`PostToolUse`, `PostToolUseFailure`, and `Stop` events complete or
reconcile through the same typed capability after aggregation. The provider
never schedules coordination as a sibling hook. Coordination mode `off`
disables only that lifecycle/collision layer; unrelated privacy, validation,
checkout, and delivery rules remain active.

Only a definite conflict derived from an owner/mode-validated coordination
registry and fresh current broker/work context blocks semantic admission. A
provider payload field named `semantic_conflict` is untrusted and ignored.
Potential or incomplete evidence stays advisory. Active foreign writers block;
stale clean state may be reclaimed through the coordination owner; dirty,
orphaned, and unknown state stays visible and conservative. The bounded
five-minute legacy liveness TTL is compatibility evidence only and never the
primary ownership decision.

The lower-level checkout lease and existing privacy, transaction, validation,
and scope guards remain independent authorities. The coordination capabilities
classify ownership before those handlers run; they do not weaken or replace a
lower-level guard.

## Override and recovery classes

- `locked` rules are fail-closed and cannot be changed by ordinary config.
  They cover privacy, writer admission, transaction integrity, validation, and
  recovery-sensitive behavior.
- `downgrade-only` rules may move from `enforce` to `shadow` or `disabled`, but
  config cannot strengthen them or change typed parameters.
- `free` rules may change mode, while their rule identity and capability remain
  policy-owned.

An override is not an emergency bypass. Locked recovery requires a scoped,
short-lived `agent-hook` recovery capability bound to the exact operation and
state revision. The bearer remains private and is never stored in policy,
provider configuration, output, or trace data.

## Migration and rollback

`scripts/sync-runtime-surfaces.sh` installs the bundle at
`${XDG_DATA_HOME:-$HOME/.local/share}/agent-hook/policies/runtime-kit-v1.toml`
and updates only the `[policy]` selection in
`${XDG_CONFIG_HOME:-$HOME/.config}/agent-hook/config.toml`. Existing
`[providers]` modes and per-rule `[overrides]` remain user-owned.

The sync then uses `agent-hook setup` preview, exact
`data.plan_digest`-bound apply, and doctor for Codex and Claude. Setup
preserves unrelated hooks and Codex notification composition while rendering
one owned dispatcher group for every event/matcher combination. Rollback uses
the remove operation's own reviewed digest and removes only exact owned
ingress. Hermes shares the policy/config surface but truthfully remains an
unsupported native hook runner.

## Performance budget

Measure dispatcher overhead independently from handler execution with at least
30 warm iterations per provider/event shape. The v1 budget is p95 no greater
than 25 ms for normalization, selection, aggregation, rendering, and redacted
trace bookkeeping. End-to-end migrated rule chains must remain within 15% of
the corresponding direct-handler p95 baseline. A platform that misses either
budget cannot be promoted without a reviewed optimization or an explicit plan
waiver containing the measurements and impact.

Run the static owner suite with:

```bash
bash tests/agent-hook/run.sh
```

Run executable validation through `scripts/dev/with-nils-version.sh` against
the exact coupled nils-cli build. Do not change the pinned nils-cli surface or
run the full repository gate against an unreleased build.
