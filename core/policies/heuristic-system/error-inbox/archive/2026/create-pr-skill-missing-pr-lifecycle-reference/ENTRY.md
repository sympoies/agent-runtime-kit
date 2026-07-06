# create-pr skill references missing pr-lifecycle reference file

## Status

- Status: promoted
- First observed: 2026-07-04
- Area: Codex PR skill packaging; progressive disclosure references
- Severity: low

## Signal

During a live `pr:create-pr` skill run on 2026-07-04, the skill body required
reading `references/pr-lifecycle.md` after `SKILL.md`. Resolving that path
relative to the installed plugin package failed with `No such file or
directory`: the installed package contained the PR skill files under `skills/`,
but no sibling `references/` tree. The agent had to continue from the remaining
skill text, `forge-cli pr create --help`, the repo label catalog, and a
provider dry-run.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-04)
- Symptom: `sed -n '1,280p' $HOME/.codex/plugins/cache/codex-kit/pr/0.1.0/references/pr-lifecycle.md`
  returned `No such file or directory`.
- Package inventory in the same session showed only `skills/*.md` and
  `.codex-plugin/plugin.json` under the installed PR plugin package.
- Workaround used successfully: rely on the create-pr skill's local contract,
  render with `agent-runtime pr-body render`, validate labels from the repo's
  catalog, and run `forge-cli pr create --dry-run` before the live create.

## Impact

The progressive-disclosure contract cannot be followed as written: future
agents are told to read a missing required reference before creating PRs. That
can waste time, make PR delivery feel blocked, or cause an agent to miss shared
PR lifecycle rules that were meant to live in the referenced file.

## Current Workaround

If the reference is still missing, do not stop PR delivery solely on that gap.
Use the create-pr skill body, `agent-runtime pr-body render --help`,
`forge-cli pr create --help`, the repo label catalog, and a dry-run create as
the operative contract. Avoid inventing provider-visible body scaffolding by
hand.

## Promotion Criteria

Promote after the installed skill package either includes the referenced
`pr-lifecycle.md` file or removes/updates the stale reference, and after an audit
or test verifies that relative files named by shipped `SKILL.md` bodies resolve
in the installed package.

## Next Action

None. Packaged lifecycle reference exists in source/rendered skill output, installed Codex plugin cache includes skills/create-pr/references/pr-lifecycle.md, and scripts/ci/skill-governance-audit.sh verifies lifecycle reference packaging and resolution.

## Archive

- Archived: 2026-07-06
- Reason: Packaged reference and governance audit verified
- Durable link: `scripts/ci/skill-governance-audit.sh`
