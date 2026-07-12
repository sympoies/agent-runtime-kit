# Runtime Smoke Harness

This directory contains the acceptance foundation for migrated runtime
skills. The harness is intentionally offline and credential-free by default.
It must never mutate real `$HOME/.codex`, `$HOME/.claude`, auth, sessions,
history, logs, caches, or product state.

## Modes

- `matrix`: validates the acceptance matrix contract, checks that case IDs are
  unique, and checks that the unique `skill_id` set exactly matches the
  committed sandbox skill pins for both products.
- `install`: creates temporary `live_home` and `state_home` roots for Codex and
  Claude, renders current product surfaces, runs `agent-runtime install
  --apply`, verifies installed `SKILL.md` surfaces against
  `tests/sandbox/<product>/expected-skills.txt`, and runs `agent-runtime
  doctor`. For Codex, the collector follows domain-nested skill folder
  symlinks under `$CODEX_HOME/skills/<domain>/<skill>/` and maps their
  rendered plugin target back to the canonical `domain.skill` id.
- `deterministic`: runs committed command-level probes for available domains.
  Current coverage includes `meta`, `media`, `browser`, `conversation`,
  `evidence`, `issue`, `code-review`, `pr`, `dispatch`, and `reporting`
  domains. The `pr` domain includes `forge-cli` dry-run probes for create,
  close, dispatch-lane create, and delivery macro surfaces.
- `product`: runs quarantined product CLI isolation probes and installs
  temporary product homes. It does not execute prompts; outcome routing is
  covered deterministically, while authenticated fresh-session acceptance is a
  separate private/live lane.
- `convergence`: clones a clean committed source and isolated Codex / Claude
  homes, then proves a historical 66-to-26-skill upgrade, baseline re-sync rollback, retired
  managed-surface pruning, stubbed plugin registry activation, independently
  rebuilt installed-runtime receipt entry/plan digests, active-ID read-back,
  idempotent reapply, and four generic
  prompt/route contract fixtures. Its public JSON summaries contain only product,
  revision, counts, digests, booleans, and status; raw path-bearing logs remain
  in the caller-owned artifact directory.

`doctor` warnings are allowed in install mode because host tool freshness can
vary. Blocking findings are not allowed; the runner parses the `block=<n>`
summary and fails when it is nonzero or missing.

## Commands

```bash
bash tests/runtime-smoke/run.sh --mode matrix
bash tests/runtime-smoke/run.sh --mode install
bash tests/runtime-smoke/run.sh --mode install --format json
bash tests/runtime-smoke/run.sh --mode deterministic
bash tests/runtime-smoke/run.sh --mode deterministic --domain meta
bash tests/runtime-smoke/run.sh --mode deterministic --domain media
bash tests/runtime-smoke/run.sh --mode deterministic --domain browser
bash tests/runtime-smoke/run.sh --mode deterministic --domain conversation
bash tests/runtime-smoke/run.sh --mode deterministic --domain evidence
bash tests/runtime-smoke/run.sh --mode deterministic --domain issue
bash tests/runtime-smoke/run.sh --mode deterministic --domain code-review
bash tests/runtime-smoke/run.sh --mode deterministic --domain pr
bash tests/runtime-smoke/run.sh --mode deterministic --domain dispatch
bash tests/runtime-smoke/run.sh --mode deterministic --domain reporting
bash tests/runtime-smoke/run.sh --mode product --product codex
bash tests/runtime-smoke/run.sh --mode product --product claude
bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only
bash tests/runtime-smoke/run.sh --mode product --product claude --probe-only
bash tests/runtime-smoke/run.sh --mode product --format json
bash tests/runtime-smoke/run.sh --mode convergence
bash tests/runtime-smoke/run.sh --mode convergence --format json
```

Use `--product codex` or `--product claude` to narrow install mode. Use
`--keep-artifacts` for manual debugging; the command prints the temporary root
to stderr. Use `--artifacts-dir <path>` when a caller needs persistent logs
without keeping the temporary runtime homes.
Portable install/product/convergence source cloning fails closed when the
working tree is dirty, so only committed reviewed content enters retained Git
objects.

Product mode is intentionally outside default CI. It proves the product CLI can
run with temporary runtime homes, installs the current runtime surface into
temporary product homes, and stops before any prompt/provider call. Product
mode must not touch real
`$HOME/.codex`, `$HOME/.claude`, auth, sessions, history, logs, or caches.
Prompt routing remains residual live-product risk and is verified only by the
private fresh-session acceptance lane after public integration.

Convergence mode does not claim prompt classification or model execution. It
validates four natural-language prompt fixtures (implementation, code review,
rendered-browser evidence, and bounded macOS desktop operation), their declared
active route contracts, and absence of retired bookkeeping surfaces. Task 4.1
owns authenticated behavioral routing against the merged runtime.

## Reviewer Subagent Discovery

The cross-product reviewer subagents render to `build/<product>/agents/` and
install (via the `agents-tree` link-map entry) into `~/.codex/agents/*.toml`
and `~/.claude/agents/*.md`.

Automated coverage (in default CI):

- `bash scripts/ci/sandbox-install-rehearsal.sh` diffs the installed reviewer
  agent set against `tests/sandbox/<product>/expected-agents.txt` for both
  products (`all.sh` sandbox-install position), failing on a missing or renamed
  reviewer agent.

Live product discovery is manual-only — it needs an authenticated product
session and stays outside default CI:

- Claude: in a session, run `/agents` and confirm `reviewer-quick` and the seven
  `reviewer-<lens>` specialists appear under the user scope. Expected: all eight
  are listed and invokable via the Agent tool.
- Codex: start a session with `CODEX_HOME` pointed at the installed home and
  confirm the definitions in `$CODEX_HOME/agents/*.toml` are offered for
  delegation. Expected: `reviewer-quick` (and the specialists) are spawnable as
  read-only subagents.

## Matrix Contract

`acceptance-matrix.yaml` is a constrained YAML subset so it can be validated
with portable shell tools. Each case must include:

- `id`
- `product`
- `domain`
- `skill_id`
- `mode`
- `fixture_workspace`
- `setup`
- `invocation`
- `expected_exit_code`
- `expected_artifacts`
- `cleanup`
- `expected_disposition`
- `skip_policy`

Allowed result dispositions are `pass`, `fail`, `skip-host-capability`, and
`blocked-design`.

The matrix may contain multiple cases for one `skill_id` when a deterministic
case and a product prompt case both exist. The unique `skill_id` set must still
match the committed sandbox skill pins.

## Artifact Policy

Committed expected outputs stay small and deterministic under `expected/`.
Runtime logs, observed skill lists, diffs, and future case artifacts are written
to the temporary run root or to the caller-provided artifacts directory.
