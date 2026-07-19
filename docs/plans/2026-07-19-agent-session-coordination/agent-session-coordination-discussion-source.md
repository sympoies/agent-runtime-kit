# Agent Session Coordination Implementation Handoff

## Document Control

- Status: approved for L2 planning; implementation not started
- Date: 2026-07-19
- Owner repository: `graysurf/agent-runtime-kit`
- Implementation repositories: `sympoies/nils-cli`,
  `graysurf/agent-runtime-kit`, and `serenvia/local-scripts`
- Work tier: L2, one serial cross-repository plan-tracking issue
- Decision owner: maintainer
- Open questions: none; execution-time release and live-activation approvals are
  explicit gates, not unresolved design questions

## Purpose

Give every managed agent session enough privacy-preserving coordination state to
answer three questions before it starts mutable work:

1. Which other sessions exist and are still live?
2. Is another session already working in the same semantic scope?
3. If metadata is insufficient, how can the sessions exchange a bounded message
   and an explicit reply without copying the message into an agent prompt?

The result must make metadata inspection the normal path, use a mailbox only for
necessary clarification, and reserve provider prompt injection for a fixed
content-free notification. It must integrate the mechanism owned by nils-cli,
the workflow policy owned by agent-runtime-kit, and the private operational skill
owned by local-scripts. [U1]

## Source Register

- [U1] Maintainer request in this planning session: add explicit session
  discovery, collision checks, coordination rules, and agent-to-agent messaging;
  prefer session metadata over direct prompting; integrate with agent-runtime-kit
  and retain an implementation-ready agent document.
- [U2] Maintainer approval in this planning session: proceed with the assessed
  design as a complete L2 plan and commit the documentation to Git.
- [F1] `serenvia/local-scripts:agent-runtime/.agents/skills/private-agent-session/SKILL.md`
  defines mobile handoff, session listing, prompt send, and managed-session
  operations, but not semantic work claims or mailbox behavior.
- [F2] `sympoies/nils-cli:crates/agent-session/src/cli.rs`,
  `sympoies/nils-cli:crates/agent-session/src/lib.rs`, and
  `sympoies/nils-cli:crates/agent-session/src/serve.rs` define current session
  records, serialized send behavior, list/glance surfaces, and the structured
  prompt route.
- [F3] `graysurf/agent-runtime-kit:core/hooks/shared/checkout-lease-guard.py`
  coordinates writers to one physical Git checkout; it does not claim semantic
  scope across distinct worktrees or repositories.
- [F4] `graysurf/agent-runtime-kit:AGENT_DOCS.toml`, `AGENT_HOME.md`, and
  `core/policies/intent-cards.md` define catalog-driven intent routing and are the
  durable home for a new `session-coordination` intent.
- [A1] Installed `agent-session` 1.24.2 list and help output inspected on
  2026-07-19: list records include lifecycle and location fields such as session
  ID, agent, cwd/repository, title, status, turn state, updated time, and session
  incarnation, but no declared work context, claim, or mailbox state.
- [A2] Privacy-minimized live `agent-session list` inspection on 2026-07-19
  found no known session title/repository overlap with this plan-authoring work.
- [A3] `plan-archive search` on 2026-07-19 found no prior session-coordination,
  mailbox, or input-lease plan. The one broader agent-session result did not
  cover this problem.
- [I1] A session title, cwd, repository, or raw prompt cannot reliably represent
  semantic work scope. A separate structured work-context declaration is needed.
- [I2] A physical-checkout writer lease and a semantic work claim solve
  complementary problems. The existing checkout lease must remain authoritative
  for same-checkout writes; a new coordination claim must cover cross-worktree
  and cross-repository collision risk.

## Current-State Assessment

The proposal is reasonable and addresses a real missing layer. Existing
capabilities are individually useful but do not form a coordination protocol:

- Session discovery exposes runtime and repository hints, but a caller must
  infer intent from weak metadata or inspect additional content. [F2][A1]
- The private skill can create a managed session, list it for Agent Console, and
  send a prompt, but it does not require the current agent to inspect existing
  sessions or declare its own scope first. [F1]
- Structured prompt delivery already fences a managed session by incarnation and
  lifecycle state, but that is a transport safety property, not a mailbox with
  acknowledgements, replies, expiry, or idempotency. [F2]
- The runtime-kit checkout lease prevents simultaneous writers to one physical
  checkout. Separate worktrees can still implement overlapping requirements or
  modify logically coupled interfaces without being detected. [F3][I2]
- `agent-docs` derives intents from its catalog, so a dedicated intent can be
  added without hard-coding a new English-keyword router. [F4]

