#!/usr/bin/env bash
# Portable historical-upgrade/read-back/rollback and routing-contract acceptance.

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/runtime-home.sh"

CONVERGENCE_ARTIFACTS_DIR="$ARTIFACTS_DIR/convergence"
mkdir -p "$CONVERGENCE_ARTIFACTS_DIR"

validate_dirty_source_rejected() {
  local dirty_source="$TMP_ROOT/dirty-source"
  local rejected_snapshot="$TMP_ROOT/rejected-snapshot"

  git clone -q --no-hardlinks "$PORTABLE_SOURCE_ROOT" "$dirty_source"
  printf 'operator private material\n' >"$dirty_source/operator-note.txt"
  if runtime_prepare_portable_source "$dirty_source" "$rejected_snapshot" \
    >"$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stdout" \
    2>"$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stderr"; then
    return 1
  fi
  test ! -e "$rejected_snapshot"
  grep -q 'portable source must be clean' \
    "$CONVERGENCE_ARTIFACTS_DIR/dirty-source.stderr"
}

validate_snapshot_ref_boundary() {
  local source="$TMP_ROOT/ref-boundary-source"
  local snapshot="$TMP_ROOT/ref-boundary-snapshot"
  local base_revision private_commit dangling_blob

  base_revision="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  runtime_prepare_portable_source "$REPO_ROOT" "$source" >/dev/null
  git -C "$source" config user.name 'Portable Acceptance'
  git -C "$source" config user.email 'portable-acceptance@example.invalid'
  git -C "$source" switch -q -c private-sentinel
  printf 'private branch sentinel\n' >"$source/private-sentinel.txt"
  git -C "$source" add private-sentinel.txt
  git -C "$source" commit -q -m 'test: private sentinel'
  private_commit="$(git -C "$source" rev-parse HEAD)"
  git -C "$source" -c advice.detachedHead=false checkout -q --detach "$base_revision"
  dangling_blob="$(printf 'dangling private sentinel\n' | git -C "$source" hash-object -w --stdin)"

  runtime_prepare_portable_source "$source" "$snapshot" >/dev/null
  if git -C "$snapshot" cat-file -e "$private_commit^{commit}" 2>/dev/null; then
    return 1
  fi
  if git -C "$snapshot" cat-file -e "$dangling_blob^{blob}" 2>/dev/null; then
    return 1
  fi
  test -z "$(git -C "$snapshot" for-each-ref --format='%(refname)' | grep private-sentinel || true)"
  test "$(git -C "$snapshot" rev-parse HEAD)" = "$base_revision"
}

validate_routing_contract() {
  local product="$1"
  local plans="$CONVERGENCE_ARTIFACTS_DIR/$product/routing-contract.json"

  mkdir -p "$(dirname "$plans")"
  python3 - \
    "$REPO_ROOT" \
    "$SCRIPT_DIR/product/routing-contract-cases.json" \
    "$SCRIPT_DIR/product/prompts" \
    "$product" \
    "$plans" <<'PY'
import hashlib
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
cases = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
prompt_root = pathlib.Path(sys.argv[3])
product = sys.argv[4]
output = pathlib.Path(sys.argv[5])

assert cases["schema"] == "agent-runtime-kit.routing-contract.v1"
active_text = (root / "manifests/skills.yaml").read_text(encoding="utf-8")
active_ids = set(re.findall(r"^  - id: ([a-z0-9.-]+)$", active_text, re.M))
retired = json.loads(
    (root / "manifests/retired-skill-ids.json").read_text(encoding="utf-8")
)["skills"]
intent_text = (root / "AGENT_DOCS.toml").read_text(encoding="utf-8")
plans = []

for case in cases["cases"]:
    prompt = (prompt_root / case["prompt"]).read_text(encoding="utf-8")
    lowered = prompt.lower()
    for skill_id in retired:
        leaf = skill_id.split(".", 1)[1]
        assert skill_id not in prompt, (case["id"], skill_id)
        assert leaf not in lowered, (case["id"], leaf)
    route = case["expected_route"]
    if route.startswith("intent:"):
        assert f'context = "{route.split(":", 1)[1]}"' in intent_text, route
    else:
        assert route in active_ids, route
    plans.append(
        {
            "case": case["id"],
            "product": product,
            "contract_route": route,
            "fixture_contract": True,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        }
    )

output.write_text(
    json.dumps({"schema": "portable-routing-contract.v1", "plans": plans}, sort_keys=True) + "\n"
)
PY

  python3 - "$plans" <<'PY'
import json
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
data = json.loads(text)
assert data["plans"]
assert len({item["case"] for item in data["plans"]}) == len(data["plans"])
assert all(item["fixture_contract"] for item in data["plans"])
for forbidden in (r"/Users/", r"/home/", r"ssh://", r"@[0-9]", r"token"):
    assert re.search(forbidden, text, re.I) is None, forbidden
PY
  ROUTING_CONTRACT_COUNT="$(python3 - "$plans" <<'PY'
import json
import pathlib
import sys

print(len(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["plans"]))
PY
)"
}

PORTABLE_SOURCE_ROOT="$(runtime_prepare_portable_source "$REPO_ROOT" "$TMP_ROOT/portable-source")"
BASELINE_REVISION="$(python3 - "$PORTABLE_SOURCE_ROOT/manifests/retired-hermes-skill-copies.json" <<'PY'
import json
import pathlib
import sys

print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["source_revision"])
PY
)"
BASELINE_SOURCE_ROOT="$(runtime_prepare_revision_source \
  "$PORTABLE_SOURCE_ROOT" "$BASELINE_REVISION" "$TMP_ROOT/baseline-source")"
products="${PRODUCT:-codex claude}"
failures=0
if validate_dirty_source_rejected && validate_snapshot_ref_boundary; then
  results_add "convergence.portable-source-boundary" shared-cli pass 1 \
    "dirty content and unrelated refs or objects were excluded from portable snapshots"
else
  results_add "convergence.portable-source-boundary" shared-cli fail 0 \
    "dirty source rejection boundary failed"
  failures=1
fi
for product in $products; do
  if runtime_convergence_product \
    "$PORTABLE_SOURCE_ROOT" "$BASELINE_SOURCE_ROOT" "$TMP_ROOT" "$product" \
    "$CONVERGENCE_ARTIFACTS_DIR/$product" &&
    python3 - "$CONVERGENCE_ARTIFACTS_DIR/$product/$product.portable-summary.json" <<'PY'
import json
import pathlib
import sys

summary = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert summary["baseline_skill_count"] == 66
assert summary["skill_count"] == 26
PY
  then
    results_add "convergence.$product.lifecycle" "$product" pass \
      "$RUNTIME_SMOKE_SKILL_COUNT" \
      "historical upgrade, rollback rehearsal, retired prune, exact registry activation, receipt transition, and idempotent apply passed"
  else
    results_add "convergence.$product.lifecycle" "$product" fail 0 \
      "portable lifecycle acceptance failed"
    failures=1
  fi

  original_repo_root="$REPO_ROOT"
  REPO_ROOT="$PORTABLE_SOURCE_ROOT"
  if validate_routing_contract "$product"; then
    results_add "convergence.$product.routing-contract" "$product" pass \
      "$ROUTING_CONTRACT_COUNT" \
      "$ROUTING_CONTRACT_COUNT generic prompt/route fixtures validated; behavioral routing remains live acceptance"
  else
    results_add "convergence.$product.routing-contract" "$product" fail 0 \
      "prompt/route contract validation failed"
    failures=1
  fi
  REPO_ROOT="$original_repo_root"
done

exit "$failures"
