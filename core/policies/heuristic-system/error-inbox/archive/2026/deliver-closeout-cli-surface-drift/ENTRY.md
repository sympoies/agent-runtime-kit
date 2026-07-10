# Deliver-* / closeout skill bodies copied broken forge-cli invocations without dry-run check

## Status

- Status: promoted
- First observed: 2026-05-23
- Area: issue-backed plan closeout skills (deliver-* + canonical *-closeout)
- Severity: medium
- Source PRs: graysurf/agent-runtime-kit#71 (introduced the bug pattern via chained closeout copy), graysurf/agent-runtime-kit#74 (fixed it)
- Source tracking issues: graysurf/agent-runtime-kit#67 (PR #71's tracking, closed via the buggy commands by deviating at runtime), graysurf/agent-runtime-kit#73 (PR #74's tracking, closed via the corrected commands verbatim)

## Signal

PR #71 (`feat(skills): chain matching closeout into deliver-* skills`) added
inline closeout commands to four `deliver-*` skill bodies by literally
copying the `forge-cli` invocations from the two canonical closeout skills.
Both copied commands were wrong under `forge-cli 0.17.6`:

1. `forge-cli issue close --reason completed` — flag does not exist;
   returns `ok=false code=unknown-subcommand` (exit 64). Backend
   `gh issue close <id>` already runs without a reason argument. 18
   occurrences across `core/skills/` + `tests/golden/` after PR #71
   merged.
2. `forge-cli issue view --format json` fed to
   `plan-issue record audit|closeout-gate --comments-json` —
   `forge-cli`'s view backend is `gh issue view --json
   number,url,state,title,labels,assignees,body` (no `comments`
   field). `--comments-json` silently resolves to an empty array
   and the closeout-gate marks required markers missing. PR #71's
   four new deliver-* blocks made the conflation explicit; the two
   pre-existing canonical closeout skills used distinct variables
   but did not document the derivation, so operators following the
   bodies fell into the same trap by copy-paste.

The specialist review on PR #71 (Sprint 3.2) flagged both as
`api-contract / info` findings and tagged them `no-action / pre-existing`.
The deferred disposition let the bugs ship in `de44f80`. Issue #67
closed only because the agent ran the chained closeout manually with
the corrected commands instead of following the documented sequence.

User follow-up requested verification: dry-runs against `forge-cli
0.17.6` confirmed both as real CLI rejections, not just docs drift.

## Evidence

- Raw record: not captured; retain provider issue / PR evidence below.
- PR #74 specialist review findings (ingested below as `evidence/pr74-specialist-findings.jsonl`): `<workspace>/out/.../forge-cli-closeout-cli-fix-review/findings.jsonl`
- PR #71 specialist review findings (where the two findings were originally surfaced and deferred): scratch dir already pruned after PR merge; the findings can be reconstructed from PR #71's delivery review outcome comment on the PR conversation tab.
- Dry-run verifying `--reason completed` is rejected: `forge-cli issue close 99999 --dry-run --format json --reason completed` → `ok=false, code=unknown-subcommand`.
- Dry-run verifying `forge-cli issue view` lacks comments: `forge-cli issue view 67 --format json --dry-run` → backend plan `["gh","issue","view","67","--json","number,url,state,title,labels,assignees,body"]`.

Ingested evidence files (under `evidence/`):

- `evidence/pr74-specialist-findings.jsonl` — PR #74 multi-lens specialist findings (6 rows, 0 blocking, 2 positive confirmations).

## Impact

Documentation drift between `forge-cli` and the SKILL bodies that wrap it.
The pattern recurs every time a new skill copies an existing CLI block
without dry-run verification. The fix (PR #74) only repairs the current
six bodies; it does not prevent the next deliver-* skill from making the
same mistake.

## Current Workaround

Fixed in PR #74. No active workaround required for the six skills already
touched (`plan-tracking-issue-closeout`, `dispatch-plan-closeout`,
`deliver-plan-tracking-issue`, `deliver-dispatch-plan`, `deliver-github-pr`,
`deliver-gitlab-mr`). New skill bodies that touch the same CLI surface
should apply the prevention rule below before merge.

## Promotion Criteria

Promote to `core/policies/heuristic-system/operation-records/` when one of:

- A new deliver-* / *-closeout skill is added and the prevention rule is
  observably followed (dry-run evidence in the PR description or
  review-evidence record).
- A repeat of this bug shape (skill body referencing a forge-cli flag or
  subcommand that the live CLI rejects) is caught by review or CI before
  merge thanks to this entry being read.
- `forge-cli` grows a comments-aware `issue view` and / or a `--reason`
  flag on `issue close`, at which point the prevention rule wording moves
  from "verify against forge-cli 0.17.6" to "verify against the installed
  forge-cli version".

## Prevention Rule

**Before editing the CLI command block of any deliver-* or *-closeout
SKILL.md.tera body, dry-run every `forge-cli`, `gh`, and `glab`
invocation in the block against the installed CLI version.** Capture
the `--dry-run --format json` backend plan as evidence in the
specialist review or commit message. Specifically:

- `forge-cli issue close <id> --dry-run --format json` must return
  `ok=true`. If any flag (e.g. `--reason`) is in the documented
  command, the dry-run must accept it.
- `forge-cli issue view <id> --dry-run --format json` must include
  every JSON field the SKILL body assumes downstream. If the SKILL
  body feeds the output to `plan-issue record --comments-json`, the
  backend plan **must** include `comments` in its `--json` list. If
  not, the SKILL body must fetch comments through `gh issue view
  --json body,comments` (GitHub) or `glab issue view --comments
  --output json` + jq reshape (GitLab) instead.

Add this rule to the specialist review checklist for any PR that
touches `core/skills/{dispatch,pr}/{deliver-*,*-closeout}/SKILL.md.tera`.

## Next Action

None — PR #547 landed the specialist-review gate and deterministic smoke
coverage; the case is archived.

Lifecycle link: `https://github.com/graysurf/agent-runtime-kit/pull/547`

## Archive

- Archived: 2026-07-10
- Reason: Prevention rule and deterministic smoke gate landed; tracking issue #530 closed.
- Durable link: `https://github.com/graysurf/agent-runtime-kit/pull/547`