The design should not turn every agent into a chat relay. Automatic access to
raw logs, glance output, prompts, or assistant messages would increase privacy
risk and create noisy recursive coordination. Metadata-first discovery plus a
small explicit mailbox is the narrower and safer contract.

## Decisions

### Ownership

1. `sympoies/nils-cli` owns the runtime mechanism: structured work context,
   atomic claims, conflict queries, mailbox persistence, CLI/JSON/API contracts,
   incarnation fencing, expiry, idempotency, and privacy.
2. `graysurf/agent-runtime-kit` owns agent behavior: a new
   `session-coordination` intent, durable policy, intent-card routing, hook cues,
   admission rules, tests, and the pinned nils-cli capability transition.
3. `serenvia/local-scripts` owns the private operational entrypoint: extend
   `private-agent-session` so a session operator can discover context, coordinate,
   and recover using the released primitives.
4. The L2 tracking issue lives in `graysurf/agent-runtime-kit` because that repo
   owns the cross-product behavior and rollout policy. Upstream nils-cli and
   downstream local-scripts work are serial children of the same tracker.

### Workflow

1. A managed session declares its work context before mutable implementation or
   delivery work.
2. The agent checks other active claims using structured metadata.
3. A definite overlap blocks admission until the owner releases, narrows, or
   explicitly coordinates the claim.
4. A potential overlap or incomplete metadata is advisory in v1. The agent may
   inspect the other public work context and send one necessary mailbox message.
5. A `clear` result is returned only when all relevant active records have enough
   metadata for the comparison. Otherwise the result is `unknown` or
   `no_known_conflict`, never a false safety claim.
6. The mailbox stores the content. Prompt transport may deliver only a fixed
   notification containing a message identifier and a command for reading it.
7. Formal multi-agent implementation still uses L3/provider-backed dispatch.
   The mailbox is ephemeral coordination, not a replacement for issues, plans,
   reviews, or durable execution state.

### Rollout

1. Ship nils-cli mechanism and deterministic tests first.
2. Release nils-cli only after a fresh explicit release authorization.
3. Consume the exact release through the runtime-kit pin-bump workflow.
4. Initially hard-block only definite conflicts. Keep `potential_conflict`,
   `unknown`, and `no_known_conflict` as visible advisory states while telemetry
   and acceptance establish confidence.
5. Update the private skill after the released mechanism and runtime policy are
   available.
6. Synchronizing installed agent homes or sending live prompts to existing
   sessions remains a separate, fresh activation approval.

## Scope

### In Scope

- A structured `work_context` independent of title, cwd, prompt, or transcript.
- Atomic `claim`, advisory `check`, `renew`, `release`, `admit`,
  `complete`, and `reconcile` operations plus a persistent held-launch broker.
- Conflict classification across sessions, worktrees, repositories, issues,
  plans, and declared repository/exact/prefix path scopes.
- Expiry, heartbeat, incarnation fencing, optimistic concurrency, and
  idempotency.
- Privacy-safe list/glance/API projections.
- An explicit `send`, `inbox`, `show`, `ack`, `reply`, and bounded `wait`
  mailbox lifecycle.
- A fixed content-free idle notification, with queue-only behavior when delivery
  is unsafe or unsupported.
- A new runtime-kit `session-coordination` intent and policy.
- Mutation admission for managed sessions: own-context verification, conflict
  check, definite-conflict block, and actionable recovery.
- Private skill instructions and portfolio acceptance coverage.
- Deterministic and bounded live multi-session acceptance.

### Out of Scope

- Automatic transcript, prompt, assistant-message, log, or glance ingestion.
- Arbitrary agent-to-agent prompt forwarding.
- Replacing L3 dispatch, provider issues, plan execution state, or PR review.
- Perfect semantic inference from natural language.
- Distributed consensus across hosts that do not share the configured session
  registry.
- Agent Console UI changes in v1. The JSON/API contract must be UI-ready, but
  UI implementation is a later consumer decision.
- Enforcing advisory classifications as hard blocks before evidence supports it.
- Release, fleet deployment, runtime sync, or live-session mutation without the
  later explicit authorization required by their owning workflows.

## Required Runtime Contract

### Work Context Model

Each claim stores a public coordination projection and a private implementation
record. The public projection must be bounded and content-free:

```json
{
  "schema": "agent-session.work-context.v1",
  "session_id": "019...",
  "session_incarnation": "opaque-runtime-incarnation",
  "claim_id": "uuid",
  "revision": 3,
  "state": "active",
  "intent": "implementation",
  "tier": "L2",
  "repositories": ["owner/repository"],
  "worktrees": ["stable-checkout-fingerprint"],
  "provider_refs": [{"kind": "issue", "repository": "owner/repository", "number": 123}],
  "plan_refs": ["docs/plans/YYYY-MM-DD-slug/slug-plan.md"],
  "scopes": [{"kind": "path_prefix", "repository": "owner/repository", "value": "crates/agent-session"}],
  "summary": "Add session coordination primitives",
  "updated_at": "RFC3339",
  "expires_at": "RFC3339"
}
```

