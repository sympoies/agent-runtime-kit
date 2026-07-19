# Runtime Hooks

`core/hooks/shared/` is the canonical source for hook logic shared by Codex and
Claude. Product-specific activation stays in `targets/<product>/hooks/` and in
the product link map.

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

Selective intent activation is enforced only when the installed `agent-docs`
exposes durable `session activate/status/verify`. `user-prompt-agent-docs.sh`
expands required docs for active intents and lists inactive routes without
injecting their runbooks. `pre-edit-intent-gate.py` then verifies
`project-dev` for every canonical target repository before direct edits. Direct
edits are gated against each explicit edit target; Bash is gated against its
effective working repository, resolved through the shared `effective_workdir`
helper (see below) rather than the hook process cwd. A pre-tool payload still
cannot reliably expose shell-expanded destinations, so cross-repository shell
mutations must run with each target repository as their effective workdir. When
verification blocks a single-repository edit or shell mutation, the reason
includes a complete, copyable `session prepare` command — the atomic
activate-plus-strict-preflight primitive — with the trusted executable and
session context; the older `session activate` bootstrap remains accepted for
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

The shared `effective_workdir` helper in `hook_common.py` resolves the working
directory a tool call actually runs in, so `pre-edit-intent-gate.py`,
`checkout-lease-guard.py`, `block-unsafe-default-delivery.py`,
`agent-scope-lock-guard.py`, and `block-direct-python.py` all agree on the
target repository instead of each reading the hook process cwd (issue #601
P0-4). It fans out across the union of Codex and Claude tool envelopes: explicit
workdir keys (`workdir`, `cwd`, `current_working_directory`,
`working_directory`) nested anywhere in the tool input; then the Codex
`exec_command` transcript, whose `arguments` carry the `workdir` in the
transcript event matching this call's `tool_use_id`/`call_id`; then workdir keys
anywhere in the payload; then the top-level `cwd`; and finally the hook process
cwd. Claude submits the session `cwd` and no per-command workdir, so a Claude
command resolves to the session directory; a Codex command submitted with an
out-of-repo `workdir` resolves to that directory, not the launch repository.
Direct-edit verification stays target-based (each edit path's repository);
shell verification is working-repository-based on this effective workdir.

`checkout-lease-guard.py` coordinates one writer per physical Git checkout
across Codex and Claude. Explicit edit tools always participate; Bash
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

`block-unsafe-default-delivery.py` owns the shell-side delivery-mode boundary.
It resolves the selected remote's default branch and blocks live raw `git push`
forms that target it, including force, force-with-lease, deletion, wildcard,
matching-branch (`:` / `+:`), and implicit current-default pushes. It also
blocks mutating
`semantic-commit commit`, `fixup`, and `squash` on the checked-out default
branch. Ambiguous live
pushes without an explicit refspec fail closed because Git configuration can
retarget them. When the live default-branch probe exhausts its bounded deadline,
the hook may use the cached remote HEAD only for exact explicit branch refspecs;
implicit, all/mirror, delete, matching, wildcard, missing-cache, and non-timeout
failure cases still fail closed, and a completed live probe must agree with the
cache. It leaves explicit feature-branch pushes,
`git push --dry-run`, semantic-commit help/dry-run, and the governed `forge-cli
repo push-default` invocation available. The hook is a guardrail rather than a
shell sandbox; provider rules and the forge-cli expected-base, one-signed-commit,
verified-fast-forward, exact-old-object compare-and-swap, and post-push
read-back contract are authoritative. The internal exact lease does not make
raw or caller-controlled `--force-with-lease` an allowed route. Hermes has no
runtime-kit hook runner.

Install surfaces:

- Codex: `targets/codex/link-map.yaml` installs shared scripts under
  `$CODEX_HOME/hooks/` and syncs the managed hook block into
  `$CODEX_HOME/config.toml`.
- Claude: `targets/claude/link-map.yaml` installs shared scripts under
  `$HOME/.claude/hooks/`; `core/hooks/claude/settings.hooks.jsonc` is the
  source fragment for the settings `hooks` block.
