# codex exec can report success after subagent thread creation fails

## Status

- Status: open
- First observed: 2026-07-11
- Area: Codex CLI multi-agent orchestration and live subagent acceptance
- Severity: medium

## Signal

After a successful `sync-runtime-surfaces` deployment, a Codex CLI 0.144.1
`codex exec --ephemeral --json` smoke explicitly requested `reviewer-quick`.
The JSONL stream logged `collab spawn failed: no thread with id`, then waited
with an empty receiver set and still returned `QUICK_OK`. A non-ephemeral retry
again waited with no receiver thread while reporting `QUICK_OK`.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/graysurf__agent-runtime-kit/20260711-231657-reviewer-model-tiers/skill-usage-sync-runtime/skill-usage.record.json`
- Summary: both hosts passed runtime sync doctor and prompt-input verification,
  exposed `gpt-5.6-sol` and `gpt-5.6-terra` in `codex debug models`, installed
  the expected reviewer TOML, and pointed at merge SHA `d895125`. The failure
  is isolated to live subagent-thread verification, not render or deployment.

## Impact

The command exits zero and the parent can emit the requested success token even
though no subagent result exists. A deployment or code-review acceptance check
that trusts only the final message can therefore produce a false positive.

## Current Workaround

Treat a live-spawn smoke as passing only when the event stream contains a
non-empty spawned receiver thread and its completed result. Until that is
reliable, combine sync doctor / prompt-input verification with model-catalog,
installed-agent TOML, and source-SHA checks; do not accept the parent's final
success token by itself.

## Promotion Criteria

Promote after the behavior is reproduced outside a nested Codex session and
either fixed upstream or covered by a deterministic acceptance check that
fails when no receiver thread is created.

## Next Action

Reproduce from a standalone terminal outside a parent Codex session; if confirmed, file an upstream Codex issue with the CLI version and redacted JSONL event sequence, then add a reliable live-spawn acceptance check.
