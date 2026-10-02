# Designated Review Handoff

Use only after resolving an explicit reviewer assignment. Preserve the
unassigned self-run route. Read `core/policies/session-coordination.md` for
mailbox dispositions, bounded waits, explicit surrender/recovery, and repair
ordering. The private body must match the provider base/head and assignment
generation captured below; retain its bytes for an identical send retry.

```bash
# Designated-review route only.
if [ -n "${AGENT_REVIEWER_SESSION:-}" ]; then
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    pr review-handoff --help >/dev/null 2>&1 || {
    echo "awaiting designated review: CLI capability unavailable; return to coordinator" >&2
    exit 69
  }
  : "${DESIGNATED_REVIEW_AUTHOR:?bind the configured native review author}"
  : "${REVIEW_HANDOFF_BODY_FILE:?prepare the private evidence handoff}"
  HANDOFF_VIEW="$(forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    --format json pr view "$PR_NUMBER")" || exit $?
  HANDOFF_HEAD="$(printf '%s\n' "$HANDOFF_VIEW" | \
    jq -er 'select(.ok == true) | .data.head_sha')" || exit $?
  HANDOFF_STATE="$(forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    --format json pr review-handoff inspect "$PR_NUMBER" \
    --expected-head "$HANDOFF_HEAD" --review-author "$DESIGNATED_REVIEW_AUTHOR")" || exit $?
  if printf '%s\n' "$HANDOFF_STATE" | jq -e '.ok == true and .data.handoff == null' >/dev/null; then
    HANDOFF_TIP="$(printf '%s\n' "$HANDOFF_STATE" | \
      jq -er 'select(.ok == true) | .data.state_tip_digest // "none"')" || exit $?
    HANDOFF_BASE_SHA="$(printf '%s\n' "$HANDOFF_STATE" | \
      jq -er 'select(.ok == true) | .data.base_sha')" || exit $?
    HANDOFF_STATE="$(forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
      pr review-handoff assign "$PR_NUMBER" \
      --reviewer-session "$AGENT_REVIEWER_SESSION" \
      --review-author "$DESIGNATED_REVIEW_AUTHOR" \
      --base-sha "$HANDOFF_BASE_SHA" --expected-head "$HANDOFF_HEAD" \
      --expected-state "$HANDOFF_TIP")" || exit $?
  fi
  printf '%s\n' "$HANDOFF_STATE" | \
    jq -e '.ok == true and .data.status == "awaiting-designated-review"' >/dev/null || {
    echo "awaiting designated review: ownership inactive; return to coordinator" >&2
    exit 69
  }
  HANDOFF_DIGEST="$(printf '%s\n' "$HANDOFF_STATE" | \
    jq -er 'select(.ok == true) | .data.handoff_digest')" || exit $?
  REVIEWER_MAILBOX_ARGS=(--to "${AGENT_REVIEWER_SESSION%%@*}")
  case "$AGENT_REVIEWER_SESSION" in
    *@*) REVIEWER_MAILBOX_ARGS+=(--to-machine "${AGENT_REVIEWER_SESSION#*@}") ;;
  esac
  agent-session message send --from "$AGENT_SESSION_ID" \
    "${REVIEWER_MAILBOX_ARGS[@]}" --body-file "$REVIEW_HANDOFF_BODY_FILE" \
    --idempotency-key "review-handoff-$HANDOFF_DIGEST-$HANDOFF_HEAD" || exit $?
  # Bounded mailbox wait and repair/return follow session-coordination policy.
  # Recheck after closure; mailbox pass is insufficient.
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
    pr review-handoff check "$PR_NUMBER" --expected-head "$HANDOFF_HEAD" || exit $?
fi
```

`inspect` validates the requested reviewer, public author, and current head
before any private send. An inactive or conflicting assignment returns control
to the coordinator; never overwrite it implicitly. A failed send retains the
same assignment. Its record digest includes repository identity, and the key
binds that ownership generation and head so a replacement at the same head
gets a new message while an identical retry is idempotent.

The reviewer binds `AGENT_REVIEW_ASSIGNMENT_GENERATION` from the inspected
handoff before appending or publishing. Ordinary handover requires its
`surrender` record. Only the owning coordinator may use explicit `recover`
with the retained head/tip and a bounded reason after reviewer unavailability;
that revokes the generation and never permits self-review. A subsequent
coordinator `assign` creates a fresh interval and the route can be retried.
On repair, require the old-head observation receipt before pushing. After
closure, re-read the provider head and run `check` again before ordinary merge
gates. Mailbox pass alone does not admit merge.
