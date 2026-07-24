# Execution Capsules

## Purpose and boundary

An Execution Capsule is the standard handoff when an authorized local
operation cannot run in the current agent environment, or when the user asks
for a reusable one-line script plus an agent-supervised alternative. It
packages one reviewable `run.sh` with a machine-readable manifest so the same
operation can be:

1. run directly by the operator; or
2. run through `codex-cli agent run`, which monitors the operation, diagnoses
   in-scope failures, reruns validation, and writes a receipt.

The capsule changes the execution environment, not the authorization or
governance contract. Repository instructions, hooks, signing requirements,
delivery rules, destructive-action policy, and session-coordination guards
remain active.

`agent-run` remains an environment normalizer for a known argv. It is not the
AI supervisor and must not absorb the capsule lifecycle.

## When to use

Use a capsule when:

- the current agent cannot execute an otherwise authorized local operation
  because its filesystem, sandbox, host, or process environment is too narrow;
- the user wants a durable script instead of pasted command fragments;
- an urgent local hotfix needs an operator-run path with explicit
  preconditions, validation, and a result report; or
- the user explicitly asks for both direct and supervised commands.

Do not use a capsule to infer permission for provider mutation, destructive
scope, credential access, or a materially different task. Obtain the same
authorization that direct execution would require.

## Required user-facing result

After creating the capsule, give the user its absolute path and the applicable
one-line commands:

```sh
bash <capsule>/run.sh
codex-cli agent run --capsule <capsule>
```

For an explicitly prepared host capsule, give:

```sh
codex-cli agent run --capsule <capsule> --allow-host-access
```

State why `host` was selected. Do not make the operator reconstruct a long
command from prose.

## Capsule construction

Allocate the location with `agent-out project --topic <topic> --mkdir`. Never
put a capsule in the repository or in repo-local `./agent-out`.

Required layout:

```text
<capsule>/                 0700
  manifest.json            0600
  run.sh                   0700
```

Use the active environment's approved file-edit mechanism, then set the exact
private modes. Mode `0775` is invalid: group write/read access breaks the
operator-only trust boundary and the runner rejects it.

The executable contract in
`crates/codex-cli/docs/specs/execution-capsule-v1.md` is the normative schema
and runner behavior. Under that contract, capsule authors must make `run.sh`:

- start with `set -euo pipefail`;
- enter or verify the exact target directory;
- check expected branch, HEAD, files, or other state before mutation;
- use project-governed commands and keep hooks/signing enabled;
- be idempotent where practical, and fail clearly when a safe retry is not
  possible;
- perform the essential validation itself, because the direct path does not
  read the manifest or generate a receipt;
- resolve files from the declared `cwd`, explicit absolute paths,
  `EXECUTION_CAPSULE_DIR`, or `EXECUTION_CAPSULE_ENTRYPOINT`; supervised
  execution preserves `run.sh` as `$0` but snapshots it through `/dev/stdin`,
  so `BASH_SOURCE` is not a stable script-relative path;
- avoid embedding secrets, tokens, private keys, or auth payloads; and
- avoid provider/network mutation unless the current request authorized that
  effect.

The manifest must use `schema_version: "execution-capsule.v1"`, an absolute
`cwd`, `entrypoint: "run.sh"`, the script's `sha256:` digest, `access`,
`allowed_paths`, optional exact Git preconditions, and validation argv arrays.
Do not put secrets in `task` or validation argv.

The executable schema, validation rules, script contract, receipt fields, and
examples are owned by `nils-cli`:

```text
crates/codex-cli/docs/specs/execution-capsule-v1.md
```

## Access classes

### `workspace`

This is the default. `codex-cli` launches Codex with `workspace-write` rooted
at the manifest `cwd`. All allowed paths must stay under that directory, while
the capsule itself must remain outside `cwd` so the supervised process cannot
rewrite its trust inputs or named artifacts. The supervisor preserves active
home/project instructions, config, and hooks.

Use it for routine repository work and whenever the current environment's
limits are not the reason for the handoff.

### `host`

Use `host` only when the user needs to escape the current agent's filesystem
or sandbox boundary, or has explicitly requested an operator-run urgent
hotfix. The manifest declaration alone is insufficient:
`codex-cli agent run` also requires the operator to pass
`--allow-host-access`.

The operator's launch is the explicit access acknowledgement. A constrained
parent agent should prepare and report the command, not self-launch the host
route to bypass its own environment.

Host mode gives the Codex child `danger-full-access` with approvals set to
`never`; it does not pass the dangerous bypass flag. The child still reads and
obeys normal instructions and hooks. `allowed_paths` remains the declared task
boundary even though the OS sandbox is broader.

The receipt marks host evidence as `supervisor-trusted`, not
`sandbox-attested`. This path preserves governance, monitoring, validation,
and reporting for cooperative execution, but it is not a tamper-resistant
security attestation against a malicious same-UID process with full host
access. Use a distinct OS security principal when that adversarial guarantee
is required.

## Supervision and failure handling

The parent never executes `run.sh` directly. Codex runs the exact internal
helper command inside the selected sandbox; its executable is a private
owner-only snapshot outside the declared workspace, held open and verified
again before receipt publication. The helper
revalidates and snapshots the script before executing the exact bytes. On failure Codex may
inspect, diagnose, make the smallest correction inside `allowed_paths`, and
rerun the same helper. It then runs exact helpers for declared validation. The
parent captures Codex JSONL on a parent-held stream, accepts only matching
command events plus nonce-bound helper attestations, and publishes
`events.jsonl` only after Codex exits. It then revalidates final capsule
integrity. The structured final report also flows through standard input
preserved by the launcher as a parent-held, unlinked workspace file before the
parent atomically publishes `final.json`. For
repeated helpers, the terminal-marked script event and the last matching event
for each validation step determine the outcome. Codex must not:

- broaden task scope;
- disable hooks, signing, policy, or approval gates;
- silently convert a read-only, permission, or policy failure into host
  authority;
- treat a shared-index race, checkout lease, stale HEAD, or concurrent agent
  edit as a permission problem; or
- claim success when Codex, the structured final report, the independently
  observed script run, capsule integrity, or wrapper validation failed.

When concurrency state changed, stop and report the exact mismatch. Regenerate
or re-authorize the capsule rather than editing away the precondition.

The runner writes private `result.schema.json`, `events.jsonl`, `final.json`,
and `receipt.json`; command output remains in the event stream. If a hostile
host-mode process blocks `receipt.json` at closeout, the runner uses a
parent-selected recovery name that remains undisclosed until atomic
publication. Report the receipt path and summarize the final status or error
recommendation to the user. These are transient execution artifacts; keep
them under `agent-out`, not in project history.
