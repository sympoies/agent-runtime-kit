#!/usr/bin/env bash
# Deterministic provider-local rehearsal for the program/dispatch issue route.
set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

DISPATCH_ARTIFACTS_DIR="$ARTIFACTS_DIR/dispatch"
DISPATCH_STORE="$TMP_ROOT/dispatch-provider"
mkdir -p "$DISPATCH_ARTIFACTS_DIR" "$DISPATCH_STORE"

provider_program_probe() {
  local tracker child_a child_b view
  local common=(--provider local --repo local:dispatch-smoke --store-root "$DISPATCH_STORE" --format json)
  cat >"$DISPATCH_ARTIFACTS_DIR/tracker.md" <<'BODY'
## Purpose
Coordinate two lanes that must integrate on one branch.

Program key: dispatch-smoke

## How to resume
Read this tracker and the child issues.

## Decisions
Use one integration branch.

## Phase table
- [ ] Lane A
- [ ] Lane B

## Dependency graph
Lane A and Lane B precede integration.

## Open decisions
None.

## Checkpoint log
Opened for local rehearsal.
BODY
  tracker="$(forge-cli "${common[@]}" issue create \
    --title 'Dispatch smoke tracker' --body-file "$DISPATCH_ARTIFACTS_DIR/tracker.md" \
    --label workflow::tracking | jq -er 'select(.ok == true) | .data.number')"
  cat >"$DISPATCH_ARTIFACTS_DIR/child.md" <<BODY
Program key: dispatch-smoke; tracker issue #$tracker.

## Goal
Deliver one assigned lane.

## Acceptance
The lane PR is reviewed and merged into the integration branch.
BODY
  child_a="$(forge-cli "${common[@]}" issue create \
    --title 'Dispatch smoke lane A' --body-file "$DISPATCH_ARTIFACTS_DIR/child.md" \
    --label workflow::follow-up | jq -er 'select(.ok == true) | .data.number')"
  child_b="$(forge-cli "${common[@]}" issue create \
    --title 'Dispatch smoke lane B' --body-file "$DISPATCH_ARTIFACTS_DIR/child.md" \
    --label workflow::follow-up | jq -er 'select(.ok == true) | .data.number')"
  python3 - "$DISPATCH_ARTIFACTS_DIR/tracker.md" "$child_a" "$child_b" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
body = path.read_text()
body = body.replace('Lane A\n', f'Lane A (#{sys.argv[2]})\n')
body = body.replace('Lane B\n', f'Lane B (#{sys.argv[3]})\n')
path.write_text(body)
PY
  forge-cli "${common[@]}" issue edit "$tracker" \
    --body-file "$DISPATCH_ARTIFACTS_DIR/tracker.md" >/dev/null
  view="$(forge-cli "${common[@]}" issue view "$tracker")"
  printf '%s\n' "$view" | jq -e --arg a "#$child_a" --arg b "#$child_b" \
    '.ok == true and (.data.body | contains($a) and contains($b))' >/dev/null
  forge-cli "${common[@]}" issue view "$child_a" |
    jq -e '.ok == true and .data.state == "open"' >/dev/null
  forge-cli "${common[@]}" issue view "$child_b" |
    jq -e '.ok == true and .data.state == "open"' >/dev/null
  # The local provider supports PR reads from seeded records, while PR
  # mutation stays with the real provider. Check the state gate before any
  # child closeout, then read back the simulated merge and checkpoint.
  mkdir -p "$DISPATCH_STORE/prs"
  cat >"$DISPATCH_STORE/prs/7.json" <<'PR'
{"number":7,"state":"OPEN","merged":false,"merge_sha":null,
 "checks":"pending","required_state":"pending","required_count":1,
 "non_required_failures":[],"comments":[]}
PR
  if forge-cli "${common[@]}" pr checks 7 |
    jq -e '.ok == true and .data.state == "success"' >/dev/null; then
    echo 'pending lane checks passed the closeout gate' >&2
    return 1
  fi
  cat >"$DISPATCH_STORE/prs/7.json" <<'PR'
{"number":7,"state":"MERGED","merged":true,
 "merge_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "checks":"success","required_state":"success","required_count":1,
 "non_required_failures":[],"comments":[{"body":"Independent review approved lane A head",
 "html_url":"local://dispatch-smoke/pull/7#comment-1","author":"reviewer"}]}
PR
  forge-cli "${common[@]}" pr checks 7 |
    jq -e '.ok == true and .data.state == "success" and .data.required_count == 1' >/dev/null
  forge-cli "${common[@]}" pr view 7 |
    jq -e '.ok == true and .data.state == "merged" and
      .data.merge_commit_sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' >/dev/null
  forge-cli "${common[@]}" pr comments 7 |
    jq -e '.ok == true and (.data.comments | any(.author == "reviewer" and
      (.body | contains("Independent review approved lane A head"))))' >/dev/null
  forge-cli "${common[@]}" issue comment "$child_a" \
    --body 'Lane PR #7 merged into the integration branch at aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; required checks passed; independent review approved the lane head.' >/dev/null
  forge-cli "${common[@]}" issue view "$child_a" --with-comments |
    jq -e '.ok == true and (.data.comments | any(.body | contains("Lane PR #7 merged") and contains("independent review approved")))' >/dev/null
  forge-cli "${common[@]}" issue close "$child_a" >/dev/null
  cat >"$DISPATCH_STORE/prs/9.json" <<'PR'
{"number":9,"state":"MERGED","merged":true,
 "merge_sha":"cccccccccccccccccccccccccccccccccccccccc",
 "checks":"success","required_state":"success","required_count":1,
 "non_required_failures":[],"comments":[{"body":"Independent review approved lane B head",
 "html_url":"local://dispatch-smoke/pull/9#comment-1","author":"reviewer"}]}
