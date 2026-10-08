# Runtime Hooks

`core/hooks/shared/` is the canonical source for hook logic shared by Codex and
Claude. `core/policies/agent-hook/runtime-kit-v1.toml` owns selection and
ordering; `agent-hook setup` owns the provider-native ingress.

The shared scripts accept neutral `AGENT_RUNTIME_*` environment variables. Do
not fork a hook per product unless the payload protocol or runtime harness
requires different behavior.

The finish-line hooks credit declared validation only after an observed
successful exit. `PreToolUse` wraps each matched Bash command with a tokenized
EXIT recorder that persists bounded outcome metadata and preserves the
command's status. Composite commands are credited only when their shell
control flow consists entirely of declared validation commands, because an
input rewrite also grants permission to the complete rewritten command. The
authorization matcher retains operator and evaluation-sensitive quote syntax
while normalizing harmless quoted words, so a quoted literal cannot be
reinterpreted as live shell control flow.
When a submitted command contains declared validation but unrelated setup or
control flow makes the aggregate status unprovable, `PreToolUse` emits one
fixed `validation_outcome_unprovable` advisory and runs the command unchanged.
It does not register an outcome or echo the submitted command. Repositories
whose validation requires a particular runtime, environment, or other setup
should declare one repository-owned wrapper that performs and verifies that
setup, runs the complete validation contract with failure-preserving
semantics, and returns its aggregate status. Put toolchain selection inside
that declared wrapper, never in an uncredited caller-side `eval`, `source`,
environment preamble, directory change, or shell suffix.
Attempts are ordered at PreToolUse creation, so a stale completion cannot
overwrite a newer attempt; an outcome that cannot persist leaves its pending
attempt blocking the gate. A bounded recovery descriptor travels with the
wrapper so removal of the pending directory recreates authoritative dirty and
failure state. Each active attempt also has an authoritative tombstone under
shared runtime state (`AGENT_RUNTIME_VALIDATION_STATE_HOME`, then
`AGENT_RUNTIME_STATE_HOME`, then the XDG state root). It remains blocking when
repo-local state cannot persist; if either side cannot register before launch,
the matching validation command is blocked and can be retried after repair.
Code-edit hooks are also fail-closed before the edit starts when shared dirty
state cannot be registered, preventing an unwritable marker directory from
hiding a later real edit. Multi-contract edits acquire every marker-directory
lock in stable order and roll back provisional markers if any write fails;
generation checks preserve a newer marker from a concurrent edit. A
repo-scoped runtime-state lock serializes edit, validation-outcome, Stop, and
terminal-cleanup transitions; cleanup also compares the exact satisfied state
snapshot after taking the local namespace lock and fails closed on change.
Tombstones use a stable lexical contract identity plus target keys that include
the product and declared command. When the hook payload identifies a runtime
session, dirty markers, command outcomes, and tombstones live in directly
addressable namespaces keyed by an opaque hash of that session identifier, so
unrelated retained state is not scanned on the current session's hot path. An
editing session still
shares its dirty generation across products, but unrelated and newly started
sessions do not inherit its outstanding session-scoped work. Unresolved
pre-upgrade legacy state remains transitional authority until an identified
session completes a newer successful validation. Pending or failed transition
attempts retain the legacy authority; success clears it or suppresses it with
the shared success marker. Payloads without a session
identifier retain the legacy shared marker contract. A newer attempt reduces
only its exact session and command targets, plus matching legacy targets during
that transition; it cannot clear another identified session's state.
Successful Stop retires the completed session's repo-local marker namespace.
When products share a session, terminal product markers let the last successful
product retire the whole namespace. Any later shared edit invalidates every
product's terminal marker, and a new validation attempt invalidates its active
product's terminal marker until the attempt completes. Cleanup also rejects a
foreign terminal generation older than the current dirty generation; any
foreign evidence owner is parsed from its complete contract stem and structured
product suffix, with unknown or ambiguous names retained fail-closed. Any
unresolved product therefore keeps the namespace fail-closed. Removed,
replaced, or reordered commands become an explicit contract-change blocker.
Only the exact internal names `.terminal-codex`, `.terminal-claude`, and
`.terminal-shared` are terminal metadata; validation contract stems may safely
begin with `.terminal-` or overlap another contract stem.
Each tombstone also retains the original edit generation (or an explicit
no-edit value), so another product in the same session sees a real edit without
inheriting its failure or being invalidated by retries for the same edit.
Unmatched contract state remains scoped to its owning product.
Marker paths and their derived state directory must remain beneath the real
repository root; atomic marker writes do not follow final symlinks, and marker
ordering accepts only non-symlink regular files.
The wrapped shell's `EXIT` trap is the only outcome recorder; there is no broad
PostToolUse hook on ordinary Bash completions. Equivalent persistence-failure
blockers are compacted under a shared lock so fail-closed state remains bounded.
A failed outcome stays outstanding and the Stop gate proposes owner-based
routing before honoring a validation waiver. The hooks retain neither raw
command output nor provider artifacts and never open an issue automatically.

