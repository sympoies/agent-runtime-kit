# Codex CLI Agent Isolated Runtime Implementation Handoff

- **Status**: decided; implementation-ready; no unresolved design questions
- **Date**: 2026-07-23
- **Source**: In-session diagnosis and design discussion after
  `codex-cli agent` began inheriting the managed Codex home policy and hooks
- **Intended next step**: implement and locally validate the `codex-cli`
  isolated one-shot runtime in `sympoies/nils-cli`, release it, then adopt the
  released version and acceptance contract in `agent-runtime-kit`
- **Delivery constraint**: complete the implementation and commits locally;
  do not require a GitHub issue, pull request, or GitHub Actions
- **Retention**: coordination source; remove after the released behavior and
  runtime-kit acceptance have shipped, unless the runtime boundary is promoted
  into an owning canonical CLI specification

## Purpose

Make `codex-cli agent` a genuinely lightweight one-shot interface. Its
`prompt`, `advice`, `knowledge`, and `commit` commands must not implicitly load
the user's full Codex runtime, including home or project `AGENTS.md`, lifecycle
hooks, plugins, skills, MCP servers, memories, goals, or subagent definitions.

The one-shot commands retain the current repository, ordinary shell tooling,
Git identity and signing environment, and the user's existing Codex
authentication. The normal default is an isolated, ephemeral child Codex
runtime. The legacy inherited runtime remains available only through an
explicit opt-in. `agent resume` remains inherited because its purpose is to
resume state stored under the real `CODEX_HOME`.

Isolation must be created at the child-process boundary in `codex-cli`. Do not
implement this feature by teaching runtime-kit hooks to exempt or bypass
`codex-cli agent`.

## Confirmed Facts

- `codex-cli 1.25.9` implements `agent prompt`, `advice`, and `knowledge` as
  wrappers around the installed `codex exec` binary. The shared executor
  inherits the parent environment and working directory. [F1]
- The current Codex-style executor always passes
  `--dangerously-bypass-approvals-and-sandbox`, selects `workspace-write`, and
  does not pass `--ignore-user-config`, `--ignore-rules`, or
  `--disable hooks`. [F1]
- The executor uses `CODEX_CLI_MODEL` and `CODEX_CLI_REASONING`, optionally adds
  `--ephemeral`, refreshes configured remote auth before launch, and then
  starts `codex` with inherited stdio. [F1]
- `agent commit` currently launches the same child agent with a prompt that
  instructs it to invoke `semantic-commit`. When `semantic-commit` is absent,
  it falls back to an interactive raw `git commit` and optional `git push`.
  [F2]
- `agent resume` resolves a session working directory from
  `$CODEX_HOME/sessions` and launches native `codex resume`; it therefore has a
  materially different persistence contract from the one-shot commands. [F3]
- Codex 0.144.6 exposes `exec --ignore-user-config`, `--ignore-rules`,
  `--ephemeral`, generic `--disable <feature>`, and
  `debug prompt-input`. `--ignore-user-config` explicitly leaves auth rooted
  in `CODEX_HOME`. [A1][W1]
- Codex reads global instructions from `$CODEX_HOME/AGENTS.md` and project
  instructions from the repository path. `project_doc_max_bytes=0` removed the
  project-local instructions in a local `debug prompt-input` probe but did not
  remove the global home instructions. An empty child `CODEX_HOME` is therefore
  required in addition to the zero-byte project-doc override. [A2][W2]
- The current runtime-kit Codex home deliberately contains the rendered global
  `AGENTS.md`, plugin registrations, user configuration, and lifecycle-hook
  registrations. Inheriting that home makes the wrapper a second full managed
  agent rather than a lightweight helper. [F4]
- Runtime-kit's existing product smoke already proves the base isolation shape
  of a temporary `CODEX_HOME` combined with
  `codex exec --ignore-user-config --ephemeral`. The new implementation
  productizes and strengthens that tested shape. [F5]
- The user requires the helper to avoid default `AGENTS.md` and lifecycle hooks
  so quick tasks do not pay the full managed-runtime context and admission
  cost. [U1]

## Policy And Product Decisions

1. `codex-cli agent prompt`, `advice`, `knowledge`, and `commit` default to an
   `isolated` runtime.
2. Add `--runtime isolated|inherited` to those four commands. The default is
   `isolated`; `--runtime inherited` is the only CLI opt-in to the legacy full
   runtime.
