# docs/discussions

Captured discussion / implementation-readiness specs — the default output of the
`discussion-to-implementation-doc` skill.

**This directory is staging, not storage.** Nothing is archived here and nothing
is kept here. A capture lives here only until it reaches an exit.

- One dated file per capture: `docs/discussions/<YYYY-MM-DD>-<slug>.md`.
- Every capture declares an `Exit:` in its header, chosen when it is written and
  executed by the PR that ships the work.
- Not scanned by `plan-tooling` / `plan-archive`. Captures are never archived;
  the durable record is the issue, the PR, the devlog entry, or promoted canon.

## Exits

Exactly one of four, and all four move or delete the file:

| `Exit:` | Action |
| --- | --- |
| `open-issue` | Open an issue for the outstanding work, then delete the capture. An ordinary issue is enough — do not manufacture an L1/L2 plan to justify the exit. |
| `promote-to-plan` | Move into `docs/plans/<YYYY-MM-DD>-<slug>/<slug>-discussion-source.md` and author the plan bundle. |
| `canonise` | Move into the owning domain doc, or `docs/source/` for repo-wide architecture, specs, and policy. |
| `retire` | Delete. The default once the work ships or is abandoned. |

## Prohibitions

- **No "keep" state.** `Retention: Keep`, `retained as the acceptance source`,
  and any other self-declared retention are prohibited. Content worth keeping is
  worth `canonise`, which moves it out of this directory.
- **No inbound links.** Nothing outside `docs/discussions/` may link to a file
  inside it — not a devlog entry, not an error-inbox `ENTRY.md`, not a README,
  not a test. Quote the conclusion instead. This is the invariant that keeps
  `retire` safe.
- **No deletion on a provider record alone.** Repositories get deleted and
  re-created, taking their issue and PR history with them. Before `retire`, the
  reasoning must already exist in-repo — an entry in this repository's
  development log (`docs/source/devlog/`) or promoted canon.

See `core/policies/work-tier-levels.md` (the lifecycle and the escalation judge)
and `docs/source/docs-placement-retention-policy-v1.md` (placement + retention).
