# Tracker row grammar fixtures

Conformance corpus for the program tracker phase-table grammar. The grammar
itself is normative in
`core/skills/issue/issue-follow-up/references/program-mode.md`, section "Phase
Table Row Grammar"; when the two disagree, that section wins and the corpus is
the defect.

A repository that implements a parser copies this directory unchanged and runs
every pair. The path is stable. `tests/ci/test_tracker_row_grammar_fixtures.py`
keeps the corpus self-consistent in this repository.

## Layout

| Path | Body | Expectation |
| --- | --- | --- |
| `valid/<name>.md` | A tracker body with no finding | `valid/<name>.json`: the parsed rows and the generated graph |
| `invalid/<code>.md`, `invalid/<code>--<variant>.md` | A tracker body that has findings | The sibling `.json`: exactly the findings a linter reports |

Every `.md` file has one `.json` sibling with the same stem. An invalid file
name starts with the finding code it exercises.

## Valid expectation

```json
{
  "rows": [
    {
      "id": "A1",
      "title": "Local projection",
      "ref": {"owner": "example", "repo": "alpha", "number": 14},
      "notes": "PR example/alpha#16",
      "after": [],
      "done": true,
      "phase": "Phase 1: Foundations"
    },
    {
      "id": "REL",
      "title": "Release containing A1",
      "ref": null,
      "notes": null,
      "after": ["A1"],
      "done": false,
      "phase": "Phase 1: Foundations"
    }
  ],
  "graph": "graph LR\n  A1\n  REL{{REL}}\n  A1 --> REL"
}
```

- `rows` is in table order.
- `title` is the text as written, Markdown included.
- `ref` is `null` for a gate. `owner` and `repo` are both `null` for a `#N`
  ref, which names the tracker's own repository.
- `notes` and `phase` are `null` when absent. `after` is `[]` when absent and
  keeps the written order.
- `graph` is the canonical Mermaid source without its fence: lines joined by
  one line feed, with no trailing line feed. The body's `mermaid` block holds
  the same lines.

| File | Covers |
| --- | --- |
| `valid/minimal.md` | Two rows and one dependency |
| `valid/full.md` | A complete tracker: phases, notes, gates, both ref forms, done and open rows, one issue on two rows, a title with `: `, parentheses, and backticks, ignored prose and sub-items |
| `valid/no-dependencies.md` | No `after` clause anywhere |
| `valid/edge-cases.md` | Section lookup, ignored lines, and the right-to-left row parse at its surprising corners |

## Invalid expectation

```json
{
  "findings": [
    {"code": "unknown-dependency", "line": 6, "ids": ["A2", "A9"]}
  ]
}
```

Compare `findings` as an unordered collection; the array order carries no
meaning. `line` is the one-based line number in the `.md` file.

| `code` | `line` | `ids` |
| --- | --- | --- |
| `malformed-row` | The row line | `[]` |
| `duplicate-id` | The row that reuses the id | The reused id |
| `unknown-dependency` | The row that declares it | The row id, then the unknown id |
| `self-dependency` | The row | The row id |
| `cycle` | The first row of the group, in table order | Every id of the group, in table order |
| `stale-graph` | `null` | `[]` |

These fields pin the corpus. The output format of a linter belongs to that
linter.

The row-finding files have no current graph, and their expectations carry no
`stale-graph`: that code is reported only when the table has no other finding.

## Not covered

The repository's whitespace check rejects files with carriage returns or
trailing whitespace, so no fixture carries them. An implementation tests its
own line-ending and trailing-whitespace normalisation.

All names are fictional. Do not add a real repository, host, or person.
