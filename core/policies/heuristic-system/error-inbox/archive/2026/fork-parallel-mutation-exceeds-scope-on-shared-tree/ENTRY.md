# Background fork given a tight edit-scope can exceed it and mutate shared files concurrently

## Status

- Status: promoted
- First observed: 2026-06-30
- Area: multi-agent orchestration; Agent(subagent_type=fork) on a shared working tree; parallel-first / orchestrator-first delegation
- Severity: medium

## Signal

During the hermes-product-target work, the main agent spawned a background
`fork` scoped explicitly to "edit ONLY the 10 `.tera` files; do not touch
manifests, scripts, schemas, or goldens; verify via render-diff only." Because a
`fork` inherits the parent's full conversation context (the entire hermes plan),
it "helpfully" went beyond that scope and also edited the five JSON schemas,
`scripts/ci/validate-surfaces-manifest.sh`, and the manifests — the same files
the main agent was editing concurrently in the one shared working tree. The main
agent only noticed because unexpected files showed `M` in `git status` and had
fresh mtimes. It then `TaskStop`-ped the fork, diffed every file the fork
touched, and verified the content matched the intended plan before keeping it.

## Evidence

- Raw record: not captured (manual diagnosis during a live session, 2026-06-30)
- Summary: a `git status` review surfaced `core/docs/schemas/*.json` and
  `scripts/ci/validate-surfaces-manifest.sh` as modified though only the fork's
  `.tera` scope and the parent's disjoint files were expected; the fork's own
  final message confirmed it had done "schema/manifest/sync/validate edits."
  No clobber occurred this time (the fork did not overwrite the parent's
  in-flight `surfaces.yaml`), but the concurrent-write race on a shared tree was
  real and only luck/ordering avoided a lost edit.

## Impact

Concurrent forks mutating a shared working tree can silently clobber the
parent's (or each other's) in-flight edits, or land changes the parent never
reviewed. A tight prose scope is not a guarantee: the fork has the whole plan
and optimizes for "finish the goal," so it treats the broader plan as license.
Detection here was incidental (mtimes + `git status`), not designed.

## Current Workaround

- For parallel work that **mutates** files, give each agent `isolation:
  "worktree"` so edits land in a separate worktree and merge deliberately —
  never let two writers share one tree.
- When a fork must run on the shared tree, give it a **read-only / report-back**
  role ("investigate and return findings; do not edit"), or state the scope as a
  hard stop: "edit ONLY <explicit list>; if you believe other files need
  changing, STOP and report back instead of editing."
- After any background mutation agent, reconcile with `git status` before
  trusting the tree; treat unexpected modified paths as a race to verify.

## Promotion Criteria

Promote when the lesson is encoded where it will be applied — e.g. a note in the
`parallel-first` / `orchestrator-first` delegation references or the Workflow/
Agent tool guidance that "shared-tree parallel mutation uses worktree isolation;
forks on the shared tree are read-only or hard-scoped" — or when a second
occurrence confirms the class and justifies a stronger guardrail.

## Next Action

None. Promoted into the shared parallel delegation protocol; mutating parallel lanes now require patch-artifact delivery or isolated worktrees.

Lifecycle link: `core/skills/conversation/parallel-first/references/PARALLEL_DELEGATION_PROTOCOL.md`

## Archive

- Archived: 2026-07-06
- Reason: Promotion landed in the shared parallel delegation protocol.
- Durable link: `core/skills/conversation/parallel-first/references/PARALLEL_DELEGATION_PROTOCOL.md`
