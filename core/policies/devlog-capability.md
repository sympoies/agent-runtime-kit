# Development Log Capability

## Purpose

This policy is the detail behind the devlog half of the `project-dev` intent:
when to read a repository's development log, when to append to it, and what
must never go into it.

The development log is the only surface that holds the reasoning a diff cannot
carry. Commit messages say what changed; the log says why the change was shaped
that way, what was ruled out, and what evidence made it credible. That value
only exists if the log is written without being asked and read without being
told — which is why this is a default capability rather than a skill somebody
has to remember to invoke.

It is declared as a `project-dev` document in `AGENT_DOCS.toml` (home scope),
conditional on the repository actually having a log. A repository without one is
unaffected: detection failing closed means "no log here", not an error.

It is required reading in the `delivery` phase, where the write half lives. The
read half fires earlier than that, so the `project-dev` intent card carries its
trigger and points here; open this policy when the trigger fires rather than
waiting for a phase boundary. The `edit` phase deliberately carries one required
document, and that budget belongs to the edit contract.

## Detection

A repository has a development log when one of these index files exists:

| Index | Log directory | Used by |
| --- | --- | --- |
| `docs/devlog/README.md` | `docs/devlog/` | most repositories |
| `docs/source/devlog/README.md` | `docs/source/devlog/` | repositories with a source/render split, including this one |

The index, not the directory, is the marker. It is what this policy points a
reader at for the repository's own conventions, so a directory without one is
not yet a log to route to. Both conventions are permanent, so a repository is
not expected to move its log to satisfy the capability.

The `devlog` CLI is looser: it resolves the two directories, in the order above,
and will happily write into one that has no index. That difference is not a
licence to treat a bare directory as a log. A repository in that state has a
half-built log, and the fix is to add the index — `devlog index` writes the
month list into an existing `README.md` — after which the capability routes
there like anywhere else. Until then, do not search it and do not append to it.

Detect; never assume.

## Enabling a log is the user's decision

Detection failing is a complete answer, not a gap to fill. A repository with no
index has no development log, and this capability does nothing there: do not
create `docs/devlog/`, do not write an index, and do not raise either as a
follow-up or a finding. Most repositories will never have a log, and that is a
finished state rather than a backlog item.

Add one only when the user asks for that repository. Enabling it is writing the
index:

```bash
mkdir -p docs/devlog
# author docs/devlog/README.md: what this log is for, and the entry shape
devlog index    # keep the month list in the index in sync from then on
```

Detection picks it up from there. Nothing else has to be declared — not in the
repository, and not in this policy.

Everything below applies only when detection succeeds.

## Read: consult the log when it would answer the question

Reading is the half that is easy to skip and expensive to skip. Consult the log
before:

- changing a contract, schema, guardrail, default, or removing something an
  entry may explain;
- acting on a behavior that looks arbitrary when the reason is not in the code;
- investigating a regression whose cause may be a recorded decision.

```bash
devlog search '<term>'            # every month
devlog search '<term>' --month 2026-09
```

Matching is literal and case-insensitive. Search the identifier — a crate name,
a flag, an error code, a file path — rather than a paraphrase of the behavior.

An entry is history, not authority. It never overrides current source, schemas,
policy, or a canonical runbook. When the log and the current contract disagree,
the contract wins and the disagreement is worth reporting.

## Write: record at the finish line

Append at the same boundary that already owns finish-line validation, where the
session knows what it actually delivered — not on request, and not per commit.

Write an entry for:

- a shipped capability, adapter, or ownership change;
- a contract, schema, compatibility, or security decision;
- a validation milestone or an incident-relevant finding;
- an external reference worth keeping.

Do not write an entry for trivial changes, transient work, same-turn cleanups,
or anything with no future lookup value. The bar stays high and silence is the
correct outcome for most sessions: an agent that writes an entry per commit
turns the log into a second changelog and destroys the signal that justifies it.

Keep the canonical owner current first. The log records history; it does not own
the current contract, policy, setup, or runbook. If a behavior changed, the
document that defines that behavior is updated in the same change.

## Mechanism

Use the `devlog` CLI. Entry insertion is positional under a month heading, the
month index has to stay in sync, and the section shape and heading levels are
Markdown-lint-visible; those are mutations that belong to a contract rather than
to an agent editing a file by hand.

```bash
devlog new --title '<title>' \
  --result '<what now exists>' \
  --why '<why it was shaped this way>' \
  --evidence '<command or observation that actually ran>' \
  --link '<commit, PR, or issue>'        # optional
devlog check
```

`--result`, `--why` and `--evidence` are what an entry must carry. `--link` and
`--follow-up` are optional and are omitted rather than filled with a
placeholder; an entry whose author had nothing to link is complete.

`devlog check` reports structural problems and exits `65`; run it after writing.

When the CLI is not installed, fall back to the repository's
`docs/devlog/README.md` (or `docs/source/devlog/README.md`) conventions and edit
the month file directly. The fallback is the same contract written in prose, so
the result is identical; the CLI exists so it does not depend on care.

## Never

- Never record a credential of any kind, a machine-local path, a personal
  identifier, an internal hostname, private topology, or a provider payload.
  Reference identifiers, never values. These logs are readable by everyone who
  can read the repository, and an entry is append-only history.
- Never record private skill contents or another agent's session state.
- Never restate a diff or a normative document without adding context,
  evidence, or a link that makes the entry worth finding later.
- Never rewrite an older entry, except to correct a factual error in the same
  change.
