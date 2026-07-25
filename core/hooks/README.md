# Runtime Hooks

`core/hooks/shared/` is the canonical source for hook logic shared by Codex and
Claude. `core/policies/agent-hook/runtime-kit-v1.toml` owns selection and
ordering; `agent-hook setup` owns the provider-native ingress.

The shared scripts accept neutral `AGENT_RUNTIME_*` environment variables. Do
not fork a hook per product unless the payload protocol or runtime harness
requires different behavior.

The finish-line hooks credit declared validation only after an observed
successful exit. `PreToolUse` wraps each matched Bash command with a tokenized
EXIT recorder that persists bounded outcome metadata and preserves the
command's status. Composite commands are credited only when their shell
control flow consists entirely of declared validation commands, because an
input rewrite also grants permission to the complete rewritten command. The
authorization matcher retains operator and evaluation-sensitive quote syntax
while normalizing harmless quoted words, so a quoted literal cannot be
reinterpreted as live shell control flow.
Attempts are ordered at PreToolUse creation, so a stale completion cannot
overwrite a newer attempt; an outcome that cannot persist leaves its pending
attempt blocking the gate. A bounded recovery descriptor travels with the
wrapper so removal of the pending directory recreates authoritative dirty and
failure state. Each active attempt also has an authoritative tombstone under
shared runtime state (`AGENT_RUNTIME_VALIDATION_STATE_HOME`, then
`AGENT_RUNTIME_STATE_HOME`, then the XDG state root). It remains blocking when
repo-local state cannot persist; if either side cannot register before launch,
the matching validation command is blocked and can be retried after repair.
Code-edit hooks are also fail-closed before the edit starts when shared dirty
state cannot be registered, preventing an unwritable marker directory from
hiding a later real edit. Multi-contract edits acquire every marker-directory
lock in stable order and roll back provisional markers if any write fails;
generation checks preserve a newer marker from a concurrent edit. A
repo-scoped runtime-state lock serializes edit, validation-outcome, Stop, and
terminal-cleanup transitions; cleanup also compares the exact satisfied state
snapshot after taking the local namespace lock and fails closed on change.
Tombstones use a stable lexical contract identity plus target keys that include
the product and declared command. When the hook payload identifies a runtime
session, dirty markers, command outcomes, and tombstones live in directly
addressable namespaces keyed by an opaque hash of that session identifier, so
unrelated retained state is not scanned on the current session's hot path. An
editing session still
shares its dirty generation across products, but unrelated and newly started
sessions do not inherit its outstanding session-scoped work. Unresolved
pre-upgrade legacy state remains transitional authority until an identified
session completes a newer successful validation. Pending or failed transition
attempts retain the legacy authority; success clears it or suppresses it with
the shared success marker. Payloads without a session
identifier retain the legacy shared marker contract. A newer attempt reduces
only its exact session and command targets, plus matching legacy targets during
that transition; it cannot clear another identified session's state.
Successful Stop retires the completed session's repo-local marker namespace.
When products share a session, terminal product markers let the last successful
product retire the whole namespace. Any later shared edit invalidates every
product's terminal marker, and a new validation attempt invalidates its active
product's terminal marker until the attempt completes. Cleanup also rejects a
foreign terminal generation older than the current dirty generation; any
foreign evidence owner is parsed from its complete contract stem and structured
product suffix, with unknown or ambiguous names retained fail-closed. Any
unresolved product therefore keeps the namespace fail-closed. Removed,
replaced, or reordered commands become an explicit contract-change blocker.
Only the exact internal names `.terminal-codex`, `.terminal-claude`, and
`.terminal-shared` are terminal metadata; validation contract stems may safely
begin with `.terminal-` or overlap another contract stem.
Each tombstone also retains the original edit generation (or an explicit
no-edit value), so another product in the same session sees a real edit without
inheriting its failure or being invalidated by retries for the same edit.
Unmatched contract state remains scoped to its owning product.
Marker paths and their derived state directory must remain beneath the real
repository root; atomic marker writes do not follow final symlinks, and marker
ordering accepts only non-symlink regular files.
The wrapped shell's `EXIT` trap is the only outcome recorder; there is no broad
PostToolUse hook on ordinary Bash completions. Equivalent persistence-failure
blockers are compacted under a shared lock so fail-closed state remains bounded.
A failed outcome stays outstanding and the Stop gate proposes owner-based
routing before honoring a validation waiver. The hooks retain neither raw
command output nor provider artifacts and never open an issue automatically.