3. Add `CODEX_CLI_AGENT_RUNTIME=isolated|inherited`. Precedence is CLI flag,
   then environment, then the built-in `isolated` default. Invalid values are
   usage errors and never fall back.
4. `agent resume` accepts no runtime selector and always uses the real inherited
   `CODEX_HOME` and existing native resume behavior.
5. Isolated mode always uses `--ephemeral`. The existing `--ephemeral` flag
   remains accepted as a compatibility no-op in isolated mode and retains its
   current meaning in inherited mode.
6. Isolated mode does not require `CODEX_ALLOW_DANGEROUS_ENABLED` and never
   passes `--dangerously-bypass-approvals-and-sandbox`. That environment gate
   remains part of the explicit inherited compatibility path.
7. Isolated mode uses `approval_policy=never` with a command-specific sandbox.
   Operations outside the sandbox fail and return to the agent; the wrapper
   never pauses for an approval prompt.
8. Isolation is fail-closed. If the installed Codex lacks a required flag or
   feature, the wrapper reports the missing capability and requires either an
   upgrade or explicit `--runtime inherited`; it never degrades silently.
9. No runtime-kit hook receives a command exemption, bypass token, special
   timeout posture, or allowlist entry for this feature.
10. An outer agent remains authoritative. If another Codex session invokes
    `codex-cli agent` through its shell tool, that outer session's hooks may
    inspect or block the wrapper invocation. Only the child Codex runtime is
    isolated.
11. Native Git hooks, commit signing, repository permissions, OS controls, and
    administrator-managed Codex requirements remain active. The feature
    removes user/project runtime customization, not product or operating-system
    safety boundaries.

## Runtime Modes

| Surface | `isolated` default | `inherited` opt-in |
| --- | --- | --- |
| Authentication | Bridge the active credential only | Use the real Codex home |
| User `config.toml` | Ignore | Load |
| Home `AGENTS.md` | Absent from child home | Load |
| Project `AGENTS.md` | Disable with `project_doc_max_bytes=0` | Load |
| User/project execpolicy rules | Ignore | Load |
| Lifecycle hooks | Force-disable | Load |
| Plugins, skills, MCP, apps | Absent or force-disabled | Load |
| Memories, goals, subagents | Force-disabled | Load |
| Repository working directory | Preserve | Preserve or resume recorded cwd |
| Shell `HOME`, `PATH`, Git, SSH, GPG | Preserve | Preserve |
| Session files | Never persist | Existing behavior |
| Codex built-in instructions | Preserve | Preserve |
| OS/administrator-managed policy | Preserve | Preserve |

## Command Capability Matrix

| Command | Runtime | Sandbox and tools | Mutation owner |
| --- | --- | --- | --- |
| `agent prompt` | Isolated by default | `workspace-write`; core local tools only | Child Codex inside the workspace |
| `agent advice` | Isolated by default | `read-only`; repository inspection allowed | None |
| `agent knowledge` | Isolated by default | `read-only`; repository inspection allowed | None |
| `agent commit` | Isolated by default | No-shell/read-only message generation | `codex-cli` plus `semantic-commit` |
| `agent resume` | Always inherited | Native resumed Codex session | Resumed session |

`prompt` intentionally remains capable of a small workspace edit because it is
an explicit user-invoked quick-operation surface. `advice` and `knowledge` are
read-only by contract. `commit` does not delegate repository mutation to the
model.

## Isolated Child Home Contract

Before changing `CODEX_HOME`, capture the source Codex home and resolve auth.
The child home lifecycle is:

1. Resolve the original Codex home from the non-empty incoming `CODEX_HOME`,
   otherwise `$HOME/.codex`.
2. Run the existing configured remote-auth refresh before constructing the
   child environment.
3. Resolve a usable file-backed auth source in this order:
   - an existing `CODEX_AUTH_FILE`;
   - an existing auth path returned by the provider runtime;
   - `<original CODEX_HOME>/auth.json`.
4. Create a unique temporary directory with mode `0700`, preferring a writable
   `XDG_RUNTIME_DIR` and otherwise the platform temporary directory.
5. When a file-backed auth source exists, create only an `auth.json` symlink in
   the child home. Never copy credential contents. When file-backed auth is
   absent, leave the child home without `auth.json` so the official Codex
   credential store can resolve normally.
