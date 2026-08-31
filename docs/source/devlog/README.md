# Development log

A time-ordered narrative of notable work on agent-runtime-kit: what changed,
why it mattered, the evidence, and links worth keeping for future debugging. It
complements, rather than duplicates, the repository's other records:

- Commit messages say what changed. The devlog preserves the non-obvious
  context, validation results, and external references that a diff cannot.
- `README.md`, `DEVELOPMENT.md`, and current policy describe today's contract.
  The devlog is an append-only historical narrative; update the canonical
  owner first when behavior or guidance changes.
- Pull requests and plan records retain detailed delivery evidence. The devlog
  summarizes milestones that remain useful after those records close.

## When to add an entry

Add one after non-trivial development work produces a durable outcome worth
future lookup: a shipped runtime change, validated milestone, compatibility or
security decision, incident-relevant finding, or external reference. Skip
trivial, transient, and same-turn fixes with no future debugging or decision
value.

## Conventions

- One file per month: `docs/source/devlog/YYYY-MM.md`, newest entry first.
- Write in English, like the rest of the repository.
- Keep current docs current. The devlog records history; it does not own the
  current runtime contract, policy, setup, or runbook.
- This is a public repository. Never record secrets, private skill contents,
  personal identifiers, internal hostnames, private topology, machine-local
  paths, or credentials. Use public references and neutral descriptions.
- Search past entries with `scripts/devlog-search.sh <term> [YYYY-MM]`.
- When an entry is committed separately, use
  `docs(devlog): <YYYY-MM> - <subject>`.

### Entry template

```md
## YYYY-MM-DD - <short title>

**Result**

- What shipped or changed.

**Why / context**

- The non-obvious reasoning or compatibility context.

**Evidence**

- Commands run and concrete observations.

**Links**

- Commits, issues, pull requests, external references, and relevant docs.

**Follow-ups**

- Optional.
```

## Months

- [2026-09](2026-09.md)
- [2026-08](2026-08.md)
- [2026-07](2026-07.md)
- [2026-06](2026-06.md)
- [2026-05](2026-05.md)
