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
half-built log: someone already decided it should have one. Say so, and offer
the repair — author the `README.md`, then `devlog index` writes the month list
into it — after which the capability routes there like anywhere else. Until the
index exists, do not search it and do not append to it.

That is the one case where naming a missing index is right, and it is right
because the log already exists. It is not the case the next section is about.

Detect; never assume.

## Enabling a log is the user's decision

This section is about a repository with neither log directory — not the
half-built log above, which already has one.

There, detection failing is a complete answer, not a gap to fill. The
repository has no development log and this capability does nothing in it: do
not create a log directory, do not write an index, and do not raise either as a
follow-up or a finding. Most repositories will never have a log, and that is a
finished state rather than a backlog item.

Add one only when the user asks for that repository. Enabling it is writing the
index, in whichever of the two directories the detection table says this
repository's layout calls for:

```bash
mkdir -p docs/devlog          # docs/source/devlog for a source/render split
# author README.md there: what this log is for, and the entry shape
devlog index    # keep the month list in the index in sync from then on
```

Detection picks it up from there. With the kit switch off, this remains the
whole enable ritual.

When the kit fragment rule is enabled, a new indexed log also needs:

1. Released `nils-cli >=1.31.14` on entry writers and CI runners.
2. The scheduled default-branch fold job from the
   [fold recipe](devlog/ci-fold.md), with a repository-scoped App installation,
   Contents: write, verified commits, and a narrowly authorized protection
   exception. Install and prove this job before entries arrive.
3. Fragment-aware validation through `devlog check`. Fetch the default branch
   and pass `--base origin/<default-branch>` in PR CI to check merged-fragment
   immutability. Do not keep a month-only custom validator.
4. The same kit launch environment on each managed host and session. Do not
   introduce repository-local layout settings.

A maintainer enables a repository's log; the maintainer separately owns the
kit-wide rollout. Do not flip the switch as part of repository enablement.

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

## Kit-wide layout switch

`AGENT_RUNTIME_DEVLOG_FRAGMENTS=1` in the shared managed launch environment is
one kit-level opt-in. Unset or `0` is off. The kit's
`scripts/render-runtime-env.sh` renders `export DEVLOG_LAYOUT=fragments` only
when on; when off it renders a shell no-op and leaves inherited environment
unchanged. `scripts/with-runtime-env.sh <launcher> ...` applies that render before
Codex, Claude, Hermes, or `agent-session` starts, so child tools inherit it.
Direct launches must source the same rendered environment at shell/service
startup. The [fold recipe](devlog/ci-fold.md) describes the host/session and CI
wiring. No product-specific or repository-specific layout choice is added.

The switch stays off until the maintainer authorizes rollout after merge.
Before enablement, prove the sandbox scenario and real-provider acceptance,
provision each existing indexed log's fold job and checks, and close the
[fragment-only PR enforcement dependency](https://github.com/sympoies/nils-cli/issues/2082).
The current `devlog check --base` rejects edited merged fragments but accepts
structurally valid month-file changes. That is a tool gap, not permission to
edit months and not a reason to implement a parallel kit checker.

With the switch on:

- Write entries with `devlog new` only. It creates a unique file under
  `pending/`; an explicit `--slug` must be unique for the change.
- Never edit a month file or fold on a PR branch. The scheduled default-branch
  CI job is the only fold owner; it folds entries dated before today and
  updates the month index.
- Fragments are immutable after merge. Do not edit or delete a merged pending
  file; a correction is a new entry. A factual correction to a folded month
  needs the maintainer's separately authorized maintenance route.
- `search`, `check`, and `index` see unfolded entries. `new` does not need an
  agent-authored index update; the fold job owns month/index writes.

With the switch off, the existing month writer, CLI fallback, validation and
agent delivery flow remain unchanged. An independently inherited
`DEVLOG_LAYOUT` is left alone; managed deployments must not set a conflicting
repository override.

## Mechanism

Use the `devlog` CLI. In the default month layout, entry insertion is positional
under a month heading, the
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

A URL passed to any bullet flag is written as an autolink, so what the CLI
produces passes `MD034` in a repository that lints its log. A URL that is
already `<url>`, either half of a `[text](url)` link, or inside a code span is
written exactly as given.

`devlog check` reports structural problems and exits `65`; run it after writing.

## Repair: bring an existing log under the contract

A repository whose log predates this capability fails `devlog check` on its
first run, usually in bulk, and that is expected rather than alarming. It is
not a reason to hand-edit months of history:

```bash
devlog fix      # repair what has one correct repair, then report the rest
devlog check
```

`fix` promotes a bold section label to a heading, replaces an em dash
separating a heading's halves with the hyphen the parser splits on, brings a
month heading back into agreement with its filename, restores newest-first
order, adds a required section an entry never had with a bullet recording that
it was not recorded, and links a month the index had lost.

Everything else it reports and leaves alone, exiting `65` as `check` would — a
file that is not a month, an entry heading with no readable date, a section
outside the template, a date in the wrong month. Each of those needs a decision
about what its author meant, and that decision belongs to whoever owns the
repository.

Nothing inside a fenced code block is structure. An entry documenting this
format quotes headings and labels as examples; neither `check` nor `fix` reads
them as real.

Three shapes make `fix` leave a whole file or entry untouched rather than guess
at it, and each is reported instead:

- an entry whose fence is never closed — there is no knowing where its content
  ends, so there is nowhere in it a section can be placed;
- a file that mixes line endings — rebuilding it would rewrite every line that
  used the other ending, and which one it meant is not knowable;
- a month file or index that is a symlink — the repair would land outside the
  log while the link itself looked untouched in review.

`fix` does not create a log, and does not create an index for a log that has
none. Both are the user's decision, for the reason the section above gives.

Run it once when a repository adopts this capability, and afterwards only when
`check` reports something. It is not part of the write path: `new` already
produces the shape `check` accepts.

With the kit switch off, when the CLI is not installed, fall back to the repository's
`docs/devlog/README.md` (or `docs/source/devlog/README.md`) conventions and edit
the month file directly. The fallback is the same contract written in prose, so
the result is identical; the CLI exists so it does not depend on care. With the switch on, a missing
or older CLI blocks entry creation; report it instead of editing a month file.
Structural repairs that touch months under the enabled rule need the same
separately authorized maintenance route; `fix` is not an entry-PR bypass.

## Never

- Never record a credential of any kind, a machine-local path, a personal
  identifier, an internal hostname, private topology, or a provider payload.
  Reference identifiers, never values. These logs are readable by everyone who
  can read the repository, and an entry is append-only history.
- Never record private skill contents or another agent's session state.
- Never restate a diff or a normative document without adding context,
  evidence, or a link that makes the entry worth finding later.
- Never rewrite an older entry, except to correct a factual error in the same
  change. A `devlog fix` run is not an exception to that rule but a different
  act: it repairs structure the parser reads and never alters what an entry
  says, apart from adding a section that records it was never recorded.
