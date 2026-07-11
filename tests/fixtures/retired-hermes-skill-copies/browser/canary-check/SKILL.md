---
name: canary-check
description: >
  Run a local canary command, persist redacted evidence, and verify status through the nils-cli `canary-check` command.
---

# Canary Check

## Contract

Prereqs:

- `canary-check` is installed from the released nils-cli package and available on `PATH`.
- The command is safe to run locally and does not mutate production systems unexpectedly.
- The output directory is explicit.

Inputs:

- Canary name.
- Local command string.
- Output directory and optional verification format.

Outputs:

- Redacted canary result record, latest result display, or verification output.

Failure modes:

- The canary command exits non-zero.
- Output redaction or record writing fails.
- Verification finds no latest passing result.

## Entrypoint

Use the released CLI directly:

```bash
canary-check run --out /tmp/canary --name smoke --command "cargo test smoke"
canary-check verify --out /tmp/canary --format json
canary-check show --out /tmp/canary
```

## Workflow

1. Choose the smallest command that proves the runtime path under test.
2. Run through `canary-check run` so stdout, stderr, exit status, and redacted evidence are captured together.
3. Use `verify` before claiming the canary passed.
4. Treat a failed canary as a validation finding, not as a reason to invent success from partial output.

## Boundary

`canary-check` owns command execution evidence and redaction. The caller owns command safety, environment setup, and interpreting whether the canary is sufficient for the workflow.
