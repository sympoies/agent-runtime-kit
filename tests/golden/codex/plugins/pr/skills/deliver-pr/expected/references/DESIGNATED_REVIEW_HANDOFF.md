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
fi
```

Stop at `awaiting designated review`. The parent uses the handoff's response
and completion deadlines to wait for a correlated initial disposition and,
after `accepted`, a correlated `completed` or `failed` result. Correlate the
reply with the request, reviewer, PR, assignment generation, and reviewed head;
inspect the exact authenticated mailbox body. Delivery, read receipts, activity,
and elapsed time are insufficient. On deferred, declined, failed, closed,
unreachable, or timeout, retain the PR and receipts and return to the coordinator.
Ownership changes only through reviewer surrender or explicit coordinator
recovery. Do not run closure while waiting or after a negative disposition.

After correlated `completed`, the parent sets
`DESIGNATED_REVIEW_DISPOSITION=completed` and runs this separate closure fence.
Re-read the provider head after repairs; the CLI must prove published review
and owned closed ledger for that exact head. A mailbox pass alone is insufficient.

```bash
# Designated-review closure only.
if [ -n "${AGENT_REVIEWER_SESSION:-}" ]; then
  [ "${DESIGNATED_REVIEW_DISPOSITION:-}" = completed ] || {
    echo "awaiting designated review: correlated completion required" >&2
    exit 69
  }
  CLOSURE_VIEW="$(forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    --format json pr view "$PR_NUMBER")" || exit $?
  CLOSURE_HEAD="$(printf '%s\n' "$CLOSURE_VIEW" | \
    jq -er 'select(.ok == true) | .data.head_sha')" || exit $?
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
    pr review-handoff check "$PR_NUMBER" --expected-head "$CLOSURE_HEAD" || exit $?
fi
```