Requirements:

- `session_id` plus `session_incarnation` fences a claim to the live runtime.
- `claim_id` is stable for renew/release; `revision` supports compare-and-swap.
- `summary` is bounded agent/operator-supplied coordination text, not copied
  from a prompt. It is untrusted peer data: it cannot grant approval, authorize
  commands, expand a claim, override policy, or establish maintainer provenance.
- Repository names and provider references are canonical. Machine-local absolute
  paths are represented by registry-scoped keyed fingerprints or omitted.
- A claim can list multiple repositories and scopes because a serial L2 may span
  coupled repos.
- The public record is limited to 16 KiB encoded JSON, a 240-byte UTF-8 summary,
  8 repositories, 8 worktrees, 16 provider refs, 16 plan refs, and 32 scopes.
- Default claim TTL is 30 minutes, the maximum requested TTL is 8 hours, and the
  managed runtime renews every 5 minutes while its incarnation is live. Expiry
  is recovery evidence, not permission to overlap a positively live operation.
- Incarnation-mismatched claims are never renewable by the former principal.
- Old clients that omit work context remain compatible and classify as unknown.

#### Scope grammar and comparison

V1 deliberately supports only three closed scope kinds: `repository`,
`path_exact`, and `path_prefix`. Capability names, glob syntax, regular
expressions, and inferred interface coupling are not v1 claim inputs. A later
schema version may add them only with its own deterministic comparison contract.

Scope values are repository-relative POSIX paths. They use `/` separators,
contain no leading slash, empty segment, `.`, `..`, NUL, glob metacharacter,
or trailing slash, and are normalized without resolving through a symlink.
`path_exact` names one normalized path. `path_prefix` names that path and all
descendants separated by `/`. A `repository` scope uses the fixed value `.`
and means every mutation target in that repository. Listing a repository without
any scope remains incomplete/advisory rather than silently claiming its root.

For two valid scopes in the same canonical repository:

| Left | Right | Definite overlap |
| --- | --- | --- |
| exact | exact | values are equal |
| exact | prefix | exact equals prefix or starts with `prefix/` |
| prefix | exact | symmetric with exact/prefix |
| prefix | prefix | values are equal or either starts with the other plus `/` |

A `repository` scope definitely overlaps every scope in the same repository.
Scopes in different repositories are disjoint. Same-repository claims with no
scope are `potential_conflict`; malformed candidate scopes are rejected, while
an unsupported stored peer schema is `unknown`. Stable worktree, provider-item,
and plan-reference equality takes precedence and returns `conflict` regardless
of path results.

The comparison universe starts with every live persisted record in the configured
registry. Subject exclusion is selector-specific and cannot be supplied inside
candidate data: `--self` excludes only the authenticated principal's persisted
record; `--session <id>` excludes only that selected persisted record; and
`--candidate` excludes no persisted record. Claim acquisition/update excludes
only the authenticated session's prior matching claim revision. A crafted
candidate therefore cannot suppress a real peer, and an operator-selected record
does not conflict with itself. Results include content-safe `subject_kind` and
selected claim/session reference metadata.

Any remaining record becomes provably irrelevant only after a valid context
shows a disjoint canonical repository set and no equal worktree, provider, or
plan reference. A missing/unsupported context therefore prevents `clear`; it
yields `unknown` (or `no_known_conflict` only in the explicitly permissive
projection). This closed rule makes `clear` a complete-registry statement
rather than a caller-selected peer subset.

#### Checkout fingerprint

The session broker owns a 256-bit registry key in a 0600 file below the private
0700 registry root. It derives a public fingerprint with HMAC-SHA-256 over a
version tag plus the canonical physical worktree identity; the canonical input
never leaves the broker. Fingerprints compare only inside the same registry and
key epoch. Cross-registry or unknown-epoch values are incomparable and classify
as `unknown`, never `clear`.

Key rotation runs under the registry lock. It either rewrites every live
fingerprint atomically into the new epoch or marks affected records
`migration_required` until their owners renew them; mixed epochs never compare
as disjoint. Public output includes only the epoch identifier and keyed digest,
not the key or canonical input.

#### Session authentication and trust boundary

Session ID and incarnation are public fencing identifiers, not credentials. At
managed-session creation the broker generates a separate 256-bit random
capability, binds it to exactly one session ID/incarnation, stores it only in a
0600 session-private credential file, and passes only the file path through the
trusted `AGENT_SESSION_AUTH_FILE` launch projection. Replacement, terminal
close, or operator revocation invalidates the capability before a new
incarnation becomes active. Capabilities never appear in arguments, environment
value dumps, list/glance/context output, logs, errors, provider evidence, or
notification text.

