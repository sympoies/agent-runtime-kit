---
name: execution-capsule
description: >
  Prepare a private execution capsule with a reviewable script and direct or
  agent-supervised run commands; use only for an already authorized local
  operation.
---

# Execution Capsule

## Contract

Prereqs:

- The underlying local operation is already authorized. Capsule preparation
  must not infer authorization for destructive scope, provider mutation,
  credential access, host access, or a materially different task.
- Resolve and read `core/policies/execution-capsules.md` from the selected
  agent-docs home before constructing any files. That policy remains the
  canonical safety and lifecycle contract.
- `agent-out` is available. The target working directory and every allowed
  path are exact absolute paths.
- For `workspace`, the workspace capsule must be outside the canonical `cwd`,
  and every canonical allowed path must remain under that `cwd`. If the
  `agent-out` allocation violates that containment boundary, stop; do not
  relocate it manually or switch to `host`.
- The supervised alternative requires a `codex-cli agent run` implementation
  whose help exposes `--capsule`. If it is unavailable, still preserve the
  direct operator path and report that supervised execution is unavailable;
  do not substitute a raw `codex` invocation.

Inputs:

- The authorized operation, exact `cwd`, access class (`workspace` by default),
  allowed paths, relevant preconditions, validation commands, and a short
  capsule topic.
- Explicit operator intent before selecting `host`; a constrained agent never
  selects or launches host access merely to bypass its environment.

Outputs:

- One private capsule directory allocated outside the repository and, for
  `workspace`, outside its canonical `cwd`, with:

  ```text
  <capsule>/                 0700
    manifest.json            0600
    run.sh                   0700
  ```

- The absolute capsule path and applicable one-line commands:

  ```sh
  bash <capsule>/run.sh
  codex-cli agent run --capsule <capsule>
  ```

- For an explicitly prepared host capsule, the reason host access is required
  and this operator-authorized command:

  ```sh
  codex-cli agent run --capsule <capsule> --allow-host-access
  ```

Failure modes:

- The operation, target, authorization, preconditions, or validation boundary
  is ambiguous.
- The capsule would contain a secret, token, private key, auth payload, or an
  unauthorized network/provider effect.
- The capsule path is inside the repository, permissions are not owner-only,
  an object is a symlink/hardlink, or the entrypoint digest does not match.
- A workspace capsule equals or descends from canonical `cwd`, or an allowed
  path escapes that `cwd`.
- Host access is needed but the operator has not explicitly selected that
  route.

## Entrypoint

Allocate a private project-scoped artifact directory:

```sh
agent-out project --topic <topic> --mkdir
```

Construct `run.sh` and `manifest.json` there with the active environment's
approved file-edit mechanism. Follow the manifest schema, digest fields,
precondition rules, and validation arrays in
`core/policies/execution-capsules.md`; do not invent a parallel capsule format.

## Workflow

1. Resolve the exact operation, `cwd`, allowed paths, authorization, and access
   class. Default to `workspace`.
2. Load `core/policies/execution-capsules.md` from the selected docs home and
   keep its direct/supervised parity, governance, and receipt boundaries.
3. Allocate the capsule through `agent-out project --topic <topic> --mkdir`.
   Never place it in the repository or repo-local `./agent-out`. Before
   authoring, canonicalize the result and enforce the workspace `cwd` and
   allowed-path containment rules; stop on a mismatch.
4. Author `run.sh` so it:
   - starts with `set -euo pipefail`;
   - enters or verifies the exact target;
   - checks branch, HEAD, files, or other relevant state before mutation;
   - uses project-governed commands without disabling hooks or signing;
   - is idempotent where practical and fails clearly otherwise;
   - performs essential validation for the direct operator path; and
   - omits sensitive values and unauthorized provider/network mutations.
5. Author `manifest.json` with
   `schema_version: "execution-capsule.v1"`, absolute `cwd`,
   `entrypoint: "run.sh"`, the final script digest, access and allowed paths,
   optional exact Git preconditions, and validation argv arrays.
6. Set directory and script mode `0700`, JSON mode `0600`, then recheck object
   type, ownership, digest, paths, and absence of sensitive values. Verify
   `codex-cli agent run --help` exposes `--capsule` before claiming the
   supervised route is currently runnable.
7. Return the absolute path and one-line commands. Do not make the operator
   reconstruct a long command from prose.
8. Do not run `run.sh` directly as the agent. Run a workspace capsule through
   `codex-cli agent run` only when the user also asked for supervised
   execution. For host capsules, prepare and report the
   `--allow-host-access` command for the operator instead of self-launching it.
9. After supervised execution, report the receipt path and concise final
   status. Keep receipts and event logs outside project history.

## Boundary

This skill is the discoverable preparation workflow. It does not replace or
duplicate the canonical execution-capsule policy, change the nils-cli schema,
grant authority, bypass sandbox limits, or turn host access into an agent-side
escape hatch.
