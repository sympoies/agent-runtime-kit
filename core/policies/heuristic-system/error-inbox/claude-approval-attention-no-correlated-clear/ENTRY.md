# Claude approval attention has no correlated clear

## Status

- Status: open
- First observed: 2026-07-25
- Area: agent-session-activity
- Severity: medium

## Signal

A Claude approval attention stays pending after the user has already answered
it. The nils-cli turn-state contract admits an exact `attention_cleared` only
for `AskUserQuestion` (correlated by `tool_use_id`) and `ElicitationResult`. A
generic approval carries no correlated clear, so it keeps a conservative latch
until turn completion, a new turn, or a new runtime. Positive `progress` never
clears attention by design.

## Evidence

- Raw record: `evidence/attention-journal.md`
- Summary: redacted activity-journal excerpt with attention event kinds and
  timestamps only; no prompt, answer, command, or transcript text, and attention
  ids truncated. It shows an exact clarification clearing on answer while the
  uncorrelated approval raised six seconds later for the same interaction stayed
  pending.
- Producer authority is stated in nils-cli
  `crates/agent-session/docs/turn-state-contract.md` under "Attention
  correlation authority", and the event mapping in
  `crates/agent-hook/src/adapter.rs`.
- The separate ingress-registration defect found in the same session is already
  fixed here by `coord.claude.pre-tool-use.ask-user-question.activity`,
  `coord.claude.post-tool.ask-user-question.activity`, and
  `coord.claude.permission-request.activity` in
  `core/policies/agent-hook/runtime-kit-v1.toml`. This entry tracks only the
  remaining producer-side gap.

## Impact

In any session that does not run with bypassed permissions, an answered
permission dialog can leave a stale pending-input cue visible for the rest of a
turn. Consumers such as Agent Console cannot resolve it: client dismissal is
presentation-only fingerprint suppression and cannot clear producer-owned
attention.

## Current Workaround

Exact clarification and elicitation flows now clear on answer. For a generic
approval, dismiss the cue in the client (presentation-only) or wait for turn
completion.

## Promotion Criteria

Promote after nils-cli either admits a correlated clear for an answered
permission request or records an explicit accepted-risk decision in the
turn-state contract.

## Next Action

Open a nils-cli issue when provider access is restored; the GitHub account is
currently blocked (`HTTP 403`, application marked as spammy), so no issue or
pull request can be filed. Until then this entry is the durable record.