CLI operations derive the current principal from that credential file; a
caller-supplied `--session`, route ID, or incarnation may select a record but
cannot establish authority. HTTP session operations use the same capability in
a dedicated authorization header over the local authenticated transport. The
existing server-wide bearer authenticates a server client/operator, not a
session owner, and cannot read message bodies or impersonate a session.

Authorization is fixed as follows:

| Operation | Required authority |
| --- | --- |
| list, public context show/check | local registry reader or server operator; privacy-safe fields only |
| claim, renew, release, admit, complete, owner reconcile | capability bound to that session incarnation |
| message send | authenticated sender capability; target is explicit |
| inbox, message show, ack, reply, wait | capability bound to the recipient incarnation |
| broker status/adopt/reconcile, revoke/expire | explicit operator authority; never grants message-body read |

This protects cooperative agents from cross-session mistakes and confused-deputy
use. It is not an isolation boundary against a malicious process already running
as the same Unix account, which can inspect that account's files; hostile
same-UID isolation requires a future OS/process sandbox. Negative tests still
prove that a peer holding only public IDs, incarnations, revisions, and message
IDs cannot act as another session without its capability.

### Claim Operations

Required CLI shape, with stable JSON envelopes and text equivalents:

```text
agent-session work-context claim --file <json> --idempotency-key <uuid> [--if-revision <n>]
agent-session work-context show --session <id>
agent-session work-context check (--self | --session <id> | --candidate <json>) [--permissive]
agent-session work-context renew --claim <id> --if-revision <n> --idempotency-key <uuid>
agent-session work-context release --claim <id> --if-revision <n> --idempotency-key <uuid>
agent-session work-context admit --claim <id> --operation <uuid> --execution-token <opaque> --targets-file <json> --if-revision <n> --idempotency-key <uuid>
agent-session work-context complete --operation <uuid> --execution-token <opaque> --if-revision <n> --idempotency-key <uuid>
agent-session work-context reconcile --operation <uuid> --if-revision <n> --idempotency-key <uuid>
```

- Authenticated commands derive session ID and incarnation from the current
  capability. They do not accept an authority-changing `--from` or
  `--session`; the `show --session` selector is public read-only.
- `check` requires exactly one selector. `--self` resolves the authenticated
  current context, `--session` selects an existing public context for a registry
  reader/operator, and `--candidate` compares supplied JSON without persisting
  it. Missing or multiple selectors return `invalid_check_selector` before the
  registry lock or comparison.
- `check` is an advisory point-in-time snapshot and reserves nothing. Two
  callers may both observe `clear` before they claim. No caller may begin a
  mutation based on `check` alone.
- `claim` performs conflict evaluation and acquisition in one registry
  transaction/lock. Only its `admitted` result authoritatively reserves scope,
  so two contenders cannot both be admitted for the same definite scope.
- Every mutation requires an explicit idempotency key. Expected revision is
  required after initial claim creation; current incarnation is derived from the
  authenticated principal. Retry returns the original outcome, not a duplicate.
- Claim acquisition returns the complete conflict evaluation used for admission.
- Release is idempotent and never releases another incarnation's claim.
- Crash recovery converts expired active claims to stale records without
  deleting audit-minimum metadata needed to explain a prior block.

An idempotency receipt is keyed by authenticated principal, session
incarnation, operation name, and idempotency key. It stores a SHA-256 digest of
the canonical request, the content-safe result envelope, and expiry for 24
hours. Same-key/same-digest retry returns the original result. Same-key with a
different digest returns content-free `idempotency_key_reused` and never reveals
the prior target, body, or result. Cross-session, cross-incarnation, and
cross-operation keys do not collide. After receipt expiry the key is new; v1
promises replay stability only inside the 24-hour window.

#### Mutation admission and operation lease

Before a tool mutation, the guard derives every target it can prove and calls
`admit`. Repository-relative edit targets must be a subset of the active
`path_exact`, `path_prefix`, or explicit `repository` scope after physical
checkout and symlink-boundary validation. Provider mutations must match a
declared provider ref. Multi-target operations must be covered in full. An
opaque shell/external mutation that cannot expose a bounded target set requires
an explicit `repository` scope for each affected repository; otherwise managed
v1 admission fails closed with `uncovered_mutation_scope`. Unsupported surfaces
may be advisory only when the workflow itself is declared non-mutating; they
must never claim enforcement for an opaque mutation.

