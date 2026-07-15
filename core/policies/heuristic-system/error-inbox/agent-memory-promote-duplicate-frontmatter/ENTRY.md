# agent-memory promote duplicates candidate frontmatter

## Status

- Status: open
- First observed: 2026-07-15
- Area: cli
- Severity: medium
- Upstream issue: https://github.com/sympoies/nils-cli/issues/1230 (nils-cli 1.22.3)

## Signal

`agent-memory candidate promote --apply` emits a **duplicated YAML frontmatter
block** in the promoted `global/<slug>.md` when the source candidate carries its
own frontmatter — which is the documented candidate format. Observed while
promoting the `hermes-agent-fork` Claude candidate to curated global memory.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-15).
- The promoted `global/hermes-agent-fork.md` contained two stacked `--- ... ---`
  blocks: the canonical header nils-cli builds (with `node_type`, `type`,
  `originSessionId`), immediately followed by the candidate's original
  frontmatter verbatim, then the body. The second block renders as raw YAML in
  the note body on recall.
- `agent-memory check global --strict --max-index-bytes 8192` passed clean, so
  the malformed note landed silently.

## Impact

Any promotion of a correctly-formatted candidate produces a malformed curated
note, and the strict check does not catch it — so it lands silently and shows
raw YAML in the note body on recall. Repeats on every promote until fixed.

## Current Workaround

Manually rewrite the promoted `global/<slug>.md` to a single canonical
frontmatter header + body after `promote --apply`, then re-run
`agent-memory check global --strict`. Done for `hermes-agent-fork` on
2026-07-15.

## Promotion Criteria

Close/promote once nils-cli #1230 ships: `candidate promote` parses the
candidate frontmatter, lifts its fields into the canonical header, and emits
header + body only (no duplicate). Bonus: a `check` lint rejecting notes with
more than one frontmatter block. Validate, then link the fix from this entry.

## Next Action

Implement the fix in nils-cli (`sympoies/nils-cli`, issue #1230). A handoff
prompt for the next implementation session is prepared; the deterministic floor
is the crate tests + `check global --strict` on a promoted fixture.
