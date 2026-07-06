# Skill removal pushed from a worktree deadlocks ci-gate-stack on live-install audit-drift

## Status

- Status: promoted
- First observed: 2026-06-14
- Area: runtime
- Severity: medium

## Signal

While pushing the test-first gate consumption PR (which removed the
`conversation.test-first` skill), the `ci-gate-stack` pre-push hook
(`bash scripts/ci/all.sh`) failed at position 7:

```
audit-drift [extra/warn/codex] skills/conversation/test-first: live runtime surface exists under an install-map root but is not tracked by the install map
... (and the analogous claude / plugin-tree surfaces)
audit-drift: 25 finding(s); highest-severity exit=1
```

## Evidence

- Raw record: `evidence/prepush-gate.md` (ingested console output from the
  failed `ci-gate-stack` pre-push run, the `prune-stale` foreign-symlink skip,
  and the block-tier audit; manual diagnosis 2026-06-14, no structured
  skill-usage record captured).
- Versions: agent-runtime / forge-cli 1.2.0; agent-runtime-kit at the
  test-first-gate-consume branch.
- Root cause: a skill **removal** pushed from a linked git worktree deadlocks
  the pre-push gate. The worktree's install map no longer lists the removed
  skill, but the live `~/.codex` / `~/.claude` homes still carry it because they
  are managed by the **primary checkout on `main`** (which still has the skill
  until the PR merges). `agent-runtime audit-drift` (default `--fail-on warn`)
  flags those live surfaces as `extra/warn`, and `set -e` in `all.sh` makes the
  warn fail the gate.
- Why it can't be cleared pre-merge: `agent-runtime prune-stale` refuses the
  live surfaces as "foreign symlinks" (they target the primary build, not the
  worktree build), and `sync-runtime-surfaces.sh --apply` must run from the
  primary checkout — which can't drop the skill until the removal is on `main`.
  So live-vs-worktree drift is unavoidable for an unmerged removal.
- Confirmation that repo content is clean: `agent-runtime audit-drift
  --fail-on block` exits 0 (zero block-tier findings); all other `all.sh`
  positions (1-6, 8-13) pass; and the GitHub `all.sh` run on a clean checkout
  (no live install) passed (PR #335, run success in ~1m).

## Impact

Any skill-removal PR pushed from a worktree is blocked by the local pre-push
gate, even when the repo content is correct and CI will pass. Forces a
guardrail bypass.

## Current Workaround

Push the removal with `LEFTHOOK_EXCLUDE=ci-gate-stack` (keeps the
`signed-commits` hook), then deliver; the GitHub `all.sh` check on a clean
checkout is the authoritative full-gate run. After merge, run
`scripts/sync-runtime-surfaces.sh --apply` from the primary checkout to prune
the now-stale live surfaces — that clears the drift permanently (verified:
`audit-drift` returns clean, exit 0).

## Promotion Criteria

Promote once the pre-push gate distinguishes "live-vs-source drift for an
unmerged removal" from real source-vs-rendered drift — e.g. the gate's
audit-drift step runs `--fail-on block` for the live (rendered-vs-live) tier,
or excludes live-install roots when invoked from a linked worktree, so a
correct removal pushes without a manual bypass.

## Next Action

None. Local pre-push now marks scripts/ci/all.sh with AGENT_RUNTIME_KIT_HOOK_PHASE=pre-push, and the audit-drift gate allows only linked-worktree live-install extra/warn findings while keeping all other source/rendered drift strict; documented in docs/source/local-git-hooks.md.

## Archive

- Archived: 2026-07-06
- Reason: Resolved by scoped linked-worktree pre-push audit-drift handling for live-install extra/warn findings.
- Durable link: `lefthook.yml`