`admit` atomically re-evaluates peer conflicts, verifies target coverage, and
creates an operation lease before the tool runs. Each lease binds an
`execution_token` derived from the product turn generation and tool-call ID,
plus an observed descendant process identity when the tool launches one. A
persistent per-session coordination broker sidecar—not the model turn, hook
subprocess, or optional HTTP server—owns capability projection and heartbeat.

The broker renews the base claim while the exact session is live. It renews an
operation only while the matching product activity token remains busy or its
bound descendant process remains live; general pane liveness alone never renews
a completed operation. Post-tool first persists an idempotent completion event
to the broker queue, then calls `complete`; response loss is retried from that
queue. If PostTool is absent, an idle/superseding activity token plus no matching
descendant on two observations at least 5 seconds apart moves the operation to
`reconcile_pending` and allows automatic or authenticated `reconcile`.
Uncertain proof remains fail closed. An explicit operator recovery may attest
inactive only after the same no-descendant checks; it records the authority and
reason but no tool/body content. Normal terminal close reconciles/abandons all
operations, releases the claim, and revokes the principal.

Managed launch uses one shared library path for CLI `start`, one-shot `run`,
`resume`, and the HTTP session-create handler:

| Entrypoint | Broker contract |
| --- | --- |
| `start` | create a new incarnation and broker, then release the interactive agent |
| `run` | same launch; broker remains until one-shot output/target exit cleanup |
| HTTP session create | delegates the same held-runtime launch transaction |
| `resume <id>` | create a replacement incarnation and fresh broker; never adopt the missing old runtime |
| `delete <id>` | request broker shutdown, kill target if needed, then revoke credential/release state under the registry lock |

The launch transaction is fixed: reserve a `starting` record and credential
path; create a held tmux pane/gate without executing the agent; capture and
persist pane ID, PID/start time, and process-group identity; generate the
capability file; start exactly one companion broker bound to that identity; wait
at most 2 seconds for its readiness record; then signal the held gate to exec the
agent with only `AGENT_SESSION_AUTH_FILE`. A failure after any boundary stops
the broker/pane, revokes/removes the credential, and marks/removes the partial
record under the lock before returning `coordination_broker_unavailable`.

Broker recovery has concrete operator surfaces:

```text
agent-session broker status <id>
agent-session broker adopt <id> --if-incarnation <opaque>
agent-session broker reconcile <id> --operation <uuid> --if-revision <n> --attest-inactive
```

`adopt` is only for a still-live coordination-aware incarnation whose broker
was lost. It acquires the broker singleton lock and validates the private
capability file, registry record, and unchanged pane/PID/start-time/process-group
identity before resuming heartbeat; failure leaves operations blocked.
Older sessions without a capability/broker record cannot be adopted and report
coordination unavailable. The optional HTTP server proxies the same library but
is neither heartbeat owner nor prerequisite.

If renewal fails or its state is uncertain, the owner is degraded and new
operations fail closed. A conflicting claimant remains blocked while either the
operation lease is unexpired or the registry can positively prove the original
session/process group is alive. Recovery admits a replacement only after the
lease is expired, the original incarnation/process group is non-live, and a
10-minute recovery grace has elapsed. Replacement fencing prevents the old
principal from renewing or completing the new incarnation's records. Fake-clock
and process-liveness tests cover long operations, approval waits, renewal
failure/recovery, crash, replacement, and clean release.

### Conflict Classification

The comparison engine returns one of:

- `conflict`: a deterministic overlap exists, such as the same physical checkout
  fingerprint, the same provider work item, the same plan reference, or
  intersecting repository/exact/prefix scopes in the same repository.
- `potential_conflict`: repositories overlap but one or both claims omit an
  explicit scope, so v1 cannot prove either definite overlap or separation.
- `unknown`: a relevant live session lacks valid work context, uses an unsupported
  schema, or the registry cannot prove a complete view.
- `no_known_conflict`: no overlap is known, but at least one comparison is
  incomplete and the caller explicitly requested a permissive projection.
- `clear`: all relevant active claims were comparable and no overlap exists.

Every result includes machine-readable reasons and only privacy-safe peer
projections. Ordering is stable. A definite conflict takes precedence over
potential or unknown results. V1 admission hard-blocks `conflict`; target
coverage and operation-lease failures are separate own-session fail-closed
admission errors, not conflict classifications.

### Mailbox Model

Required CLI shape:

```text
agent-session message send --to <id> --body-file <path> --idempotency-key <uuid> [--reply-to <id>]
agent-session message inbox [--state unread] [--cursor <opaque>] [--limit <n>]
agent-session message show --message <id>
agent-session message ack --message <id> --if-revision <n> --idempotency-key <uuid>
agent-session message reply --message <id> --if-revision <n> --body-file <path> --idempotency-key <uuid>
agent-session message wait --message <id> --after-revision <n> --timeout <duration>
```

