# Runtime Hooks

`core/hooks/shared/` is the canonical source for hook logic shared by Codex and
Claude. Product-specific activation stays in `targets/<product>/hooks/` and in
the product link map.

The shared scripts accept neutral `AGENT_RUNTIME_*` environment variables. Do
not fork a hook per product unless the payload protocol or runtime harness
requires different behavior.

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
the session surface fails closed. These hooks are mechanical guardrails, not a
security sandbox: the product launch environment, managed runtime home, and its
resolved executable `PATH` are host trust boundaries. Hermes has no runtime-kit
hook runner.

Install surfaces:

- Codex: `targets/codex/link-map.yaml` installs shared scripts under
  `$CODEX_HOME/hooks/` and syncs the managed hook block into
  `$CODEX_HOME/config.toml`.
- Claude: `targets/claude/link-map.yaml` installs shared scripts under
  `$HOME/.claude/hooks/`; `core/hooks/claude/settings.hooks.jsonc` is the
  source fragment for the settings `hooks` block.
