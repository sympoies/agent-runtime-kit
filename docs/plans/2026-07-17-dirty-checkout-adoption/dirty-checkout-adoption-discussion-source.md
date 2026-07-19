# Discussion Source: Governed dirty-checkout adoption

## Trigger

The maintainer wants an optional development-mode mechanism that notices an
existing dirty checkout before implementation, leaves pure question-and-answer
work visibly unaffected, and asks whether to inspect/adopt the existing changes
or preserve them and create a managed worktree. The follow-up decision is to
design the stronger case: an agent may take responsibility for an already dirty
checkout only after explicit user authorization.

## Findings

- The current adaptive checkout lease already blocks the first mutation against
  an unowned dirty checkout. It intentionally has no route for claiming those
  changes, so “handle the existing changes first” currently permits read-only
  inspection but not agent mutation.
- The existing unconditional `PreToolUse` guard is the correct deterministic
  backstop. Making it optional, or adding a raw environment-variable bypass,
  would weaken the one-writer contract without proving user approval or binding
  approval to the state the user saw.
- `UserPromptSubmit` can inspect repository state and inject private agent
  context, but it must not classify natural language or force a visible prompt
  during read-only discussion. The agent remains responsible for deciding when
  implementation is beginning and for asking the user.
- The lease guard already owns physical-checkout identity, hashed hook session
  identity, locking, expiry, and Stop behavior. Adoption must extend that model
  rather than create a parallel ownership mechanism.
- A challenge/receipt transition is required to bridge the user turn and the
  later mutation: the authorization must be current-session, one-time,
  short-lived, and bound to an exact dirty snapshot. A reason string or feature
  flag alone is insufficient.
- The exact snapshot primitive and typed state-changing command are durable CLI
  behavior suitable for `sympoies/nils-cli`; runtime-kit owns the policy,
  challenge issuance from hook payloads, lease-schema compatibility, command
  routing, product wiring, and acceptance tests.
- Codex and Claude expose the required hook lifecycle. Hermes has no
  runtime-kit hook runner and cannot claim the same enforced capability.
- GitHub issue #601 is related to progressive, agent-friendly intent-hook UX but
  does not define checkout adoption or its ownership transition.

## Decisions

1. Add one off-by-default master switch,
   `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION=1`. It enables advisory context and
   the challenged adoption route; it never disables normal checkout-lease
   enforcement.
2. On a dirty checkout without a same-session lease, the opt-in
   `UserPromptSubmit` hook emits private context only. For read-only Q&A the
   agent does not surface it. Before implementation, the agent asks the user to
   choose between read-only inspection followed by explicit adoption, or a
   managed worktree.
3. Each dirty user turn may issue a private, short-lived adoption challenge.
   The challenge stores a random bearer token, hashed hook session identity,
   physical checkout instance, canonical dirty-snapshot ID, HEAD/branch summary,
   user-turn digest, issue/expiry time, and no raw prompt or file contents.
   Issuing a challenge does not acquire a lease.
4. The agent may consume a challenge only after an unambiguous post-warning user
   turn authorizes takeover. The hook does not interpret that text; policy makes
   the agent responsible, while the stored turn digest makes the authorization
   auditable. Ambiguous answers require another question.
5. `git-cli worktree dirty-snapshot` is the canonical read-only snapshot command.
   `git-cli worktree adopt-dirty --challenge <token> --reason-file <path>` is the
   governed state transition. The lease guard permits only this sole command as
   an admission escape; the CLI validates and atomically consumes the challenge
   under the lease lock before writing the adopted lease and receipt.
6. A snapshot binds checkout/common-dir identity, checkout-instance sentinel,
   HEAD and symbolic branch state, index entries, staged and unstaged content,
   and untracked regular-file/symlink content. Snapshot calculation is
   streaming and race-checked. V1 rejects active Git operations, unmerged index
   stages, dirty submodules, unsupported special files, and bounded-resource
   overflow instead of weakening the fingerprint.
7. Adoption rejects a live foreign lease, expired/used/wrong-session challenge,
   checkout-instance mismatch, state drift, active Git operation, unsupported
   dirty state, malformed state, or unverifiable snapshot. Any drift requires a
   fresh warning and fresh user authorization.
8. The adopted lease schema preserves the existing session, instance, root,
   acquisition, refresh, and expiry fields and adds privacy-safe adoption
   metadata: receipt ID, snapshot ID, authorization-turn digest, reason digest,
   and adoption time. It stores neither diff contents nor the reason text.
9. Stop remains non-destructive. It releases a clean matching-session lease,
   retains a dirty or unverifiable lease, and never stashes, resets, cleans,
   commits, deletes, or moves files. Expiry never transfers ownership; a later
   session must obtain fresh authorization. A receipt-bound revoke command may
   remove only the lease/adoption state and never working-tree data.
10. The managed-worktree escape remains available from every rejection path.
    Disabling the feature flag immediately disables new challenge issuance and
    adoption, while ordinary lease reads, refresh, blocking, and Stop audit
    continue unchanged.

## Scope

- In scope: nils-cli snapshot/adopt/revoke contract and tests; runtime-kit
  policy, challenge and lease-schema changes, Codex/Claude hook wiring, command
  classification, render/golden coverage, full validation, release/pin
  convergence, and deploy-readiness proof.
- Out of scope: natural-language authorization parsing, automatic adoption,
  stashing/resetting/cleaning/committing unknown changes, taking over a foreign
  live lease, continuing a Git operation, dirty-submodule adoption in v1,
  Hermes enforcement, and automatic live-home activation.

## Deployment boundary

Implementation, review, provider delivery, required nils-cli release/pin
convergence, and deploy-readiness validation belong to this L2. Applying the
new hook configuration to live Codex or Claude homes is a separate final step
requiring fresh explicit maintainer approval after readiness is proven.

## Execution

- Recommended plan: docs/plans/2026-07-17-dirty-checkout-adoption/dirty-checkout-adoption-plan.md
- Recommended execution state: docs/plans/2026-07-17-dirty-checkout-adoption/dirty-checkout-adoption-execution-state.md