6. Do not create `config.toml`, `AGENTS.md`, `hooks.json`, `plugins`, `skills`,
   `agents`, or session-history links in the child home.
7. Run the child with the temporary directory as `CODEX_HOME` and preserve the
   caller's real `HOME`, current working directory, toolchain, Git config,
   signing agents, and stdio.
8. Remove the temporary home after child exit. Cleanup failure is a warning
   that names only the temporary path; it does not expose credential data.

The wrapper must never print auth contents or include them in debug output. If
Codex replaces the child `auth.json` symlink with a regular file, do not copy
that file back over the source credential. Emit a typed
`isolated-auth-write-not-propagated` warning and allow the normal auth refresh
owner to reconcile credentials later.

On platforms where a safe file symlink cannot be created, a required
file-backed credential produces a typed `isolated-auth-bridge-unavailable`
failure. Do not copy the secret or inherit the full home as fallback.

## Child Environment Contract

The isolated child inherits the ordinary shell environment except for runtime
control-plane variables. Override `CODEX_HOME` with the temporary home and
remove these child-visible families after the parent wrapper has consumed
them:

- `CODEX_AUTH_FILE`, `CODEX_SECRET_DIR`, `CODEX_SECRET_CACHE_DIR`, and
  `CODEX_AUTH_REMOTE_*`;
- `AGENT_DOCS_*`, `AGENT_SESSION_*`, `AGENT_HOOK_*`, and
  `AGENT_EVIDENCE_*`.

Keep `HOME`, `PATH`, `XDG_*`, `SSH_AUTH_SOCK`, Git configuration variables,
and signing-related variables. This is runtime isolation, not a hermetic build
container.

The existing `nils-common::process` helper supports environment overrides but
not removals. Implement a typed process specification that accepts cwd,
overrides, and removals, or use an equivalent Codex-specific command builder.
Do not mutate the parent process environment with global `set_var` calls.

## Required Codex Invocation

The isolated executor constructs the equivalent of:

```text
CODEX_HOME=<temporary-home> codex --ask-for-approval never exec
  --ignore-user-config
  --ignore-rules
  --ephemeral
  --skip-git-repo-check
  --disable hooks
  --disable plugins
  --disable remote_plugin
  --disable apps
  --disable memories
  --disable goals
  --disable multi_agent
  --disable workspace_dependencies
  -c project_doc_max_bytes=0
  --model <CODEX_CLI_MODEL-or-default>
  -c model_reasoning_effort=<CODEX_CLI_REASONING-or-default>
  --sandbox <read-only-or-workspace-write>
  -- <prompt>
```

Arguments must be passed as exact argv entries, never shell-interpolated.
CLI-supplied model, reasoning, sandbox, feature, and project-doc values have
the highest ordinary configuration precedence. The empty home removes global
instructions and trust records; `--ignore-user-config` prevents user config
loading; the zero-byte project-doc limit removes project instructions; and the
feature disables defend against project/runtime surface reactivation.

Administrator-managed requirements that the product refuses to override remain
effective by design.

## Capability Detection And Diagnostics

Add:

```text
codex-cli agent doctor [--format text|json]
```

The same probe used by execution and doctor must verify without an API call:

- `codex exec --help` advertises `--ignore-user-config`, `--ignore-rules`,
  `--ephemeral`, `--skip-git-repo-check`, and generic `--disable`;
- `codex features list` contains every feature the isolated profile disables;
- a secure child home can be created and removed;
- a required auth link can be created without reading credential contents;
- a `codex debug prompt-input` sentinel probe with a temporary home and
  `project_doc_max_bytes=0` omits both home and project instruction sentinels;
- no lifecycle-hook sentinel executes during the diagnostic probe.

Text and JSON diagnostics report capability names and boolean readiness only.
They must not report token values, auth payloads, secret paths, hook bodies, or
the contents of ignored instructions.

Execution runs the cheap CLI/feature capability checks and fails before an API
request when isolation is unsupported. `doctor` owns the fuller sentinel
diagnostic.

Stable failure codes:

| Code | Meaning | Recovery |
| --- | --- | --- |
| `isolated-runtime-unsupported` | Required Codex flag or feature missing | Upgrade Codex or explicitly choose `inherited` |
| `isolated-home-create-failed` | Secure child home unavailable | Repair local filesystem/runtime-dir permissions |
| `isolated-auth-bridge-unavailable` | Required auth cannot be exposed safely | Repair the auth store or link capability |
| `isolated-instruction-leak` | Diagnostic sentinel reached model input | Stop; do not run isolated mode |
| `isolated-hook-leak` | Diagnostic hook executed | Stop; do not run isolated mode |
| `isolated-auth-write-not-propagated` | Child replaced the auth link | Warning; refresh through the normal auth owner |

## CLI Compatibility Contract

The command shape is:

```text
codex-cli agent prompt [--runtime isolated|inherited] [--ephemeral] [PROMPT...]
codex-cli agent advice [--runtime isolated|inherited] [--ephemeral] [QUESTION...]
codex-cli agent knowledge [--runtime isolated|inherited] [--ephemeral] [CONCEPT...]
codex-cli agent commit [--runtime isolated|inherited] [--ephemeral]
                       [-a|--auto-stage] [-p|--push] [EXTRA...]
codex-cli agent resume <SESSION_ID> [--cd <dir>]
codex-cli agent doctor [--format text|json]
```

- `CODEX_CLI_AGENT_RUNTIME` is included in `codex-cli config show` and accepted
  by `codex-cli config set`.
- Existing scripts that pass `--ephemeral` continue to parse.
- `--runtime inherited` preserves the current agent executor, dangerous-mode
  gate, home loading, and optional persistence semantics.
- `agent resume` argv and exit-code behavior remain unchanged.
- Help text must identify `isolated` as the default and describe `inherited` as
  loading the user's full Codex home policy and integrations.

## Deterministic Commit Contract

The isolated `agent commit` path replaces the current prompt-controlled
mutation and removes the raw Git fallback.

### Repository preparation

1. Require `git` and `semantic-commit`; missing `semantic-commit` is a typed
   dependency failure, not fallback mode.
2. Resolve one canonical Git root.
3. Without `--auto-stage`, require at least one staged path and do not alter the
   index.
4. With `--auto-stage`, run the existing exact `git -C <root> add -A` action.
   If a later step fails, leave the resulting index intact and report that it
   remains staged; do not attempt a lossy rollback.
5. Capture the original `HEAD` object and staged-tree object (`git write-tree`)
   before model generation.

### Message generation

1. Obtain the only model-visible repository context through
   `semantic-commit staged-context --format bundle --repo <root>`.
2. Write the response schema inside the child temporary home. It accepts only:

   ```json
   {
     "type": "fix",
     "scope": "runtime",
     "subject": "isolate codex agent helpers",
     "body_bullets": []
   }
   ```

3. Invoke isolated Codex in `read-only` mode with shell and unified-exec
   features disabled, the staged bundle embedded in the prompt, and
   `--output-schema` plus `--output-last-message` targeting temporary files.
4. The model returns message fields only. It cannot stage, commit, push, read
   additional repository files, or execute `semantic-commit` itself.
5. Parse the structured result strictly. Reject unknown fields, invalid commit
   types, empty subject, invalid scope, newline injection, headers over the
   configured width, and body lines that cannot be represented as
   `--body-bullet` arguments.

### Commit and push

1. Re-read `HEAD` and `git write-tree`; both must equal the captured values.
   A changed HEAD or index is a concurrency failure and creates no commit.
2. Invoke `semantic-commit commit` with structured
   `--type`, optional `--scope`, `--subject`, repeated `--body-bullet`,
   `--expect-head <captured-head>`, `--repo <root>`, and the existing summary
   mode. `semantic-commit` remains the only commit primitive.
3. `--push` is an explicit user request. Only after a successful commit may the
   wrapper perform the existing current-upstream push behavior. The model never
   chooses a destination or executes the push.
4. A push failure does not rewrite or delete the successful local commit; report
   the committed object and the push failure separately.
5. Extra user text may influence message wording only. It cannot add commands,
   change the staged context, override the runtime mode, select a push target,
   or weaken validation.

The inherited `agent commit --runtime inherited` path preserves the existing
agent-driven behavior for compatibility during this change. It remains an
explicit full-runtime opt-in and is not the default.

## Implementation Ownership

### `sympoies/nils-cli`

Own all behavior changes:

- `crates/codex-cli/src/cli.rs`: runtime selector, doctor command, and help.
- `crates/codex-cli/src/main.rs`: route runtime options and doctor.
- `crates/codex-cli/src/runtime/`: runtime-mode resolution, capability probe,
  child-home/auth bridge, child environment, and isolated invocation builder.
- `crates/codex-cli/src/agent/`: command capability selection and deterministic
  commit workflow.
- `crates/nils-common/src/process.rs` only if a shared typed environment-removal
  primitive is justified; otherwise keep the process builder Codex-local.
- `crates/codex-cli/tests/integration/`: argv, environment, auth bridge,
  isolation, compatibility, doctor, and commit regression coverage.
- `crates/codex-cli/README.md` and retained CLI contract docs.

Do not change Gemini, OpenCode, or other provider wrappers as part of this
implementation.

### `agent-runtime-kit`

After the nils-cli release:

- advance the validated nils-cli pin and relevant `codex-cli` compatibility
  floor through the normal version-baseline workflow;
- add or extend product smoke so the installed `codex-cli agent` default is
  proven isolated with sentinel home/project instructions and hooks;
- update the Codex harness narrative to distinguish the full managed Codex
  surface from the isolated `codex-cli agent` child runtime;
- retain all outer hook policies unchanged.

The hook-timeout degraded-admission implementation is separate. This feature
prevents the isolated child from loading those hooks but does not repair timeout
behavior for full managed Codex sessions or outer-agent invocations.

## Non-Scope

- No global disablement or removal of runtime-kit hooks.
- No hook allowlist or bypass for the `codex-cli agent` executable.
- No change to the full `codex` CLI, desktop app, IDE, or ordinary Codex
  sessions.
- No alternate Codex account, duplicated credential store, or copied auth
  payload.
- No persistent isolated session and no isolated `agent resume` mode.
- No container, VM, or fully hermetic shell-environment guarantee.
- No remote provider delivery abstraction for `agent commit --push` beyond the
  existing current-upstream behavior.
- No implementation changes to runtime-kit before a released nils-cli surface
  exists.

## Acceptance Criteria

- A1: A default `agent prompt` child receives a unique temporary `CODEX_HOME`,
  `--ignore-user-config`, `--ignore-rules`, `--ephemeral`, feature disables,
  and `project_doc_max_bytes=0`; it does not receive
  `--dangerously-bypass-approvals-and-sandbox`.
- A2: Home and project `AGENTS.md` sentinels are absent from model-visible
  prompt input in isolated mode and present in an explicit inherited control.
- A3: User and project lifecycle-hook sentinels do not execute in isolated mode
  and do execute in the inherited control when otherwise trusted and enabled.
- A4: Isolated mode does not discover configured plugins, skills, MCP servers,
  memories, goals, or subagent definitions from the real Codex home.
- A5: File-backed auth is exposed only through a temporary symlink; tests prove
  no credential copy, content log, or full-home link is created.
- A6: `prompt` can modify only its workspace sandbox; `advice` and `knowledge`
  cannot modify the workspace.
- A7: Missing isolation capabilities or an unsafe auth bridge fail before an
  API request and never fall back to inherited mode.
- A8: `--runtime inherited` retains the current child argv/config loading and
  dangerous-mode gate, while `agent resume` retains its exact existing argv and
  session lookup behavior.
- A9: Isolated `agent commit` generates structured message fields from only the
  staged bundle, rejects invalid output, detects HEAD/index drift, and commits
  only through `semantic-commit`.
- A10: Missing `semantic-commit` creates no commit; the raw `git commit`
  fallback is absent from the isolated path.
- A11: `--push` executes only after a successful commit and cannot be requested
  by model output or extra prompt text.
- A12: `agent doctor --format json` reports a stable, secret-free capability
  result and performs no model/API request.
- A13: No runtime-kit hook policy, manifest, or registration contains an
  exemption for `codex-cli agent`.
- A14: The released nils-cli version is adopted by runtime-kit and its isolated
  product smoke passes before this coordination document is retired.

## Validation Plan

In `sympoies/nils-cli`, add red-first tests for the default argv and environment
contract before production edits, then run at minimum:

```bash
cargo test -p codex-cli
cargo test -p nils-common
cargo fmt --all -- --check
```

Run the repository's declared full validation before release. Targeted coverage
must include:

- stubbed Codex argv and environment capture for isolated/inherited modes;
- secure temporary-home creation, auth symlink, link-replacement warning, and
  cleanup;