Selective intent activation uses the durable `session prepare/status/verify`
surface that every supported `agent-docs` release ships; the hooks do not probe
for it. `user-prompt-agent-docs.sh` expands required docs for active intents and
lists inactive routes without injecting their runbooks; it always passes
`--require-declared-intent --product <product>` to `preflight` and stays silent
when no `codex`/`claude` runtime product is set. `pre-edit-intent-gate.py` then checks `project-dev`
for every canonical target repository before direct edits and against the
shared shell command context.

`AGENT_RUNTIME_PROJECT_DEV_MODE` selects `advisory` (the default), `enforce`, or
`off`. Advisory mode attempts one bounded exact preparation for each unprepared
attested target and allows the original work whether preparation succeeds or
not. Successful auto-preparation includes the exact, phase-qualified
`agent-docs preflight --intent project-dev` command to read the prepared
contract; failures use `project-dev-advisory-unavailable` plus exact recovery
when available. A preparation near miss in advisory mode is not consumed as a
trusted bootstrap and executes normally with corrected bootstrap guidance;
enforce mode blocks the same near miss before execution. Invalid mode values
deterministically degrade to advisory. Enforce retains fail-closed verification
and target-specific recovery. Off disables only this project-dev workflow
check; checkout ownership, work-context coordination, validation,
delivery/signing, credential-protection, provider, OS, and user-authority hooks
still run.

Direct edits discover and verify each explicit target independently. Bash uses
a host-attested command workdir: Codex inline metadata, a matching bounded
transcript call, provider session cwd, or the exact cwd in a ready private
`agent-session` record whose session id and runtime incarnation match the hook
process. This last route keeps a target-rooted Claude worker usable when its
Bash envelope omits cwd or its current call has not yet been flushed to the
transcript. The managed record may only attest the same physical process cwd;
it cannot redirect the target. A plain process-cwd or unauthenticated
mismatched-call fallback is recorded as un-attested and receives
`workdir-attestation-missing` instead of silently becoming a cross-repository
target. Its message tells the agent not to repeat unchanged Bash and names the
supported Codex workdir, managed
target-rooted session, and exact-path edit routes. Shell-expanded
destinations remain unobservable. A shell-embedded `agent-run exec --cwd`
cross-repository hop stays fail-closed in enforce mode with
`cross-repository-target-unsupported`; V1 requires a target-rooted session or
host-attested workdir. Admitting that wrapper later requires a typed nils-cli
command-context primitive that binds release provenance, canonical cwd, wrapper
grammar, and child argv once for every mutation-sensitive guard.
Recovery diagnostics make that route operational: resubmit the mutation as a
standalone tool call whose top-level `workdir` is the target checkout; for
staging, run `git add -- <owned-paths>` there and invoke `semantic-commit`
separately. They explicitly reject shell `cd`, raw `git -C`, and nested
`agent-run exec --cwd` as substitutes, and name a target-rooted managed session
as the fallback when the host cannot attest a target workdir.
Exact help/version argv for the
managed `agent-docs` and `forge-cli` release surface remains read-only, while
extra options, trailing arguments, and executable shadows fail closed. When
verification blocks a single-repository edit or shell mutation, the reason
includes a complete, copyable `session prepare` command — the atomic
activate-plus-strict-preflight primitive — with the trusted executable and
session context. A successful in-hook prepare keeps `[reason: prepared]` and
adds `[action: retry-original]`: do not run the prepare command again; retry the
original blocked command. The older `session activate` bootstrap remains accepted for
backward compatibility. The gate does not probe `agent-docs` for the session or
`--phase` surface, which every supported release ships; a missing, timed-out,
crashed, malformed, or pre-session binary fails at `session verify` like any
unverified session, so enforce blocks and advisory preserves the work. Before any probe, the hooks require the
resolved `agent-docs` executable to live in a known managed CLI directory
(`/opt/homebrew/bin`, `/home/linuxbrew/.linuxbrew/bin`, `/usr/local/bin`,
`/usr/bin`, or the per-user `~/.local/nils-cli/bin` produced by
`NILS_WRAPPER_INSTALL_PREFIX`); Homebrew links must resolve under that prefix's
`Cellar/nils-cli` package, while `/usr/bin` and the per-user root hold regular
files and so must resolve to themselves. The per-user root is owner-writable,
but so is the Homebrew prefix on Linux hosts, so trusting it adds no weakness
the packaged list did not already carry. Any other installation requires an
explicit launch-time `AGENT_RUNTIME_TRUSTED_CLI_ROOT`, which narrows trust to
exactly the roots it names in the gates that pair it with a repository-local
executable check; repository-local candidates are always rejected. These hooks are mechanical guardrails, not a security sandbox: the
product launch environment, managed runtime home, and an explicit trusted-root
override remain host trust boundaries. Hermes has no runtime-kit hook runner.

