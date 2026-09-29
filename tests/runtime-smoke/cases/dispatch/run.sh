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
  forge-cli "${common[@]}" issue close "$child_a" >/dev/null
  forge-cli "${common[@]}" issue close "$child_b" >/dev/null
  forge-cli "${common[@]}" issue close "$tracker" >/dev/null
  forge-cli "${common[@]}" issue view "$tracker" |
    jq -e '.ok == true and .data.state == "closed"' >/dev/null
}

rendered_route_probe() {
  local source="$REPO_ROOT/core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera"
  grep -Fq 'program/dispatch' "$source"
  grep -Fq 'workflow::tracking' "$source"
  grep -Fq 'workflow::follow-up' "$source"
  grep -Fq -- '--allow-non-default-base' "$source"
  ! grep -Eq 'plan-issue|plan-tooling|plan-archive' "$source"
  rendered_contract_assert_skill dispatch deliver-dispatch-plan
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'forge-cli issue close'
  rendered_contract_assert_reference dispatch deliver-dispatch-plan references/outcome-routing.md
}

failures=0
results_record_case 'dispatch.deliver-dispatch-plan.provider-program' \
  'forge-cli local tracker and child create/edit/read/close passed' provider_program_probe
results_record_case 'dispatch.deliver-dispatch-plan.rendered-route' \
  'rendered dispatch routes through program issues without plan CLIs' rendered_route_probe
exit "$failures"
