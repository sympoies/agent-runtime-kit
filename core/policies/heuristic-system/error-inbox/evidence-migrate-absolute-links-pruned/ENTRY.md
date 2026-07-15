# evidence migrate retains dangling linked-evidence paths before source prune

## Status

- Status: open
- First observed: 2026-07-15
- Area: evidence archive; skill-usage linked-record path contract
- Severity: medium

## Signal

`skill-usage` v1.21.31 emitted three `linked_records` as absolute paths inside
one agent-out run. `evidence migrate` v1.22.3 accepted and archived the record,
rendered three normalized `linked_evidence` paths into the rollup, but staged
only `metadata.yaml` and `skill-usage.rollup.json`. It returned no warning.
The governed `prune-source --archived-only --apply` step then deleted the whole
source run, including the only copies of the linked JSON and PNG files.

## Evidence

- Raw record: archived as
  `github.com/sympoies/agent-console/20260713T161856Z-computer-use-macos-desktop-df5885b3`
  with source digest
  `sha256:df5885b330bd69e14ad9e46ac3d3df84dd9e09f09a6df3dacb99042e2c86ab4a`.
- Archive commit: `e15a2d5ba098d056ff62062a0651d937734dc9ec`.
- Migration dry-run: `scanned=1`, `eligible=1`, `blocked=0`,
  `scrub.total_matches=0`, `warnings=[]`; the `files` list contained only the
  rollup and metadata sidecar even though `linked_evidence` contained three
  entries.
- Archive inspection after apply found only those same two files below the
  record target; none of the three referenced child paths existed.
- Source-prune dry-run selected exactly one archived run; apply reported
  `deleted=1`, removing the run directory and its child evidence.
- Source behavior in nils-evidence migration explicitly declines to stage an
  absolute linked path even when that path resolves inside the record's own run
  directory, while still retaining the normalized link in the rollup.

## Impact

The archive can report linked evidence that does not exist, while a successful
archived-only prune irreversibly removes the only child copies. The source
record digest and normalized rollup remain queryable, but validation JSON and
binary acceptance evidence are lost without any warning or blocking result.

## Current Workaround

Before source pruning, compare every rollup `linked_evidence` path with the
migration `files` list and target contents. If any referenced child was not
staged, leave that run unpruned; do not manually commit unscreened agent-out
artifacts into the archive.

## Promotion Criteria

Promote when regression coverage proves that an absolute linked path resolving
inside the same run is safely normalized and copied, or causes migration/prune
to block with a clear reason. The migrate-plus-prune test must prove no retained
link can outlive its only child copy.

## Next Action

Normalize in-run absolute linked-record paths to run-relative paths during migration, warn or block when bytes are not staged, and add migrate-plus-prune regression coverage.
