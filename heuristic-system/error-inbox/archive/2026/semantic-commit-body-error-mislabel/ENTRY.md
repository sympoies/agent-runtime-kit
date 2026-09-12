# semantic-commit reports a bullets-only body violation as a trailer error

## Status

- Status: promoted
- First observed: 2026-09-02
- Area: cli
- Severity: medium

## Signal

`semantic-commit commit --message-file` rejects a message whose body contains a prose paragraph
after the bullet list, but reports it as a trailer syntax error:

```
error: commit trailer line 13 must use 'Token: value' or 'Token=value'
```

The actual rule is that the body is bullets only; the first non-bullet line after the bullets is
parsed as the start of the trailer block. The message names `Token: value` syntax, which points at
a construct the author did not write and never mentions bullets, so the reported location and the
reported fix both mislead.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-09-02)
- Observed twice in one session, on two independent commit messages, each shaped as:
  header, blank, bullet list, blank, explanatory paragraph, blank, `Refs: #N`.
- Both times the reported line number pointed at the explanatory paragraph, not at the valid
  `Refs:` trailer.
- Resolution both times was to fold the prose into additional bullets. Nothing about the trailer
  changed.
- Tracked as sympoies/nils-cli#1697 and fixed by sympoies/nils-cli#1699 (merge
  `4bebd0eadecf44818d38966f02526dc8d3b12aff`). Regression coverage now distinguishes prose
  before any valid trailer from malformed content after a valid trailer.

## Impact

The error sends the author to inspect a correct trailer while the real defect is several lines
earlier and structurally different. An agent that takes the message literally will try to rewrite
or delete the trailer, or add `Token:` prefixes to prose, none of which fixes it. This costs a
retry loop on every commit whose body reads like prose, which is common for change descriptions
that need to explain a why.

This is not repo-specific: it applies to every repository that authors commits through
`semantic-commit`.

## Current Workaround

No workaround is needed on the nils-cli default branch after sympoies/nils-cli#1699. Until a
release containing that merge is installed, write the commit body as bullets only, folding any
explanation into additional bullets, and keep `Refs:`/`Closes:` trailers in their own block at the
end.

## Promotion Criteria

Met by sympoies/nils-cli#1699: `semantic-commit` reports this case as a body-shape violation that
names the offending line and the bullets-only rule, while malformed content after a valid trailer
retains the trailer diagnostic.

## Next Action

None. Fixed and validated by https://github.com/sympoies/nils-cli/pull/1699; tracking issue
https://github.com/sympoies/nils-cli/issues/1697 is closed.

Lifecycle link: `https://github.com/sympoies/nils-cli/pull/1699`

## Links

- Observed while delivering sympoies/agent-runtime-kit#90 and sympoies/nils-cli#1599.
- Tracking issue: https://github.com/sympoies/nils-cli/issues/1697.
- Fix: https://github.com/sympoies/nils-cli/pull/1699.

## Archive

- Archived: 2026-09-13
- Reason: Fixed and validated in nils-cli PR #1699.
- Durable link: `https://github.com/sympoies/nils-cli/pull/1699`