- `debug prompt-input` home/project instruction sentinels without network;
- hook, plugin, MCP, skill, memory, goal, and subagent sentinels;
- unsupported capability and auth-bridge failures;
- read-only versus workspace-write command behavior;
- structured commit output parsing, message validation, HEAD/index races,
  dependency failure, auto-stage failure, and push ordering;
- unchanged resume tests and legacy inherited-mode tests.

After releasing nils-cli and adopting it in `agent-runtime-kit`, run:

```bash
bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only
bash scripts/ci/all.sh
bash tests/hooks/run.sh
```

Add one authenticated manual smoke only after deterministic probes pass:

```text
codex-cli agent doctor
codex-cli agent knowledge 'reply with the active runtime mode only'
```

The smoke must show `isolated`, must not invoke `agent-hook`, and must not
surface home or repository `AGENTS.md` content.

## Risks And Guardrails

- **Isolation accidentally becomes a policy bypass**: outer-agent hooks remain
  authoritative, and runtime-kit receives no exemption.
- **Partial isolation still loads global instructions**: use both an empty
  child home and `project_doc_max_bytes=0`; doctor verifies sentinels.
- **Auth duplication or stale refresh state**: link, never copy; refresh before
  launch; do not propagate a child replacement file automatically.
- **Removing hooks also removes all mutation safety**: isolated mode removes
  dangerous bypass, applies command-specific sandboxes, and makes commit
  mutation deterministic.
- **Silent compatibility regression on older Codex**: capability probe fails
  closed and requires explicit inherited opt-in.
- **Model-controlled commit or push**: the model returns structured message
  fields only; the wrapper validates and owns every mutation.
- **Index race during message generation**: compare both HEAD and staged-tree
  object immediately before commit.
- **Scope expansion into other provider wrappers**: implementation ownership is
  Codex-only.

## Execution

- Status: not started; ready for direct local implementation.
- Next-task source: this document.
- Recommended next workflow: implement test-first in `sympoies/nils-cli`, run
  its declared validation, release locally, then perform the runtime-kit
  version adoption and product-smoke update.
- This is a `docs/discussions/` capture, not an L2 plan bundle; it intentionally
  contains no recommended plan or execution-state path.

## Retention Intent

Coordination material; cleanup-eligible after the released `codex-cli` behavior
and runtime-kit acceptance ship. Promote the runtime-mode contract into the
owning nils-cli specification only if future consumers require it as a stable
public API reference.

## Read-First References

- `[U1]` User decision in this session: the one-shot helper must not load
  default `AGENTS.md` or lifecycle hooks and must remain suitable for fast
  local work.
- `[F1]` `sympoies/nils-cli:crates/nils-common/src/provider_runtime/exec.rs`,
  `crates/codex-cli/src/runtime/mod.rs`, and
  `crates/codex-cli/src/agent/mod.rs` — current inherited executor.
- `[F2]` `sympoies/nils-cli:crates/codex-cli/src/agent/commit.rs` and the
  `semantic-commit-staged` / `semantic-commit-autostage` prompts — current
  agent-driven commit and raw-Git fallback.
- `[F3]` `sympoies/nils-cli:crates/codex-cli/src/agent/resume.rs` and
  `crates/nils-provider-resume/src/lib.rs` — real-home session lookup and native
  resume.
- `[F4]` `docs/source/harness-shape-codex.md` — installed home prompt, plugin,
  hook, and configuration surfaces.
- `[F5]` `tests/runtime-smoke/product/run.sh` — existing temporary-home Codex
  isolation probe.
- `[A1]` Local `codex 0.144.6` `exec --help`, `features list`, and
  `debug prompt-input` inspection on 2026-07-23.
- `[A2]` Local prompt-input comparison on 2026-07-23: the zero-byte project-doc
  override omitted repository instructions while the real home instructions
  remained.
- `[W1]` OpenAI Codex CLI command reference:
  <https://learn.chatgpt.com/docs/developer-commands?surface=cli>.
- `[W2]` OpenAI Codex `AGENTS.md` discovery reference:
  <https://learn.chatgpt.com/docs/agent-configuration/agents-md>.

## Recommended Next Artifact

The nils-cli implementation diff and its targeted test evidence. Do not create
an issue-backed plan unless the direct implementation later expands into
independent delivery lanes.