Selective intent activation is available when the installed `agent-docs`
exposes durable `session activate/status/verify`. `user-prompt-agent-docs.sh`
expands required docs for active intents and lists inactive routes without
injecting their runbooks. `pre-edit-intent-gate.py` then checks `project-dev`
for every canonical target repository before direct edits and against the
shared shell command context.

`AGENT_RUNTIME_PROJECT_DEV_MODE` selects `advisory` (the default), `enforce`, or
`off`. Advisory mode attempts one bounded exact preparation for each unprepared
attested target and allows the original work whether preparation succeeds or
not. Successful auto-preparation includes the exact, phase-qualified
`agent-docs preflight --intent project-dev` command to read the prepared
contract; failures use `project-dev-advisory-unavailable` plus exact recovery
when available. A preparation near miss in advisory mode is not consumed as a
trusted bootstrap and executes normally with corrected bootstrap guidance;
enforce mode blocks the same near miss before execution. Invalid mode values
deterministically degrade to advisory. Enforce retains fail-closed verification
and target-specific recovery. Off disables only this project-dev workflow
check; checkout ownership, work-context coordination, validation,
delivery/signing, credential-protection, provider, OS, and user-authority hooks
still run.

Direct edits discover and verify each explicit target independently. Bash uses
a host-attested command workdir: Codex inline metadata, a matching bounded
transcript call, provider session cwd, or the exact cwd in a ready private
`agent-session` record whose session id and runtime incarnation match the hook
process. This last route keeps a target-rooted Claude worker usable when its
Bash envelope omits cwd or its current call has not yet been flushed to the
transcript. The managed record may only attest the same physical process cwd;
it cannot redirect the target. A plain process-cwd or unauthenticated
mismatched-call fallback is recorded as un-attested and receives
`workdir-attestation-missing` instead of silently becoming a cross-repository
target. Its message tells the agent not to repeat unchanged Bash and names the
supported Codex workdir, managed
target-rooted session, and exact-path edit routes. Shell-expanded
destinations remain unobservable. A shell-embedded `agent-run exec --cwd`
cross-repository hop stays fail-closed in enforce mode with
`cross-repository-target-unsupported`; V1 requires a target-rooted session or
host-attested workdir. Admitting that wrapper later requires a typed nils-cli
command-context primitive that binds release provenance, canonical cwd, wrapper
grammar, and child argv once for every mutation-sensitive guard.
Recovery diagnostics make that route operational: resubmit the mutation as a
standalone tool call whose top-level `workdir` is the target checkout; for
staging, run `git add -- <owned-paths>` there and invoke `semantic-commit`
separately. They explicitly reject shell `cd`, raw `git -C`, and nested
`agent-run exec --cwd` as substitutes, and name a target-rooted managed session
as the fallback when the host cannot attest a target workdir.
Exact help/version argv for the
managed `agent-docs` and `forge-cli` release surface remains read-only, while
extra options, trailing arguments, and executable shadows fail closed. When
verification blocks a single-repository edit or shell mutation, the reason
includes a complete, copyable `session prepare` command — the atomic
activate-plus-strict-preflight primitive — with the trusted executable and
session context. A successful in-hook prepare keeps `[reason: prepared]` and
adds `[action: retry-original]`: do not run the prepare command again; retry the
original blocked command. The older `session activate` bootstrap remains accepted for
backward compatibility. Only a successfully probed,
explicitly versioned pre-session `agent-docs` release retains compatibility
behavior; a missing, timed-out, crashed, malformed, or on-floor binary without
the session surface fails closed. Before any probe, the hooks require the
resolved `agent-docs` executable to live in a known managed CLI directory
(`/opt/homebrew/bin`, `/home/linuxbrew/.linuxbrew/bin`, `/usr/local/bin`,
or `/usr/bin`); Homebrew links must resolve under that prefix's
`Cellar/nils-cli` package. A custom installation requires an explicit
launch-time
`AGENT_RUNTIME_TRUSTED_CLI_ROOT`; repository-local candidates are always
rejected. These hooks are mechanical guardrails, not a security sandbox: the
product launch environment, managed runtime home, and an explicit trusted-root
override remain host trust boundaries. Hermes has no runtime-kit hook runner.