Message records require sender/recipient session IDs and incarnations, message
ID, idempotency key, created/expiry timestamps, state/revision, optional
`reply_to`, and a bounded UTF-8 body. Sender identity is always derived from the
authenticated principal; recipient operations are implicitly bound to the
current recipient principal. Message bodies and summaries are untrusted
peer-supplied data. Structured results place them only in a dedicated `body`
field with authenticated sender provenance; they cannot grant approval,
authorize commands, expand work scope, request secrets, or override governing
instructions.

V1 resource limits are fixed:

- body size: 16 KiB UTF-8; default expiry: 24 hours; maximum expiry: 7 days;
  acknowledged records are retained for 24 hours;
- at most 256 unexpired messages and 4 MiB retained mailbox bytes per session,
  and 64 MiB retained bytes per registry;
- send rate: 30 messages per authenticated sender/recipient pair per minute with
  a burst of 10; fixed notification attempts: at most one per target per minute;
- inbox page default 50 and maximum 100; opaque cursors bind query and principal;
- wait maximum 60 seconds and reply depth maximum 16.

At quota, rate, or cursor failure the operation returns a content-free typed
error and does not evict an unread/unexpired message. Cleanup runs under the
registry lock in stable `expires_at`, `created_at`, message-ID order: remove
expired records and expired idempotency receipts, then acknowledged records past
retention. Restart repeats the same ordering. A send that still exceeds quota is
rejected; mailbox readability remains authoritative.

The implementation must:

- keep the mailbox in a private state directory with directory mode 0700 and
  files/database mode 0600;
- reject oversize, invalid UTF-8, self-recursive reply chains, expired targets,
  incarnation mismatch, and unbounded waits;
- support idempotent send/ack/reply and stable ordering;
- never include message body, reply body, prompt, or transcript content in
  `list`, `glance`, provider records, hook output, routine logs, or notifications;
- optionally attempt one fixed notification such as `Coordination message <id>
  is available; run agent-session message show --message <id>` when the target
  is idle, rate permits, and the structured prompt route can fence the current
  incarnation;
- queue without prompt delivery when the target is busy, unmanaged, replaced,
  or lacks the structured route;
- prevent notification loops: notifications do not trigger replies, forwarding,
  or further notifications without an explicit mailbox operation.

Notification is deliberately **at-most-one attempt**, not guaranteed delivery.
The mailbox transaction records `notification_attempting` before the external
prompt call. Once that state is durable, retries and crash recovery never attempt
the prompt again, including when the call result is unknown. A crash before the
call may therefore omit the optional notification; a crash after acceptance may
leave an unknown receipt, but cannot cause a retry storm. The message remains
readable through inbox/show in every case. Notification templates and message
IDs are trusted control-plane data; bodies are never interpolated.

### API Projection

The existing server adds versioned routes equivalent to the CLI:

```text
GET    /sessions/{id}/work-context/v1
POST   /sessions/{id}/work-context/claim/v1
POST   /sessions/{id}/work-context/check/v1
POST   /coordination/work-context/check/v1
POST   /sessions/{id}/work-context/renew/v1
POST   /sessions/{id}/work-context/release/v1
POST   /sessions/{id}/work-context/admit/v1
POST   /sessions/{id}/work-context/complete/v1
POST   /sessions/{id}/work-context/reconcile/v1
GET    /sessions/{id}/broker/v1
POST   /sessions/{id}/broker/adopt/v1
POST   /sessions/{id}/broker/reconcile/v1
GET    /sessions/{id}/messages/v1
POST   /sessions/{id}/messages/v1
GET    /sessions/{id}/messages/{message_id}/v1
POST   /sessions/{id}/messages/{message_id}/ack/v1
POST   /sessions/{id}/messages/{message_id}/reply/v1
GET    /sessions/{id}/messages/{message_id}/wait/v1
```

The route `{id}` must equal the session bound to the capability for an
owner/recipient operation; for send it is the explicit recipient while the
authenticated principal is the sender. CLI `check --self` and
`check --session <id>` use the session route (the former binds `id` from the
principal); `check --candidate <json>` uses the registry-level route with a
required candidate body. The route/body rejects missing or conflicting selectors
with the same `invalid_check_selector` envelope. The public contract matrix is:

| Operation | Authenticated/derived identity | Revision | Idempotency | Bound |
| --- | --- | --- | --- | --- |
| context show | registry reader/operator; existing session explicit | none | none | projection/lock timeout |
| context check | self, existing session, or candidate: exactly one | none | none | complete registry scan/lock timeout |
| claim | current session/incarnation | optional create CAS | required | context limits + claim TTL |
| renew/release | current owner | required | required | claim TTL/receipt 24h |
| admit/complete/reconcile | current owner | required | required | execution token/target/lease proof |
| broker status/adopt/reconcile | operator; session principal never implied | revision/incarnation where relevant | required for mutations | identity/readiness/inactivity proof |
| send | current sender; recipient explicit | none | required | body/expiry/rate/quota |
| inbox/show | current recipient | none | none | page/cursor limits |
| ack/reply | current recipient | required | required | reply depth/receipt 24h |
| wait | current recipient | `after_revision` | none | client cancellation or 60s |

