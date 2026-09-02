# semantic-commit reports a bullets-only body violation as a trailer error

## Status

- Status: open
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

## Impact

The error sends the author to inspect a correct trailer while the real defect is several lines
earlier and structurally different. An agent that takes the message literally will try to rewrite
or delete the trailer, or add `Token:` prefixes to prose, none of which fixes it. This costs a
retry loop on every commit whose body reads like prose, which is common for change descriptions
that need to explain a why.

This is not repo-specific: it applies to every repository that authors commits through
`semantic-commit`.

## Current Workaround

Write the commit body as bullets only, folding any explanation into additional bullets, and keep
`Refs:`/`Closes:` trailers in their own block at the end. When the trailer error appears, look at
the reported line rather than at the trailer.

## Promotion Criteria

Promote once `semantic-commit` reports this case as a body-shape violation that names the offending
line and the bullets-only rule, or once the body grammar is documented where message authors will
see it before the failure.

## Next Action

Route to `sympoies/nils-cli` as a `semantic-commit` message-quality defect. The fix is in the error
path, not the grammar: the parser already knows it transitioned from body to trailer at a line the
author intended as body, so it can say so. Confirm whether the bullets-only body rule is documented
anywhere an author reads before hitting the error, and file the upstream issue with the two
observed message shapes as the reproduction.

## Links

- Observed while delivering sympoies/agent-runtime-kit#90 and sympoies/nils-cli#1599.
