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
generation checks preserve a newer marker from a concurrent edit.
Tombstones use a stable lexical contract identity plus product-scoped target
keys that include the declared command. A newer attempt reduces only the exact
matching targets; removed, replaced, or reordered commands become an explicit
contract-change blocker. Each tombstone also retains the original shared edit
generation (or an explicit no-edit value), so another product sees a real edit
without inheriting its failure or being invalidated by retries for the same
edit. Unmatched contract state remains scoped to its owning product. Each
product can therefore release its own commands with newer success evidence
while another product's unresolved failure remains blocked.
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
`project-dev` for every canonical target repository before direct edits. Bash
is gated against its working repository because a pre-tool payload cannot
reliably expose shell-expanded destinations; cross-repository shell mutations
must run with each target repository as CWD. Only a successfully probed,
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

Install surfaces:

- Codex: `targets/codex/link-map.yaml` installs shared scripts under
  `$CODEX_HOME/hooks/` and syncs the managed hook block into
  `$CODEX_HOME/config.toml`.
- Claude: `targets/claude/link-map.yaml` installs shared scripts under
  `$HOME/.claude/hooks/`; `core/hooks/claude/settings.hooks.jsonc` is the
  source fragment for the settings `hooks` block.