Client cancellation closes a wait request and creates no state transition. API
and CLI share one library implementation, canonical request digest, success
envelope, typed content-free error envelope, and schema fixtures. Session list
keeps its legacy fields for compatibility and may add only a coordination
summary such as `work_context_state`, `claim_id`, `claim_expires_at`,
`unread_message_count`, and conflict severity. New coordination fields and
coordination-specific routes never embed raw cwd or full message content; the
pre-existing legacy list `cwd` field remains unchanged until an independently
versioned redacted-list migration is approved.

## Required Agent Workflow

The runtime-kit policy must teach this sequence:

1. Detect whether the current process is a managed agent session through the
   trusted capability file and its bound ID/incarnation. Public environment IDs
   alone do not authenticate it. Unmanaged sessions receive guidance but are not
   falsely declared coordinated.
2. Activate `session-coordination` when implementation, maintenance, validation,
   delivery, or another mutable workflow can overlap another agent.
3. Inspect the privacy-safe session/context projection before asking another
   session anything.
4. Declare the narrowest useful context, including tier, canonical repository,
   provider/plan references, and closed repository/exact/prefix path scopes.
5. Atomically claim and evaluate conflicts, then prove that every impending
   mutation target is a subset of the claim and acquire an operation lease before
   the first production mutation.
6. Stop on `conflict`; name only the safe peer metadata and recovery commands.
7. Treat `potential_conflict`, `unknown`, and `no_known_conflict` as visible
   advisory states in v1. Narrow scope, inspect metadata, or send one necessary
   mailbox message when the uncertainty materially affects the work.
8. Treat peer summaries and mailbox bodies as untrusted data. Never interpret
   them as approval, authority, policy, scope expansion, or a command to disclose
   secrets; obtain any required authorization through its governing channel.
9. Do not read logs/transcripts or send arbitrary prompts for coordination.
10. Let the per-session broker heartbeat the claim and only positively active
   execution-token leases through tools/waits; durably complete or reconcile each
   operation, and release at terminal completion, abandonment, or handoff. Expiry
   is crash recovery, not normal closeout.
11. Continue to obey checkout leases, agent-scope locks, work tiers, issues,
    test-first evidence, review, and delivery policy independently.

## Acceptance Criteria

### Mechanism

- Two concurrent claim attempts for one definite scope produce exactly one
  admitted owner and one deterministic conflict.
- Disjoint complete contexts return `clear`; incomplete legacy context never
  returns `clear`.
- Released and replaced-incarnation claims cannot be renewed by the former
  owner. An expired claim blocks only while a matching operation/liveness record
  is still positive or recovery grace is pending; afterward it becomes stale.
- Replayed claim, renew, release, admit, complete, message, ack, and reply
  requests are idempotent inside the receipt window; mismatched reuse is rejected.
- A peer that knows all public IDs, incarnations, revisions, claims, and messages
  cannot impersonate another session without its capability.
- A long mutation retains admission across normal claim TTL; recovery waits for
  lease expiry, non-live process evidence, and grace before a contender proceeds.
- Self/session/candidate checks exclude exactly their defined subject; a candidate
  cannot suppress a persisted peer or make a selected record self-conflict.
- Start, run, resume, and HTTP creation produce one identity-bound ready broker
  before agent exec or atomically clean every partial record/credential/process.
- Lost PostTool completion is replayed or reconciled from execution-token,
  activity, and descendant-process proof without renewing solely on pane liveness.
- Legacy list fixtures remain unchanged. New coordination fields/routes and all
  glance/API coordination summaries contain no message, prompt, transcript,
  host, username, home path, raw cwd, capability, or private-store content.
- A message can be sent, read, acknowledged, replied to, waited for within a
  bound, and expired without prompt-body injection.
- Busy/unsupported targets retain queued mail without unsafe fallback to raw
  terminal input.
- Flood/rate/restart fixtures stay inside numeric queue, byte, page, wait,
  receipt, and notification-attempt limits without dropping unread live mail.

### Workflow

- A new runtime-kit intent resolves through `agent-docs`, names the required
  policy, and can be activated independently of `project-dev`.
- Managed mutation without valid own context receives an actionable block.
- A valid but narrower claim cannot authorize uncovered edit, symlink, shell,
  multi-target, or provider mutations.