The shared `command_context` helper in `hook_common.py` resolves the canonical
working directory, source, attestation, and optional stable diagnostic for a
tool call. Its `effective_workdir` compatibility wrapper means
`pre-edit-intent-gate.py`,
`checkout-lease-guard.py`, `block-unsafe-default-delivery.py`,
`agent-scope-lock-guard.py`, and `block-direct-python.py` all agree on the
target repository instead of each reading the hook process cwd (issue #601
P0-4). It fans out across the union of Codex and Claude tool envelopes: explicit
workdir keys (`workdir`, `cwd`, `current_working_directory`,
`working_directory`) nested anywhere in the tool input; then the Codex
`exec_command` transcript, whose `arguments` carry the `workdir` in the event
matching this call's `tool_use_id`/`call_id`; then non-session payload metadata;
then the top-level session `cwd`; then a bounded 64 KiB private managed-session
record whose id, agent, ready state, runtime incarnation, owner/mode, and cwd all
match the current hook process; and finally process cwd. Absolute inline,
matching-transcript, payload, ordinary session-cwd, and authenticated
managed-session-cwd values are attested. Relative values and plain process cwd
are not. A transcript-call mismatch keeps payload/session cwd un-attested, but
does not suppress an independently authenticated managed-session cwd matching
that same resolved path. The transcript tail remains capped at 4 MiB.
Direct-edit verification stays target-based; shell verification is
command-context based.

`checkout-lease-guard.py` coordinates one writer per physical Git checkout
across Codex and Claude only when the managed launch explicitly selects
`AGENT_SESSION_COORDINATION_MODE=enforce`. Missing, invalid, `advisory`, and
`off` modes bypass the lease without acquiring or blocking, so ordinary
iTerm-launched agents remain valid non-participants. In enforce mode, explicit
edit tools participate; Bash
participates only for conservative high-confidence mutations, including known
nested shell / `agent-run exec` forms and managed worktree removal, so read-only
recovery remains available. In particular, `semantic-commit` help and dry-run
forms do not acquire a writer lease unless the command includes the
file-writing `--message-out` option. Managed worktree slugs resolve through the
authoritative `git-cli` inventory, and removal must be the command's sole
mutation with exactly one removal target. Nested repositories and submodules
retain independent lease boundaries. A clean linked worktree may acquire a
lease. The primary checkout may acquire one only while clean, on its resolved
default branch, and outside a pre-existing Git operation. The owning session
refreshes the lease after its own edits; live foreign ownership and unowned
dirty state block with managed-worktree guidance. Lease files contain hashed
session identity,
timestamps, and local checkout identity paths under shared XDG runtime state;
they never retain the raw session identifier. A random sentinel under the
checkout's Git admin directory distinguishes a removed/recreated linked
worktree at the same path. Expired leases are reclaimable only while clean;
`AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS` tunes the eight-hour default. Stop
releases clean matching owner leases across the current repository and prunes
lease state for physically removed worktrees while retaining the stable
per-checkout lock inode; dirty or mismatched ownership is retained and reported.
Stop never removes a worktree, branch, commit, or dirty file.