The shared `command_context` helper in `hook_common.py` resolves the canonical
working directory, source, attestation, and optional stable diagnostic for a
tool call. Its `effective_workdir` compatibility wrapper means
`pre-edit-intent-gate.py`,
`checkout-lease-guard.py`, `block-unsafe-default-delivery.py`,
`agent-scope-lock-guard.py`, and `block-direct-python.py` all agree on the
target repository instead of each reading the hook process cwd (issue #601
P0-4). It fans out across the union of Codex and Claude tool envelopes: explicit
workdir keys (`workdir`, `cwd`, `current_working_directory`,
`working_directory`) nested anywhere in the tool input; then the Codex
`exec_command` transcript, whose legacy `arguments` or anchored custom-tool
`tools.exec_command(<strict JSON>)` input carries the `workdir` in the event
matching this call's `tool_use_id`/`call_id`; then non-session payload metadata;
then the top-level session `cwd`; then a bounded 64 KiB private managed-session
record whose id, agent, ready state, runtime incarnation, owner/mode, and cwd all
match the current hook process; and finally process cwd. Absolute inline,
matching-transcript, payload, ordinary session-cwd, and authenticated
managed-session-cwd values are attested. Relative values and plain process cwd
are not. A transcript-call mismatch keeps payload/session cwd un-attested, but
does not suppress an independently authenticated managed-session cwd matching
that same resolved path. The transcript tail remains capped at 4 MiB.
The custom-tool form accepts one optional strict-JSON `// @exec:` pragma and
one complete canonical wrapper only; additional JavaScript or another exec
call makes the workdir ambiguous rather than borrowing the first call's target.
Its argument is strict JSON or a flat object literal whose keys are identifiers
or JSON strings and whose values are JSON scalars or names bound by leading
`const NAME = "<JSON string>"` declarations; a JSON decoder and a JavaScript
engine read that subset identically. In the object-literal form, duplicate
keys, nested values, spreads, computed keys, comments, template or
single-quoted strings, and other bindings stay unreadable; strict JSON keeps
its own rules, where the last duplicate key wins as it does in JavaScript and
only the top-level `workdir` is read. The wrapper may bind the result and render it with `text(r)`,
`text(r.output)`, or `text(JSON.stringify(r))`, or render the call directly as
`text(await tools.exec_command(...))` or
`text((await tools.exec_command(...)).output)`. When the matching transcript
call exists but its workdir is unreadable, a managed-session-cwd result
reports `call_workdir_unreadable`: that session record attests the session
root, not this call, and `block-unsafe-default-delivery.py` then treats the
call's repository as unresolved.
Direct-edit verification stays target-based; shell verification is
command-context based.

`checkout-lease-guard.py` coordinates one writer per physical Git checkout
across Codex and Claude only when the managed launch explicitly selects
`AGENT_SESSION_COORDINATION_MODE=enforce`. Missing, invalid, `advisory`, and
`off` modes bypass the lease without acquiring or blocking, so ordinary
iTerm-launched agents remain valid non-participants. In enforce mode, explicit
edit tools participate; Bash
participates only for conservative high-confidence mutations, including known
nested shell / `agent-run exec` forms and managed worktree removal, so read-only
recovery remains available. In particular, `semantic-commit` help and dry-run
forms do not acquire a writer lease unless the command includes the
file-writing `--message-out` option; a mutating `default-branch` invocation is
classified as a checkout writer too. Managed worktree slugs resolve through the
authoritative `git-cli` inventory, and removal must be the command's sole
mutation with exactly one removal target. In every mode a trusted
`git-cli worktree remove <target> --safe --format json` delegates to the CLI's
execution fence without claiming a writer lease in PreToolUse. The CLI holds
checkout/session locks and proves clean, stable, managed, idle and delivered
state before removal. Older binaries reject `--safe`; advisory removal without
it stays blocked. Incomplete process or ownership visibility retains the
worktree. Batch `git-cli branch cleanup --remove-worktrees` remains blocked in
agent shells because older CLIs bypass fencing; remove each target with the
sole sanctioned command, then clean up branches separately. Nested repositories and submodules
retain independent lease boundaries. A clean linked worktree may acquire a
lease. The primary checkout may acquire one only while clean, on its resolved
default branch, and outside a pre-existing Git operation. The owning session
refreshes the lease after its own edits; live foreign ownership and unowned
dirty state block with managed-worktree guidance. Lease files contain hashed
session identity,
timestamps, and local checkout identity paths under shared XDG runtime state;
they never retain the raw session identifier. A random sentinel under the
checkout's Git admin directory distinguishes a removed/recreated linked
worktree at the same path. Expired leases are reclaimable only while clean;
`AGENT_RUNTIME_CHECKOUT_LEASE_TTL_SECONDS` tunes the eight-hour default. Stop
releases clean matching owner leases across the current repository and prunes
lease state for physically removed worktrees while retaining the stable
per-checkout lock inode; dirty or mismatched ownership is retained and reported.
Stop never removes a worktree, branch, commit, or dirty file.