- A definite semantic conflict blocks before production mutation even across
  separate worktrees; disjoint work proceeds.
- Advisory results are visible but do not hard-block v1.
- The private skill checks session context before start/send operations and
  documents mailbox recovery and untrusted peer-data handling without exposing
  content or treating it as authorization.
- Existing unmanaged sessions and older nils-cli installations fail compatible:
  coordination becomes unavailable/unknown, not falsely clear and not a broken
  core agent workflow.

### Delivery

- Each repository has meaningful red before production changes or a complete
  documented waiver for non-testable documentation-only work.
- Nils-cli focused and full gates, runtime-kit render/golden/hook/full gates, and
  local-scripts `_tools/check.zsh` pass on exact delivery heads.
- Independent specialist review and provider checks pass with zero unresolved
  actionable threads before each merge.
- Release, exact pin bump, private-skill update, and live activation preserve the
  serial dependency order.

## Validation Strategy

- Unit/property tests for canonicalization, the closed scope truth table, keyed
  fingerprint epochs, state transitions, TTL/operation leases, CAS, authenticated
  principals, idempotency binding, quotas, and redaction.
- Integration tests with isolated registries and concurrent processes for atomic
  claim acquisition and mailbox lifecycle.
- Server contract tests proving CLI/API parity and prompt-v2 notification fences.
- Runtime-kit hook tests for managed/unmanaged, missing context, definite
  conflict, advisory state, stale claim, and unavailable CLI behavior.
- Product rendering, golden, sandbox, and runtime-smoke tests for Codex, Claude,
  and Hermes surfaces.
- Private-skill metadata/portfolio tests and repository shell validation.
- Bounded live acceptance with disposable sessions only after explicit approval;
  use synthetic text, prove no body appears in terminal notification/list/logs,
  and close every disposable session afterward.

## Risks and Mitigations

1. **False clear from weak metadata.** Reserve `clear` for complete comparable
   records; return unknown/advisory otherwise.
2. **Race between check and claim.** Make conflict evaluation and acquisition one
   atomic transaction; hooks consume the acquisition result.
3. **Stale claims block work or live mutations overlap after TTL.** Fence by
   incarnation, let the managed runtime own bounded heartbeat/operation leases,
   require non-live evidence plus grace for recovery, provide idempotent release,
   and expose content-free degraded/stale diagnostics.
4. **Sensitive content leaks through convenience surfaces.** Separate public
   projections from private records; never include mailbox bodies in list,
   glance, notification, provider evidence, or normal logs.
5. **Prompt injection becomes the de facto bus.** Permit only a fixed
   content-free notification over the structured fenced route; queue otherwise.
6. **Coordination policy breaks unmanaged/old installations.** Capability-detect
   and degrade to unavailable/unknown guidance; do not claim enforcement.
7. **The mechanism replaces governed multi-agent workflows.** State explicitly
   that L3/provider dispatch remains the owner of delegated implementation.
8. **Cross-repository rollout drifts.** Ship/review/release nils-cli first, then
   use the governed exact pin bump, then update the private consumer.
9. **A peer impersonates another session.** Bind every private action to a
   per-incarnation capability; treat public IDs and the server bearer as
   selectors/operator authority, never session authentication.
10. **Untrusted coordination text is mistaken for authority.** Delimit summary
    and body fields, retain authenticated sender provenance, and require
    independent approval for commands, scope changes, or disclosures.
11. **A buggy peer exhausts state or prompt turns.** Enforce numeric message,
    byte, rate, page, wait, receipt, and notification-attempt limits; reject
    overflow without evicting live unread mail.

## Rollback

- Before release: close or revise the nils-cli PR; no installed surface changes.
- After release but before runtime-kit pin: leave runtime-kit on its prior exact
  nils-cli version.
- After pin but before enforcement: revert the runtime-kit pin/policy PR and sync
  the prior rendered surfaces through the governed workflow.
- After private-skill update: revert its PR and resync private skills only with
  explicit activation approval.
- Mailbox/claim state is versioned and optional. A rollback must preserve or
  quarantine newer records rather than reinterpret them with an older schema.
- Never delete active records as an automatic rollback step; use release/expiry
  and retain privacy-minimum diagnostic metadata.

## Execution and Retention

- Recommended plan: docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md
- Recommended execution state: docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-execution-state.md
- Open one L2 plan-tracking issue in `graysurf/agent-runtime-kit` after this
  bundle is committed. Keep implementation evidence in the execution-state file
  and provider checkpoints, not in this source document.
- Keep all three files active while implementation is open. At terminal closeout,
  follow the runtime-kit plan archive workflow; do not archive merely because
  the plan-authoring PR merged.
- No unresolved questions are carried into execution.