`session-coordination-guard.py` is a separate semantic awareness layer for
managed Codex and Claude launches. `advisory` is the default when the mode is
missing or invalid. Broker-ready sessions automatically participate through
presence; recognized mutations call privacy-safe `work-context advise` and may
emit fixed informational, overlap, or degraded-availability guidance, but never
block the tool call. Audited read-only argv shapes and pipe-only pipelines whose
every stage is audited stay silent. Unknown shell effects also stay silent in
advisory mode instead of being presented as observed mutations; strict
`enforce` admission remains fail-closed for them. The shared tri-state shell
effect result is `read-only`, `mutation`, or `unknown`; redirection, command
substitution, unsafe stages, executable shadows, and shell control other than a
plain pipe never receive the read-only result. `work-context set|clear` can add
optional bounded task context without requiring session IDs, capability
arguments, revision numbers, or a pre-written JSON file. `work-context
acknowledge` suppresses only the
most recently observed overlap for a bounded incarnation-specific window;
changed peers, reasons, repositories, or availability warn again, while target
churn covered by the same overlap stays quiet and explicit advice retains the
reasons. `off` and unmanaged launches are silent.

When a managed launch explicitly selects `enforce` and provides
`AGENT_SESSION_ID`, `AGENT_SESSION_CAPABILITY_FILE`, and
`AGENT_SESSION_STATE_DIR` on the released v1.24.5 surface, recognized direct
edits, repository shell mutations, and exact provider mutations require an
authenticated active work context and atomic operation lease. Direct edits
carry every repository-relative target; simple shell effects require repository
scope; compound or otherwise opaque shell effects, explicit cross-repository
destinations, commands outside a
governed repository, wrapped provider clients, and unresolved provider targets
fail closed. Provider `--repo`/`-R` overrides bind the effective provider
reference rather than the hook checkout. Nested `sh`/`bash`/`zsh` command
strings are unwrapped before destination checks, and Git forms that may invoke
configured fsmonitor, pager, external-diff, or filter programs do not bypass
admission. A definite peer conflict and
uncovered or uncertain own scope block, while potential/unknown/no-known-
conflict classifications remain bounded advisories. PostTool success/failure
is durably recorded before runtime probes and completes the exact token-bound
lease. Admission intent, replay key, token, targets, and completion proof remain
in a mode-0600 hashed session namespace across timeouts for exact duplicate/Stop
replay rather than being guessed or released. Same-call Pre/Post/Stop activity
is serialized by a stable local lock. `agent-hook` evaluates every ordinary
rule first and invokes the locked `agent-session.coordination.v1` capability
only after an aggregate allow, so neither provider can admit a tool denied by
another prerequisite. The guard applies one 50-second global subprocess budget
inside the setup-owned dispatcher timeout. In advisory mode,
older/missing coordination surfaces remain usable with bounded degraded
guidance; in enforce mode they retain accurate no-enforcement guidance. Hook
output never includes
raw session/capability/incarnation/checkout values, peer summaries, mailbox
bodies, or private registry paths. The physical checkout lease above shares the
same explicit enforce-mode boundary, and Hermes still has no runtime-kit hook
runner.

Executable runtime rules use independent child deadlines and an explicit
`timeout_posture`. A timeout no longer erases completed outcomes or skips later
mandatory rules. Allowed `warn` or `effect_gated` timeouts create mode-0600,
redacted incidents under the XDG state `agent-hook/degraded` tree; terminal
PostTool success/failure correlates them without retaining raw commands,
paths, prompts, or provider identifiers. A bounded summary keyed by policy,
rule, error, effect, product, and platform aggregates recurrence and the latest
completion. Completed blocks and closed/unknown effect outcomes remain
authoritative.

Dirty-checkout adoption is an opt-in advisory layered over the enforce-mode
checkout gate. With `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION` set to `1` and
coordination mode set to `enforce`, a dirty
`UserPromptSubmit` may use released `git-cli worktree dirty-snapshot` to issue a
mode-0600, one-time, five-minute bearer challenge bound to the exact repository,
checkout instance, session digest, authorization-turn digest, HEAD/branch state,
and content snapshot. The private context keeps Q&A read-only and asks the agent
to obtain explicit takeover authorization or use `git-cli worktree add`; it does
not parse natural-language authorization or adopt automatically. Snapshot failure,
unsupported state, malformed output, an active Git operation, or existing lease
makes the advisory silent while later file/index mutation continues to fail
closed.

