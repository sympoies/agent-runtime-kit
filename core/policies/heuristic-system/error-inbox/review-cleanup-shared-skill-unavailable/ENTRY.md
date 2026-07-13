# Private review-cleanup adapter depends on a retired shared skill

## Status

- Status: open
- First observed: 2026-07-13
- Area: private review cleanup and shared PR workflow packaging
- Severity: medium

## Signal

The machine-local `private-review-cleanup` adapter declares that
`pr:review-thread-cleanup` is available and routes every candidate through it,
but that shared skill is absent from the active Codex catalog. The workflow
completed only by applying the thread-convergence contract directly with
`forge-cli` plus the retained `deliver-pr` and specialist-review surfaces.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/sympoies__nils-cli/20260713-195144-skill-usage-review-cleanup/skill-usage.record.json`
- Runtime surface: nils-cli `1.21.29`, observed 2026-07-13.
- Repository evidence: `manifests/retired-skill-ids.json` retires
  `pr.review-thread-cleanup`; `manifests/skill-dispositions.yaml` declares its
  replacement as `pr.deliver-pr` and says cleanup is an internal delivery
  phase.
- Upstream issue: none found; the retirement and replacement are already
  explicit in the governed manifests.

Minimal reproduction:

1. Start a fresh Codex session with the current managed and private skill
   surfaces.
2. Invoke `private-review-cleanup` for a repository with unresolved threads.
3. Observe that the adapter-required `pr:review-thread-cleanup` skill is not in
   the active catalog, even though its `SKILL.md` says that dependency is
   available.

## Impact

The advertised top-level cleanup path cannot execute as written. Agents must
reconstruct the retired orchestration manually, which risks skipping the
convergence policy, specialist follow-up, or final unresolved-thread gate.

## Current Workaround

Use the current `forge-cli pr review-threads` mechanics, the shared
review-thread convergence policy, specialist follow-up mode, and `deliver-pr`
terminal gates directly. This completed the nils-cli sweep with zero unresolved
threads on all affected PRs.

## Promotion Criteria

Promote after the private adapter no longer names the retired skill and a fresh
session proves discovery, triage, fix/reply/resolve, follow-up review, and final
convergence through supported active surfaces.

## Next Action

Update the private adapter to use the active `deliver-pr`,
`code-review-specialists`, convergence-policy, and `forge-cli` surfaces instead
of restoring the intentionally retired skill; then run a fresh-session cleanup
acceptance.
