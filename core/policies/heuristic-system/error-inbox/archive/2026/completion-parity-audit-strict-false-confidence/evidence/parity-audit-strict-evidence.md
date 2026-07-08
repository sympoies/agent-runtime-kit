# Evidence — completion parity audit --strict false confidence

## Failure (nils-cli v1.9.0 release.yml, on tag)

`release.yml` runs `completion-flag-parity-audit.sh --strict`, which failed:
the new `pr review-threads list/resolve/reply` subcommands had missing zsh
completion blocks. The local pre-release run had used the bare (non-`--strict`)
invocation and passed, so the gap only surfaced in CI on the tag. The tag was
created but no release was published.

## Root cause

The initial clap shape (optional bare positional + `args_conflicts_with_subcommands`)
shifts the zsh subcommand context to `$line[2]`, while the audit hardcodes
`$line[1]` in `zsh_context_marker`. `--strict` flags the resulting missing
per-subcommand blocks; the non-strict run tolerates them.

## Fix + post-fix strict pass

Fixed in sympoies/nils-cli#885 (clean `review-threads` subcommand group, drop
the bare `<id>` positional). The strict audit then passes on the fix worktree:

```
=== strict parity audit ===
PASS: completion flag parity audit (required=44, failures=0)
```

Re-released cleanly as v1.9.1.
