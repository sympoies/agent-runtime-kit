# Release skill should preserve a pinned Homebrew formula

## Status

- Status: open
- First observed: 2026-07-13
- Area: release
- Severity: medium
- Cluster: managed-homebrew-pin-preservation

## Signal

Skill `project-bump-version-tag-release` ended with `pass`. Summary: nils-cli 1.21.25 was released, installed on sympoies and m4, and verified against the original failing ID

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/sympoies__nils-cli/20260713-123401-codex-vscode-resume-closeout/release/skill-usage.record.json`
- Summary: linked `skill-usage.record.v1` envelope; raw runtime details remain in the evidence location.

## Impact

Future agents may repeat this workflow gap unless the retained entry is triaged,
routed, and later promoted into a durable fix, runbook, test, script, or skill
policy.

## Current Workaround

Apply the safest manual workaround for the affected workflow until the durable
fix lands, and avoid copying raw logs or secrets into this entry.

## Promotion Criteria

Promote after the durable fix or accepted-risk decision is implemented,
validated, and linked from this entry.

## Next Action

Update the nils-cli project-bump-version-tag-release skill to detect an existing formula pin, temporarily unpin for upgrade, restore the pin on success or failure, and add regression coverage.
