# Active session skill catalog references pruned retired paths

## Status

- Status: open
- First observed: 2026-07-12
- Area: runtime
- Severity: medium

## Signal

During a long-running Codex session, the injected available-skills catalog
listed several skills that were retired by the capability-convergence change
while the session was still active. Later attempts to follow those catalog
entries failed because their cached `SKILL.md` paths no longer existed. The
affected entries included `heuristic-session-closeout`, `semantic-commit`,
`test-first-evidence`, `agent-out`, and the pre-merge review gate.

## Evidence

- Raw record: not captured; the signal is a catalog/path consistency failure,
  not user or provider data.
- Repository state: the affected IDs are present in
  `manifests/retired-skill-ids.json` and their CLI replacements are declared in
  `manifests/skill-dispositions.yaml`.
- Runtime observation: the session catalog still named the retired skill paths,
  while filesystem reads returned missing; the replacement CLIs remained
  installed and usable.

## Impact

An active agent is required to read a selected `SKILL.md` completely before
acting, but cannot satisfy that contract after the file is pruned. This forces
ad hoc fallback reasoning, creates false "missing skill" warnings, and can
interrupt closeout or delivery in sessions that overlap a runtime sync.

## Current Workaround

Confirm the skill ID is declared retired, read its CLI replacement from
`manifests/skill-dispositions.yaml`, and use the installed released CLI plus
the governing policy. Do not infer a replacement for an ID that is not present
in the retirement manifest.

## Promotion Criteria

Promote when runtime convergence either preserves retired cache files for the
lifetime of active sessions, makes the injected catalog immutable and
self-contained, or provides a deterministic retired-skill fallback that an
active session can resolve without reading a removed path. Cover a session that
starts before retirement and invokes the entry after convergence.

## Next Action

Define a session-safe retirement or fallback contract so injected catalogs
never point to files removed before the session ends.