After exact authorization, the PreToolUse gate admits the transition only through
the resolved managed `git-cli` executable and only when the private challenge or
adopted receipt belongs to the current agent session. Released `git-cli worktree
adopt-dirty` then rechecks and consumes the challenge under the lease lock, and
publishes one privacy-safe receipt and an adopted lease-v2 record in the same
transaction. The strict embedded lease-v2 adoption block is the guard's
authoritative provenance input; it preserves receipt ID/schema, snapshot ID,
authorization-turn and reason digests, adoption time, and challenge issue time
across same-session refresh. `git-cli worktree revoke-dirty` removes only
matching receipt-bound ownership and never changes checkout content. Challenge
records, adoption-provenance fields, and provider-visible evidence exclude raw
prompts, bearer values, reason text, filenames, paths, diffs, and file contents,
and require this one-time value to remain private.

A separate dirty-checkout exception admits only one recognized ref-only operation
through the resolved `git` executable: selected branch delete/move/copy forms, or
tag deletion and lightweight/forced tag creation with explicit `--no-sign`. It
mints no lease, requires a valid session and safe checkout state, and remains
blocked by live foreign ownership, stale/unowned lease state, Git operations,
an executable `reference-transaction` hook, or an off-default primary checkout.
Redirects, dynamic arguments, command-local Git/executable retargeting, compound
mutations, and every co-resident working-tree/index write are rejected. File and
index protection remains unconditional for staged, unstaged, and untracked-only
dirt. Codex and Claude register the shared guard on `UserPromptSubmit`; Hermes
has no runtime-kit hook runner and does not support this enforcement.

`block-unsafe-default-delivery.py` owns the shell-side delivery-mode boundary.
It resolves the selected remote's cached local default branch and blocks raw `git push`
forms that target it, including force, force-with-lease, deletion, wildcard,
matching-branch (`:` / `+:`), and implicit current-default pushes. It also
blocks mutating
`semantic-commit commit`, `fixup`, and `squash` on the default branch of the
repository that invocation actually commits in. Ambiguous
pushes without an explicit refspec fail closed because Git configuration can
retarget them. PreToolUse performs no live `ls-remote` or provider probe;
implicit, all/mirror, delete, matching, wildcard, and missing-cache cases fail
closed, while live remote truth remains owned by the delivery CLI. It leaves explicit feature-branch pushes,
`git push --dry-run`, semantic-commit help/dry-run, and the governed `forge-cli
repo push-default` invocation available. Exact authorized `semantic-commit
local-default` is also admitted when expected branch/head and the outside-repo
receipt destination are statically visible; ordinary default-branch commit
forms remain blocked. A `semantic-commit` target resolves from `--repo` or from
a literal absolute `cd` in the same command, so a cross-repository invocation is
classified against the repository it mutates rather than the tool workdir; a
relative or expanded destination, a nested shell, and any command-local
`GIT_*`/`HOME` override fail closed, and raw Git still fails closed after every
shell-context change. A blocked verdict names the resolved repository, how it
resolved, and the first failing precondition. When a `semantic-commit` target
stays unresolvable, one command may state a reason inline as
`AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER=<reason>`; that is handler admission, not
a rule override, and it never reaches a proven default-branch target or a raw
Git path. Hook admission is intentionally independent of cached
upstream ancestry: `semantic-commit local-default` owns the aligned/ahead-only
proof and rejects behind, diverged, or unknown relations. The hook is a
guardrail rather than a shell sandbox; provider rules and the forge-cli
expected-base, one-signed-commit, verified-fast-forward, exact-old-object
compare-and-swap, and post-push read-back contract are authoritative. The
internal exact lease does not make raw or caller-controlled
`--force-with-lease` an allowed route. Hermes has no runtime-kit hook runner.

Install surfaces:

- Codex: `targets/codex/link-map.yaml` installs shared scripts under
  `$CODEX_HOME/hooks/`; its legacy managed hook block is intentionally empty.
- Claude: `targets/claude/link-map.yaml` installs shared scripts under
  `$HOME/.claude/hooks/`; its legacy settings fragment is intentionally
  empty.
- `scripts/sync-runtime-surfaces.sh` installs the shared digest-pinned policy
  and delegates exact Codex/Claude provider ingress to `agent-hook setup`.