PR
  forge-cli "${common[@]}" pr checks 9 |
    jq -e '.ok == true and .data.state == "success" and .data.required_count == 1' >/dev/null
  forge-cli "${common[@]}" pr view 9 |
    jq -e '.ok == true and .data.state == "merged" and
      .data.merge_commit_sha == "cccccccccccccccccccccccccccccccccccccccc"' >/dev/null
  forge-cli "${common[@]}" pr comments 9 |
    jq -e '.ok == true and (.data.comments | any(.author == "reviewer" and
      (.body | contains("Independent review approved lane B head"))))' >/dev/null
  forge-cli "${common[@]}" issue comment "$child_b" \
    --body 'Lane PR #9 merged into the integration branch at cccccccccccccccccccccccccccccccccccccccc; required checks passed; independent review approved the lane head.' >/dev/null
  forge-cli "${common[@]}" issue view "$child_b" --with-comments |
    jq -e '.ok == true and (.data.comments | any(.body | contains("Lane PR #9 merged") and contains("independent review approved")))' >/dev/null
  forge-cli "${common[@]}" issue close "$child_b" >/dev/null
  forge-cli "${common[@]}" issue view "$child_a" |
    jq -e '.ok == true and .data.state == "closed"' >/dev/null
  forge-cli "${common[@]}" issue view "$child_b" |
    jq -e '.ok == true and .data.state == "closed"' >/dev/null
  python3 - "$DISPATCH_ARTIFACTS_DIR/tracker.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
body = path.read_text()
assert body.count('- [ ] Lane ') == 2
path.write_text(body.replace('- [ ] Lane ', '- [x] Lane '))
PY
  forge-cli "${common[@]}" issue edit "$tracker" \
    --body-file "$DISPATCH_ARTIFACTS_DIR/tracker.md" >/dev/null
  forge-cli "${common[@]}" issue view "$tracker" |
    jq -e '.ok == true and .data.state == "open" and
      (.data.body | contains("- [x] Lane A") and contains("- [x] Lane B"))' >/dev/null
  cat >"$DISPATCH_STORE/prs/8.json" <<'PR'
{"number":8,"state":"MERGED","merged":true,
 "merge_sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
 "checks":"success","required_state":"success","required_count":1,
 "non_required_failures":[],"comments":[]}
PR
  forge-cli "${common[@]}" pr view 8 |
    jq -e '.ok == true and .data.state == "merged" and
      .data.merge_commit_sha == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"' >/dev/null
  forge-cli "${common[@]}" issue comment "$tracker" \
    --body 'Integration PR #8 merged at bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; both child issues closed with lane checkpoints and tracker checkboxes completed.' >/dev/null
  forge-cli "${common[@]}" issue view "$tracker" --with-comments |
    jq -e '.ok == true and (.data.comments | any(.body | contains("Integration PR #8 merged") and contains("both child issues closed")))' >/dev/null
  forge-cli "${common[@]}" issue close "$tracker" >/dev/null
  forge-cli "${common[@]}" issue view "$tracker" |
    jq -e '.ok == true and .data.state == "closed"' >/dev/null
}

rendered_route_probe() {
  local source="$REPO_ROOT/core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera"
  grep -Fq 'program/dispatch' "$source"
  grep -Fq 'workflow::tracking' "$source"
  grep -Fq 'workflow::follow-up' "$source"
  python3 - "$source" <<'PY'
from pathlib import Path
import re
import sys
body = Path(sys.argv[1]).read_text()
guarded_merge = re.search(r'pr merge \\\n\s+"\$LANE_PR_NUMBER" --allow-non-default-base \\\n\s+--expected-head "\$REVIEWED_HEAD" --expected-base "\$INTEGRATION_BRANCH"', body)
assert guarded_merge, 'lane merge must bind reviewed head and integration base'
assert body.index('reviewed readiness stop (`--no-merge`)') < guarded_merge.start()
assert body.index('only after independent') < guarded_merge.start()
assert body.index('green required checks') < guarded_merge.start()
assert guarded_merge.end() < body.index('close the child with `forge-cli issue close`')
assert body.index('close the child with `forge-cli issue close`') < body.index('Tick its tracker checkbox')
assert body.index('deliver the integration PR through') < body.index('Read back the integration PR merge and all children')
assert body.index('Read back the integration PR merge and all children') < body.index('close the tracker through `forge-cli issue close`')
PY
  ! grep -Eq 'plan-issue|plan-tooling|plan-archive' "$source"
  rendered_contract_assert_skill dispatch deliver-dispatch-plan
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'forge-cli issue close'
  rendered_contract_assert_reference dispatch deliver-dispatch-plan references/outcome-routing.md
}

failures=0
results_record_case 'dispatch.deliver-dispatch-plan.provider-program' \
  'forge-cli local tracker, seeded PR read, checkpoint and closeout passed' provider_program_probe
results_record_case 'dispatch.deliver-dispatch-plan.rendered-route' \
  'rendered dispatch routes through program issues without plan CLIs' rendered_route_probe
exit "$failures"
