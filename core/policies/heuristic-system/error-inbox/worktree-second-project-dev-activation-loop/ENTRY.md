# Second managed worktree stuck in project-dev missing-activation loop

## Status

- Status: open
- First observed: 2026-07-16
- Area: hooks
- Severity: medium
- Versions: agent-docs 1.22.7, git-cli 1.22.7 (nils-cli 1.22.7)
- Related issue: graysurf/agent-runtime-kit#601
- Upstream issue: not filed; exact reproduction evidence is still required

## Signal

During one live `serenvia/agent-console` session, `project-dev` activation
worked for the first managed worktree but the workflow became stuck after
creating and entering a second worktree (`review-cleanup-base`). The pre-edit /
pre-bash hook repeatedly reported `missing-activation`; Bash and edit attempts
remained blocked until the operator intervened, so the review-thread cleanup
did not finish in that session.

The observed stall is real, but its root cause is not yet confirmed. The
original session did not retain the exact recovery argv, hook payload, command
result, or `session verify` JSON. A later controlled check with the same 1.22.7
surface successfully activated, preflighted, and verified two managed
worktrees of one repository in one session. That rules out a generic
"second/Nth project record cannot initialize" defect, but it does not exercise
the original `EnterWorktree` transition or prove that the Bash tool's effective
working repository matched the recovery command's `--project-path`.

The leading hypothesis is therefore a recovery-context mismatch at the hook /
tool-envelope boundary, already related to the real-workdir work in #601, not a
confirmed per-worktree record-initialization defect.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-16). No
  `skill-usage` envelope was retained. If the loop recurs, attach only redacted
  evidence through `heuristic-inbox ingest-evidence`.
- Environment: Linux; agent-docs / git-cli / nils-cli 1.22.7. Activation state
  must be compared using the resolved state home, session ID, product, and
  canonical project path; `AGENT_HOME` alone does not identify that state.
- Follow-up diagnostic: two existing managed worktrees accepted
  `session activate`, required preflight, and `session verify` in the same
  Codex session; both returned `verified=true`.
- Missing evidence: the original exact fully-qualified activation command,
  submitted shell text, effective tool CWD, exit code, stdout/stderr, verify
  result, and presence/absence of the expected hashed record.

## Impact

In the observed session, the second-worktree workflow was not self-recovering
and required operator intervention. An unattended agent encountering the same
context mismatch could be hard-blocked. The evidence does not establish that
all second worktrees, or the current 1.22.7 activation primitive by itself, are
permanently unactionable.

## Current Workaround

Before entering a newly created worktree, activate `project-dev` for its exact
canonical path and read its preflight using the complete trusted commands
printed by the hook. Keep the session ID, product, resolved state home, docs
home, and `--project-path` identical through activation and verification.

If already stuck after `EnterWorktree`, attempt recovery only with the Bash
tool envelope's `workdir` (effective CWD) set to the target worktree and submit
the exact printed activation argv by itself. Do not prefix it with `cd`, append
shell control, or attempt absolute-path edits before the target worktree
verifies. Run preflight and verification with the same tool workdir and state
tuple before editing.

If the host cannot expose or retain that target workdir, or the hook blocks the
exact activation argv there, no self-serve recovery is currently verified.
Preserve the worktree, return to an activated checkout, request operator
intervention, and route the effective-workdir gap through #601. Removing the
worktree and resyncing `main` remains a last resort.

## Promotion Criteria

Capture a minimal fresh-session reproduction that creates two managed
worktrees, enters the second before activation, and records redacted evidence
for the hook-selected repository plus the exact activate/preflight/verify
sequence. All commands must use the same session, product, state home, and
canonical project path.

- If the exact trusted activation succeeds, classify the incident under #601
  as an invocation / effective-workdir recovery gap and promote the durable
  workaround or host fix.
- If the exact trusted activation is itself blocked or fails verification,
  file the owning nils-cli / agent-docs issue with the deterministic repro and
  link its fix here.

After a fix or a supported recovery is validated end to end, update this entry
to `promoted` or `wontfix` and archive it through the heuristic-inbox lifecycle.

## Next Action

Keep this entry open as the durable tracker. On recurrence, ingest the redacted
command/payload/verification evidence above and link the resulting #601 or
upstream resolution. Do not change runtime behavior based only on the original
uncaptured session.