`session-coordination-guard.py` is a separate semantic awareness layer for
managed Codex and Claude launches. `advisory` is the default when the mode is
missing or invalid. Broker-ready sessions automatically participate through
presence; recognized mutations call privacy-safe `work-context advise` and may
emit fixed informational, overlap, or degraded-availability guidance, but never
block the tool call. Audited read-only argv shapes and pipe-only pipelines whose
every stage is audited stay silent. Unknown shell effects also stay silent in
advisory mode instead of being presented as observed mutations; strict
`enforce` admission remains fail-closed for them. The shared tri-state shell
effect result is `read-only`, `mutation`, or `unknown`; redirection, command
substitution, unsafe stages, executable shadows, and shell control other than a
plain pipe never receive the read-only result. `work-context set|clear` can add
optional bounded task context without requiring session IDs, capability
arguments, revision numbers, or a pre-written JSON file. `work-context
acknowledge` suppresses only the
most recently observed overlap for a bounded incarnation-specific window;
changed peers, reasons, repositories, or availability warn again, while target
churn covered by the same overlap stays quiet and explicit advice retains the
reasons. `off` and unmanaged launches are silent.

When a managed launch explicitly selects `enforce` and provides
`AGENT_SESSION_ID`, `AGENT_SESSION_CAPABILITY_FILE`, and
`AGENT_SESSION_STATE_DIR` on the released v1.24.5 surface, recognized direct
edits, repository shell mutations, and exact provider mutations require an
authenticated active work context and atomic operation lease. Direct edits
carry every repository-relative target; simple shell effects require repository
scope; compound or otherwise opaque shell effects, explicit cross-repository
destinations, commands outside a
governed repository, wrapped provider clients, and unresolved provider targets
fail closed. Provider `--repo`/`-R` overrides bind the effective provider
reference rather than the hook checkout. `forge-cli pr create` and
`forge-cli pr deliver --no-merge` name their pull request by head branch, so
they resolve to one `pull-request-head` target (repository from `--repo` or the
checkout origin, head from `--head` or the current branch) that only a Main
Agent worker's private head grant covers; another branch or repository is
denied as uncovered. A repeated option, a `--host` or `--provider` override
or non-origin `--remote` (the target carries no forge host), a detached
checkout, or an invalid branch name stays unresolved. The
guard emits this additive `pull_requests` field only when the admitting
`agent-session` is at or above the first release that accepts it; the released
v1.29.0 surface rejects the unknown field, so it keeps the unresolved result.
A delivery that would merge, every numbered `pr <action> <N>` (which cannot be
bound to a head without a provider lookup and keeps its `pr` provider
reference, never held by a worker claim), `gh pr create`, and `issue create`
keep their released behavior, leaving merges and new issues with the Main
Agent. Nested `sh`/`bash`/`zsh` command
strings are unwrapped before destination checks, and Git forms that may invoke
configured fsmonitor, pager, external-diff, or filter programs do not bypass
admission. A definite peer conflict and
uncovered or uncertain own scope block, while potential/unknown/no-known-
conflict classifications remain bounded advisories. PostTool success/failure
is durably recorded before runtime probes and completes the exact token-bound
lease. Admission intent, replay key, token, targets, and completion proof remain
in a mode-0600 hashed session namespace across timeouts for exact duplicate/Stop
replay rather than being guessed or released. `work-context admit` commits a
lease only in its final save, so a well-formed refusal (for example a parallel
sibling refused while another call holds the session's single operation slot)
retires its intent; a lost process, timeout, or unparseable reply stays
pending. Before admitting a new mutation, the guard recovers up to four other
calls' records of the current incarnation within a 1.5-second slice and
without waiting on their locks: with
no nonterminal broker operation it retires them; otherwise it replays a lost
admission by its exact idempotency key when the CLI lacks the broker proof
surface (a replay retires only on refusals raised after admit's idempotency
lookup), completes a recorded outcome, or asks
`work-context reconcile` to finalize a lease whose PostToolUse never arrived.
That command proves the call inactive from controller-owned turn and
descendant evidence, so a sibling still running in the same turn is kept; an
outcome that was never observed is reported as `fail`. A PostToolUse whose
admission reply was lost replays it and completes the lease with the observed
result, and a background shell call completes when the provider reports its
launch. Same-call Pre/Post/Stop activity is serialized by a stable local lock.
`agent-hook` evaluates every ordinary rule first and invokes the locked `agent-session.coordination.v1` capability
only after an aggregate allow. A prerequisite denial remains blocked; no
orchestration bootstrap may supersede owner-liveness admission. The guard applies one
50-second global subprocess budget inside the setup-owned dispatcher timeout.
For Stop, the guard emits
`runtime-kit.session-coordination-result.v1` with a `not-run`, `clean`,
`pending`, or `unavailable` status. This typed transaction result is separate
from provider presentation: `agent-hook` may prescribe reconciliation only for
`pending`, while legacy `systemMessage` or generic decision output proves no
broker state. A typed `pending` result also carries the legacy provider block
fields during the nils-cli rollout so the released consumer remains fail-closed.
In advisory mode,
older/missing coordination surfaces remain usable with bounded degraded
guidance; in enforce mode they retain accurate no-enforcement guidance. Hook
output never includes
raw session/capability/incarnation/checkout values, peer summaries, mailbox
bodies, or private registry paths. The physical checkout lease above shares the
same explicit enforce-mode boundary, and Hermes still has no runtime-kit hook
runner.

The guard accepts `--capabilities --format json` as a side-effect-free
self-probe. Its capability map contains no retired orchestration admission
contracts; ordinary intent and coordination enforcement still applies.

Executable runtime rules use independent child deadlines and an explicit
`timeout_posture`. A timeout no longer erases completed outcomes or skips later
mandatory rules. Allowed `warn` or `effect_gated` timeouts create mode-0600,
redacted incidents under the XDG state `agent-hook/degraded` tree; terminal
PostTool success/failure correlates them without retaining raw commands,
paths, prompts, or provider identifiers. A bounded summary keyed by policy,
rule, error, effect, product, and platform aggregates recurrence and the latest
completion. Completed blocks and closed/unknown effect outcomes remain
authoritative.

Dirty-checkout adoption is an opt-in advisory layered over the enforce-mode
checkout gate. With `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION` set to `1` and
coordination mode set to `enforce`, a dirty
`UserPromptSubmit` may use released `git-cli worktree dirty-snapshot` to issue a
mode-0600, one-time, five-minute bearer challenge bound to the exact repository,
checkout instance, session digest, authorization-turn digest, HEAD/branch state,
and content snapshot. The private context keeps Q&A read-only and asks the agent
to obtain explicit takeover authorization or use `git-cli worktree add`; it does
not parse natural-language authorization or adopt automatically. Snapshot failure,
unsupported state, malformed output, an active Git operation, or existing lease
makes the advisory silent while later file/index mutation continues to fail
closed.

After exact authorization, the PreToolUse gate admits the transition only through
the resolved managed `git-cli` executable, or through this hook's own
`checkout-lease-guard.py adopt-dirty` launcher, and only when the private
challenge or adopted receipt belongs to the current agent session. A released
git-cli that reads the challenge only through `--challenge-fd`
(sympoies/nils-cli#1761) gets the launcher command. The launcher reads the
one-time challenge from stdin, requires it to match the issued reason-file
digest, and parents git-cli through a private Unix socket, so the challenge
never reaches argv. An older git-cli gets the legacy argv command. Released `git-cli worktree
adopt-dirty` then rechecks and consumes the challenge under the lease lock, and
publishes one privacy-safe receipt and an adopted lease-v2 record in the same
transaction. The strict embedded lease-v2 adoption block is the guard's
authoritative provenance input; it preserves receipt ID/schema, snapshot ID,
authorization-turn and reason digests, adoption time, and challenge issue time
across same-session refresh. `git-cli worktree revoke-dirty` removes only
matching receipt-bound ownership and never changes checkout content. Challenge
records, adoption-provenance fields, and provider-visible evidence exclude raw
prompts, bearer values, reason text, filenames, paths, diffs, and file contents,
and require this one-time value to remain private.

A separate dirty-checkout exception admits only one recognized ref-only operation
through the resolved `git` executable: selected branch delete/move/copy forms, or
tag deletion and lightweight/forced tag creation with explicit `--no-sign`. It
mints no lease, requires a valid session and safe checkout state, and remains
blocked by live foreign ownership, stale/unowned lease state, Git operations,
an executable `reference-transaction` hook, or an off-default primary checkout.
Redirects, dynamic arguments, command-local Git/executable retargeting, compound
mutations, and every co-resident working-tree/index write are rejected. File and
index protection remains unconditional for staged, unstaged, and untracked-only
dirt. Codex and Claude register the shared guard on `UserPromptSubmit`; Hermes
has no runtime-kit hook runner and does not support this enforcement.

`block-unsafe-default-delivery.py` owns the shell-side delivery-mode boundary.
It admits a non-governed executable when shell expansion changes only its path
prefix (for example `$HOME/.local/bin/tool` or `~/.local/bin/tool`) while
retaining the literal basename; every suffix component must be literal, so a
wholly dynamic executable, shell glob/brace/extglob syntax, or an expanded path
ending in `git` or `semantic-commit` remains fail-closed. Refusals include the
matched rule, extracted operation, command-context provenance, and, when one
word could not be classified, that word (`word=`), so an unverified target is
distinguishable from a proven default-branch write and the word to spell
literally is named.
The same opaque classification applies when glob, brace, extglob, tilde, zsh
`=command`, or zsh glob-qualifier syntax appears directly in command position,
even without a variable prefix. The zsh extended-glob repetition, exclusion,
and negation operators (`#`, `~`, and `^`) are opaque there as well. A lone `[`,
the `[[` reserved word, and a zsh `$+name[key]` presence test with a literal key
are literal test syntax that cannot name `git` or `semantic-commit`, so they stay
classifiable. A `[`/`[[` test never executes its operands, so they are not
scanned for hidden commands; a substitution among them is still classified.
`block-direct-git-commit.py` shares that literal-test helper and does not scan
test operands for a Git subcommand, because the test never executes them.
Both Git guards classify every command substitution the shell would run:
`$(...)` unquoted or inside double quotes, and backticks quoted or not,
including in test operands and assignments. The shared tokenizer parses each
body as its own simple command ahead of the command it expands and leaves a
dynamic placeholder word in its place, so several substitutions in one command
stay arguments instead of leaving a stray `$` in command position.
A `)` inside `${...}` stays part of the expansion, as does a `|`, `;`, or `&`
(`${m%|*}` is one word), and `$((cmd) )` is read as a substitution as bash
reads it; an arithmetic `$(( ... ))` is one word whose substitutions are still
classified. Single-quoted text, shell comments, escaped markers, and
quoted-delimiter here-doc bodies stay literal; an unquoted-delimiter here-doc
body expands every substitution (it has no quotes or comments, so an
apostrophe there stays literal), and inside a substitution its lines are
classified like any other script text. When that body feeds `cat`,
`python`/`python3`, or `jq` by bare name or from `/bin` or `/usr/bin`, no pipe or process substitution reads its output
on, the body has no line continuation, and nothing else in the command runs a
shell (a shell name anywhere, or `.`/`source`/`eval`/`exec` in command
position), redefines command resolution (an alias, function, hash, or `PATH`
change), or redirects into a file (anything but `/dev/null` or a numeric
`>&N` dup), only its substitutions are classified; the rest is data. A refusal caused by here-doc
text suggests quoting the delimiter (`<<'EOF'`). Both Git
guards parse strictly: shell comments are dropped before tokenizing (only a
`#` after an unescaped blank, newline, `;`, or `&`, outside `[[ ]]` and any
open parenthesized group, counts as a comment), and a
command the tokenizer still cannot parse (for example an unterminated quote)
is refused as unresolved instead of yielding no commands. A substitution body runs in a
subshell, so default-delivery applies the shell state it changes (aliases,
PATH, `cd`, executable resolution) only within that body: a governed
`semantic-commit commit --message "$(cat <<'EOF' ... EOF)"` keeps the
classification it has without the substitution. The commit guard's
program-lookup scan stays conservative and still counts PATH changes inside
substitution bodies.
After alias, hash, command-table, PATH, sourced-function, `enable`, or zsh
`disable` state changes, later bare command words are opaque. This taint is monotonic across the conservative
flattened shell scan: nested removals never make an outer executable trusted.
Redirections are ignored when judging such a command, so a query such as
`alias name 2>/dev/null` stays query-only. Only a word in assignment position
assigns `PATH` or `path`: a leading assignment (also after `!`, `{`, `then`,
`do`, `time`, or zsh `nocorrect`) or a declaration builtin's operand, never an
argument such as a `grep -o 'path=[^ ]*'` pattern. `$${` is the `$$` PID
expansion followed by a literal `{`, so it is not read as `${`.
It resolves the selected remote's cached local default branch and blocks raw `git push`
forms that target it, including force, force-with-lease, deletion, wildcard,
matching-branch (`:` / `+:`), and implicit current-default pushes. It also
blocks mutating
`semantic-commit commit`, `fixup`, and `squash` on the default branch of the
repository that invocation actually commits in. Ambiguous
pushes without an explicit refspec fail closed because Git configuration can
retarget them. PreToolUse performs no live `ls-remote` or provider probe;
implicit, all/mirror, delete, matching, wildcard, and missing-cache cases fail
closed, while live remote truth remains owned by the delivery CLI. It leaves explicit feature-branch pushes,
`git push --dry-run`, semantic-commit help/dry-run, and the governed `forge-cli
repo push-default` invocation available. A semantic-commit `--help`,
`--dry-run`, or `--validate-only` counts only when every word before it is a
literal, known option or value: a dynamic word, an unknown option, or a
redirection-like word in a value slot could swallow it in semantic-commit's
own parser, so the invocation is classified as authoring. A zsh glob
qualifier or alternation group (`word(N)`, `(a|b)`) counts as dynamic. Raw
`git send-pack` and `git http-push` publish refs outside the push classifier
and fail closed toward `git-cli push`. Exact authorized `semantic-commit
default-branch` preview and mutation forms are admitted only through the active
trusted managed CLI with a full expected HEAD, explicit absolute repository,
primary checkout, authoritative
remote-free or aligned cached-default identity, and correct receipt behavior:
preview uses `--dry-run` without a receipt, while mutation requires a new
outside-repository receipt. The removed `local-default` spelling and ordinary
default-branch commit forms remain blocked. A `semantic-commit` target resolves
from explicit `--repo`, so a cross-repository invocation is classified against
the repository it mutates rather than the tool workdir. A bare authoring
invocation after any earlier shell command fails closed as
`[default-delivery: unverified]` (`rule=executable-resolution`) because PATH,
hashes, aliases, functions, or shell command tables may have changed; that
refusal says the executable identity is unproven, not that the target is the
default branch, and the one-shot waiver never admits it. Compound routes,
including `git add ... && semantic-commit commit`, must be split into a
separate tool call with the target checkout as its top-level workdir. Help,
`--dry-run`, and `--validate-only` forms author nothing and stay available
after earlier commands. Relative or expanded destinations,
nested shells, and command-local `GIT_*`/`HOME` overrides also fail closed, and
raw Git still fails closed after every shell-context change or missing
per-call workdir attestation. An absolute `git -C /path/to/repository ...`
target remains independently classifiable. A
blocked verdict names the resolved repository, how it resolved, and the first
failing precondition. When a `semantic-commit` target stays unresolvable, one
command may state a reason inline as
`AGENT_RUNTIME_DEFAULT_DELIVERY_WAIVER=<reason>`; that is handler admission, not
a rule override, and it never reaches a proven default-branch target or a raw
Git path. Hook admission is intentionally independent of cached
upstream ancestry: `semantic-commit default-branch` owns the full transaction
proof and rejects already-ahead, behind, diverged, or unknown relations. The hook is a
guardrail rather than a shell sandbox; provider rules and the forge-cli
expected-base, one-signed-commit, verified-fast-forward, exact-old-object
compare-and-swap, and post-push read-back contract are authoritative. The
internal exact lease does not make raw or caller-controlled
`--force-with-lease` an allowed route. Hermes has no runtime-kit hook runner.

Install surfaces:

- Codex: `targets/codex/link-map.yaml` installs shared scripts under
  `$CODEX_HOME/hooks/`; its legacy managed hook block is intentionally empty.
- Claude: `targets/claude/link-map.yaml` installs shared scripts under
  `$HOME/.claude/hooks/`; its legacy settings fragment is intentionally
  empty.
- `scripts/sync-runtime-surfaces.sh` installs the shared digest-pinned policy
  and delegates exact Codex/Claude provider ingress to `agent-hook setup`.

## Managed cleanup rollout

Use the CLI-owned `--safe` execution fence for cleanup in advisory sessions.
Changing coordination mode is a broader workflow migration, not a cleanup
prerequisite. The hook-side support and the companion CLI implementation are
separate deliveries: see [runtime-kit PR #239](https://github.com/sympoies/agent-runtime-kit/pull/239)
and [the CLI owner](https://github.com/sympoies/nils-cli/issues/2236).
An installed hook accepting the command does not prove that the installed CLI
implements it. Do not infer availability from the hook, a release number alone,
or the read-only `diagnose-removal` result.

Before backlog cleanup:

1. The release owner must deliver and release the companion CLI fence. Verify
   that the installed `git-cli worktree remove --help` advertises `--safe` on
   every cleanup host; an older binary must reject the flag. Keep it present.
   Do not substitute an unreleased binary or change pins to an unpublished
   version as a rollout shortcut.
2. Through the normal runtime sync owner, dry-run then install the hook and
   refreshed cleanup skills from the merged kit source. Confirm Codex and
   Claude provider ingress through `agent-hook setup`. All participating local
   sessions and the cleanup command must resolve the same session registry and
   checkout lease state roots; preserve `AGENT_SESSION_STATE_DIR` and the
   configured checkout lease state override/fallback. An empty alternate state
   directory is not evidence that the target is idle.
3. Prove disposable fixture acceptance on each supported operating system:
   idle, clean, merged managed target removal succeeds; a live cwd/open file,
   live managed session binding, active lease (including the requester), dirty
   target, or undelivered HEAD retains the target. The cleanup account needs
   `lsof` and complete process visibility, remote Git access, and provider
   access for exact-head squash/rebase merge proof. Missing tools, warnings,
   timeouts, or incomplete visibility retain the target.
4. Inventory and classify the backlog through `worktree-triage`. Finish parent
   delivery/rollback duties and have original owners release their bindings
   through their owning lifecycle before cleanup. A merged branch or expired
   retention period alone cannot establish release. Retain dirty or ambiguous
   targets; this path does not authorize disposable-dirty removal or expiry-only
   deletion.
5. From the primary checkout, submit one sole shell command per eligible target:
   `git-cli worktree remove <path-or-slug> --safe --format json`. Retain each JSON
   result privately with the captured target/head and delivery evidence, then
   verify inventory disappearance. A refusal is a retained target requiring
   resolution of its stated proof failure. Do not retry without `--safe`, use
   batch `--remove-worktrees`, force deletion, or override state roots. Branch
   deletion is a separate lifecycle step after exact-tip delivery proof.

The [terminal cleanup policy](../policies/git-delivery.md#terminal-local-cleanup)
owns cleanup eligibility and receipts. A hook diagnostic always has
`execution_fenced=false` and `cleanup_authorized=false`; it is not an execution
receipt. A successful CLI result proves its completed lifecycle call, while
parent duties still require their own evidence. Roll back an unavailable or
failing rollout by retaining the backlog and correcting the failed prerequisite.

## What a fleet-wide enforce switch requires

Select `agent-session start|run --coordination-mode enforce` at the managed
launch boundary; do not merely export the mode around a cleanup command.
The launch must supply its own authenticated `AGENT_SESSION_ID`, private regular
mode-0600 `AGENT_SESSION_CAPABILITY_FILE`, and `AGENT_SESSION_STATE_DIR`, with a
ready broker and a released trusted CLI supporting `claim`, `show`, `check`,
`renew`, `release`, `admit`, `complete`, and `reconcile`. Install the matching PreTool, PostTool success/
failure, and Stop ingress for Codex and Claude. Hermes has no kit hook runner
and cannot provide the same enforcement guarantee. Missing metadata or an
unavailable coordination surface may emit no-enforcement guidance rather than
block; the environment variable alone is never proof of enforced participation.

Each worker needs an authenticated active raw claim covering its repository,
exact checkout, edit paths, and provider targets before mutation. Optional
advisory context is not a substitute for verifying that claim. Claims must be
renewed and replaced through their compare-and-swap lifecycle. Head-specific PR
creation needs the worker's authorized head scope; numbered provider mutations
need the corresponding provider scope. Preserve tool-call execution identity
through PostTool completion, and retain/reconcile uncertain operation proofs
before admitting later work. See [session coordination](../policies/session-coordination.md#explicit-enforcement).

Beyond removal, enforce acquires physical writer leases for edits and recognized
shell mutations; live foreign leases, unowned dirty state, and pending Git
operations block acquisition. Clean primary-checkout acquisition requires its
resolved default branch. Semantic admission also blocks missing/expired claims,
uncovered scopes, conflicts, shell retargeting, opaque shell effects, and
unresolved provider targets. Read-only audited commands remain available, and
sole managed-worktree creation and Git abort/quit remain recovery routes.
Dirty adoption is separately opt-in; switching mode does not adopt existing
changes. Stop audits ownership and operation completion rather than deleting
worktrees.

Existing advisory workers can therefore lose mutation access after a blanket
switch. Pilot the complete claim/admission/completion flow, drain or relaunch
old sessions, and verify shared state and recovery before wider enforcement.
Neither enforce leases nor provider merge truth alone prove that an advisory
session has left a target or that parent duties are complete; use the supported
execution fence for cleanup in either mode.
