#!/usr/bin/env bash
# Deterministic probes for evidence skills.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"

EVIDENCE_ARTIFACTS_DIR="$ARTIFACTS_DIR/evidence"
EVIDENCE_WORKSPACE="$TMP_ROOT/workspaces/evidence-basic-repo"
mkdir -p "$EVIDENCE_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$EVIDENCE_WORKSPACE"

require_evidence_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke evidence: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_web_evidence_probe() {
  local root="$EVIDENCE_ARTIFACTS_DIR/web-root"
  local out_dir="$EVIDENCE_ARTIFACTS_DIR/web-evidence"
  local out_json="$EVIDENCE_ARTIFACTS_DIR/web-evidence.capture.json"
  local port_file="$EVIDENCE_ARTIFACTS_DIR/web-server.port"
  local server_out="$EVIDENCE_ARTIFACTS_DIR/web-server.stdout.txt"
  local server_err="$EVIDENCE_ARTIFACTS_DIR/web-server.stderr.txt"
  local server_pid port attempt
  require_evidence_bin web-evidence || return 1
  require_evidence_bin python3 || return 1
  mkdir -p "$root" "$out_dir"
  printf 'runtime smoke web evidence\n' >"$root/index.txt"
  python3 - "$root" "$port_file" >"$server_out" 2>"$server_err" <<'PY' &
import http.server
import os
import socketserver
import sys

root = sys.argv[1]
port_file = sys.argv[2]
os.chdir(root)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
    with open(port_file, "w", encoding="utf-8") as handle:
        handle.write(str(httpd.server_address[1]))
    httpd.serve_forever()
PY
  server_pid="$!"
  attempt=0
  while [ "$attempt" -lt 10 ]; do
    if [ -s "$port_file" ]; then
      break
    fi
    attempt=$((attempt + 1))
    sleep 0.1
  done
  if [ ! -s "$port_file" ]; then
    kill "$server_pid" >/dev/null 2>&1 || true
    wait "$server_pid" 2>/dev/null || true
    echo "runtime-smoke evidence: local web server did not publish a port" >&2
    return 1
  fi
  port="$(cat "$port_file")"
  (
    cd "$EVIDENCE_WORKSPACE"
    web-evidence capture "http://127.0.0.1:$port/index.txt" \
      --out "$out_dir" \
      --method get \
      --format json \
      --timeout-seconds 3 \
      --max-body-bytes 1024 \
      --body-preview-bytes 128
  ) >"$out_json" 2>&1
  kill "$server_pid" >/dev/null 2>&1 || true
  wait "$server_pid" 2>/dev/null || true
  grep -q '"schema_version": "cli.web-evidence.capture.v1"' "$out_json"
  grep -q '"ok": true' "$out_json"
  grep -q '"status_code": 200' "$out_json"
  test -s "$out_dir/summary.json"
  test -s "$out_dir/body-preview.redacted.txt"
}

run_test_first_evidence_probe() {
  local out_dir="$EVIDENCE_ARTIFACTS_DIR/test-first-evidence"
  require_evidence_bin test-first-evidence || return 1
  mkdir -p "$out_dir"
  test-first-evidence init \
    --out "$out_dir" \
    --classification docs-only \
    --production-path README.md \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/test-first.init.json"
  test-first-evidence record-waiver \
    --out "$out_dir" \
    --reason "docs-only runtime smoke fixture" \
    --substitute-validation "bash -n tests/runtime-smoke/run.sh" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/test-first.waiver.json"
  test-first-evidence record-final \
    --out "$out_dir" \
    --command "bash tests/runtime-smoke/run.sh --mode deterministic --domain evidence" \
    --status pass \
    --summary "runtime smoke evidence fixture passed" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/test-first.final.json"
  test-first-evidence verify \
    --out "$out_dir" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/test-first.verify.json"
  grep -q '"schema_version": "cli.test-first-evidence.verify.v1"' "$EVIDENCE_ARTIFACTS_DIR/test-first.verify.json"
  grep -q '"ok": true' "$EVIDENCE_ARTIFACTS_DIR/test-first.verify.json"
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/test-first.verify.json"
}

run_review_evidence_probe() {
  local out_dir="$EVIDENCE_ARTIFACTS_DIR/review-evidence"
  local artifact="$EVIDENCE_ARTIFACTS_DIR/review-artifact.txt"
  require_evidence_bin review-evidence || return 1
  mkdir -p "$out_dir"
  printf 'runtime smoke review artifact\n' >"$artifact"
  review-evidence init \
    --out "$out_dir" \
    --subject "runtime smoke evidence fixture" \
    --reviewer runtime-smoke \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/review.init.json"
  review-evidence record-finding \
    --out "$out_dir" \
    --severity low \
    --path README.md \
    --line 1 \
    --summary "fixture finding recorded and fixed" \
    --status fixed \
    --artifact "$artifact" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/review.finding.json"
  review-evidence record-validation \
    --out "$out_dir" \
    --command "true" \
    --status pass \
    --summary "fixture validation passed" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/review.validation.json"
  review-evidence verify \
    --out "$out_dir" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/review.verify.json"
  grep -q '"schema_version": "cli.review-evidence.verify.v1"' "$EVIDENCE_ARTIFACTS_DIR/review.verify.json"
  grep -q '"ok": true' "$EVIDENCE_ARTIFACTS_DIR/review.verify.json"
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/review.verify.json"
}

run_docs_impact_probe() {
  local docs_workspace="$TMP_ROOT/workspaces/docs-impact-repo"
  local record_dir="$EVIDENCE_ARTIFACTS_DIR/docs-impact-record"
  local out_json="$EVIDENCE_ARTIFACTS_DIR/docs-impact.scan.json"
  require_evidence_bin docs-impact || return 1
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$docs_workspace"
  git -C "$docs_workspace" init -q
  git -C "$docs_workspace" config user.email runtime-smoke@example.invalid
  git -C "$docs_workspace" config user.name "Runtime Smoke"
  git -C "$docs_workspace" add README.md
  git -C "$docs_workspace" commit -q -m "Initial fixture"
  mkdir -p "$docs_workspace/docs"
  printf 'docs impact fixture\n' >"$docs_workspace/docs/runtime-smoke.md"
  docs-impact scan \
    --repo "$docs_workspace" \
    --include-untracked \
    --format json >"$out_json"
  grep -q '"schema_version": "cli.docs-impact.scan.v1"' "$out_json"
  grep -q '"ok": true' "$out_json"
  grep -q '"docs_changed": true' "$out_json"
  grep -q '"docs/runtime-smoke.md"' "$out_json"
  docs-impact record --help >/dev/null
  docs-impact record \
    --out "$record_dir" \
    --repo "$docs_workspace" \
    --base HEAD \
    --disposition docs-updated \
    --rationale "runtime smoke fixture added matching docs" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/docs-impact.record.json"
  docs-impact verify \
    --out "$record_dir" \
    --repo "$docs_workspace" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/docs-impact.verify.json"
  grep -q '"schema_version": "cli.docs-impact.verify.v1"' "$EVIDENCE_ARTIFACTS_DIR/docs-impact.verify.json"
  grep -q '"ok": true' "$EVIDENCE_ARTIFACTS_DIR/docs-impact.verify.json"
}

run_selective_intent_control_plane_probe() {
  local workspace="$TMP_ROOT/workspaces/selective-intent-repo"
  local state_home="$EVIDENCE_ARTIFACTS_DIR/agent-docs-state"
  local test_first_dir="$EVIDENCE_ARTIFACTS_DIR/phase-aware-test-first"
  require_evidence_bin agent-docs || return 1
  agent-docs --version | grep -q '1\.21\.17'
  agent-docs session --help | grep -q 'status'
  mkdir -p "$workspace/src" "$workspace/tests"
  printf '# Dev\n' >"$workspace/DEV.md"
  printf '# Fixture\n' >"$workspace/README.md"
  printf 'fn main() {}\n' >"$workspace/src/lib.rs"
  mkdir -p "$workspace/build"
  printf 'generated\n' >"$workspace/build/output.rs"
  cat >"$workspace/AGENT_DOCS.toml" <<'TOML'
[[document]]
context = "project-dev"
scope = "project"
path = "DEV.md"
required = true
when = "always"

[path_classes]
production = ["src/**", "mixed/**"]
test = ["tests/**"]
docs = ["**/*.md", "mixed/**"]
generated = ["build/**"]
unmatched = "unknown"
TOML
  agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session activate --session-id runtime-smoke --product codex \
    --state-home "$state_home" --intent project-dev --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.activate.json"
  agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session status --session-id runtime-smoke --product codex \
    --state-home "$state_home" --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.status.json"
  grep -q '"product": "codex"' "$EVIDENCE_ARTIFACTS_DIR/agent-docs.status.json"
  grep -q '"project-dev"' "$EVIDENCE_ARTIFACTS_DIR/agent-docs.status.json"
  agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session verify --session-id runtime-smoke --product codex \
    --state-home "$state_home" --require-intent project-dev --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.verify.json"
  python3 - "$state_home" "$workspace" \
    "$EVIDENCE_ARTIFACTS_DIR/agent-docs.activate.json" \
    "$EVIDENCE_ARTIFACTS_DIR/agent-docs.status.json" \
    "$EVIDENCE_ARTIFACTS_DIR/agent-docs.verify.json" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

state_home = Path(sys.argv[1])
workspace = Path(sys.argv[2]).resolve()
activate, status, verify = [json.loads(Path(path).read_text()) for path in sys.argv[3:]]
for body, schema, verified in (
    (activate, "cli.agent-docs.session.activate.v1", True),
    (status, "cli.agent-docs.session.status.v1", False),
    (verify, "cli.agent-docs.session.verify.v1", True),
):
    assert body["schema_version"] == schema, body
    assert body["ok"] is True, body
    assert body["data"]["product"] == "codex", body
    assert body["data"]["active_intents"] == ["project-dev"], body
    assert body["data"]["verified"] is verified, body

session_hash = "sha256:" + hashlib.sha256(b"runtime-smoke").hexdigest()
project_hash = "sha256:" + hashlib.sha256(str(workspace).encode()).hexdigest()
record_file = activate["data"]["record_file"]
assert record_file == status["data"]["record_file"] == verify["data"]["record_file"]
record_path = (state_home / record_file).resolve()
assert record_path.is_relative_to(state_home.resolve()), record_path
record = json.loads(record_path.read_text())
assert record["schema"] == "agent-docs.session.v1", record
assert record["session_hash"] == session_hash, record
assert record["project_hash"] == project_hash, record
assert record["product"] == "codex", record
assert list(record["active_intents"]) == ["project-dev"], record
expected_record_path = (
    state_home.resolve()
    / "agent-docs"
    / "sessions"
    / session_hash
    / "codex"
    / f"{project_hash}.json"
)
assert record_path == expected_record_path, (record_path, expected_record_path)
PY

  test-first-evidence init --out "$test_first_dir" \
    --classification behavior-change --production-path src/lib.rs --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/phase-aware.init.json"
  if test-first-evidence check --out "$test_first_dir" --phase pre-edit \
    --project-path "$workspace" --path src/lib.rs --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/phase-aware.denied.json" 2>&1; then
    echo "runtime-smoke evidence: production pre-edit unexpectedly allowed before evidence" >&2
    return 1
  fi
  grep -q '"code": "pre-edit-blocked"' "$EVIDENCE_ARTIFACTS_DIR/phase-aware.denied.json"
  test-first-evidence record-failing --out "$test_first_dir" \
    --command "false" --exit-code 1 --summary "fixture failure reproduced" \
    --test-name "runtime smoke regression" --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/phase-aware.failing.json"
  test-first-evidence check --out "$test_first_dir" --phase pre-edit \
    --project-path "$workspace" --path src/lib.rs --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/phase-aware.pre-edit.json"
  grep -q '"allowed": true' "$EVIDENCE_ARTIFACTS_DIR/phase-aware.pre-edit.json"

  local classification path dir
  for classification in docs-only generated-only; do
    path="README.md"
    [[ "$classification" == "generated-only" ]] && path="build/output.rs"
    dir="$EVIDENCE_ARTIFACTS_DIR/phase-$classification"
    test-first-evidence init --out "$dir" --classification "$classification" \
      --production-path "$path" --format json >/dev/null
    test-first-evidence record-waiver --out "$dir" \
      --reason "$classification fixture" --substitute-validation "test -e $path" \
      --format json >/dev/null
    test-first-evidence check --out "$dir" --phase pre-edit \
      --project-path "$workspace" --path "$path" --format json \
      >"$EVIDENCE_ARTIFACTS_DIR/phase-$classification.check.json"
    grep -q '"allowed": true' "$EVIDENCE_ARTIFACTS_DIR/phase-$classification.check.json"
  done

  dir="$EVIDENCE_ARTIFACTS_DIR/phase-unavailable-harness"
  test-first-evidence init --out "$dir" --classification behavior-change \
    --production-path src/lib.rs --format json >/dev/null
  test-first-evidence record-waiver --out "$dir" \
    --reason "fixture harness unavailable" --substitute-validation "test -s src/lib.rs" \
    --format json >/dev/null
  test-first-evidence check --out "$dir" --phase pre-edit \
    --project-path "$workspace" --path src/lib.rs --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/phase-unavailable-harness.check.json"
  grep -q '"allowed": true' "$EVIDENCE_ARTIFACTS_DIR/phase-unavailable-harness.check.json"

  dir="$EVIDENCE_ARTIFACTS_DIR/phase-explicit-waiver"
  test-first-evidence init --out "$dir" --classification behavior-change \
    --production-path src/lib.rs --format json >/dev/null
  test-first-evidence record-waiver --out "$dir" \
    --reason "focused failure cannot be reproduced in the fixture" \
    --substitute-validation "test -s src/lib.rs" --format json >/dev/null
  test-first-evidence check --out "$dir" --phase pre-edit \
    --project-path "$workspace" --path src/lib.rs --format json >"$dir/check.json"
  grep -q '"allowed": true' "$dir/check.json"

  for path in misc/unknown.rs mixed/file.md; do
    dir="$EVIDENCE_ARTIFACTS_DIR/phase-$(basename "$path")"
    test-first-evidence init --out "$dir" --classification behavior-change \
      --production-path "$path" --format json >/dev/null
    if test-first-evidence check --out "$dir" --phase pre-edit \
      --project-path "$workspace" --path "$path" --format json \
      >"$dir/check.json" 2>&1; then
      echo "runtime-smoke evidence: unknown/ambiguous path unexpectedly allowed: $path" >&2
      return 1
    fi
    grep -q '"code": "pre-edit-blocked"' "$dir/check.json"
  done

  local no_classes="$TMP_ROOT/workspaces/no-path-classes"
  mkdir -p "$no_classes/src"
  printf '# Dev\n' >"$no_classes/DEV.md"
  printf '[[document]]\ncontext = "project-dev"\nscope = "project"\npath = "DEV.md"\nrequired = true\nwhen = "always"\n' >"$no_classes/AGENT_DOCS.toml"
  dir="$EVIDENCE_ARTIFACTS_DIR/phase-not-configured"
  test-first-evidence init --out "$dir" --classification behavior-change \
    --production-path src/lib.rs --format json >/dev/null
  test-first-evidence record-failing --out "$dir" --command false --exit-code 1 \
    --summary "fixture failure" --format json >/dev/null
  test-first-evidence check --out "$dir" --phase pre-edit \
    --project-path "$no_classes" --path src/lib.rs --format json >"$dir/check.json"
  python3 - "$EVIDENCE_ARTIFACTS_DIR" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
cases = (
    ("phase-docs-only.check.json", True, "docs", "pre-edit-ready"),
    ("phase-generated-only.check.json", True, "generated", "pre-edit-ready"),
    ("phase-unknown.rs/check.json", False, "unknown", "unknown-path-class"),
    ("phase-file.md/check.json", False, "ambiguous", "ambiguous-path-class"),
    ("phase-not-configured/check.json", True, "not-configured", "path-classes-not-configured"),
)
for relative, allowed, path_class, reason in cases:
    body = json.loads((root / relative).read_text())
    assert body["schema_version"] == "cli.test-first-evidence.check.v1", (relative, body)
    assert body["ok"] is allowed, (relative, body)
    payload = body["result"] if allowed else body["error"]["details"]
    assert payload["phase"] == "pre-edit", (relative, body)
    assert payload["path_class"] == path_class, (relative, body)
    assert payload["reason_code"] == reason, (relative, body)
    if allowed:
        assert payload["allowed"] is True, (relative, body)
        assert "error" not in body, (relative, body)
    else:
        assert body["error"]["code"] == "pre-edit-blocked", (relative, body)
        assert "result" not in body, (relative, body)
PY

  printf '# Added requirement\n' >"$workspace/ADDED.md"
  printf '\n[[document]]\ncontext = "project-dev"\nscope = "project"\npath = "ADDED.md"\nrequired = true\nwhen = "always"\n' >>"$workspace/AGENT_DOCS.toml"
  if agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session verify --session-id runtime-smoke --product codex \
    --state-home "$state_home" --require-intent project-dev --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.stale.json" 2>&1; then
    echo "runtime-smoke evidence: catalog drift unexpectedly verified" >&2
    return 1
  fi
  if agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session status --session-id missing --product codex --state-home "$state_home" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.missing-session.json" 2>&1; then
    echo "runtime-smoke evidence: missing session unexpectedly found" >&2
    return 1
  fi
  set +e
  agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session status --product codex --state-home "$state_home" --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.omitted-session-id.txt" 2>&1
  omitted_session_status=$?
  set -e
  if [[ "$omitted_session_status" -ne 64 ]]; then
    echo "runtime-smoke evidence: omitted session id returned $omitted_session_status, expected 64" >&2
    return 1
  fi
  grep -q -- '--session-id <ID>' \
    "$EVIDENCE_ARTIFACTS_DIR/agent-docs.omitted-session-id.txt"
  if agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session status --session-id "" --product codex --state-home "$state_home" --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.empty-session-id.json" 2>&1; then
    echo "runtime-smoke evidence: empty session id unexpectedly accepted" >&2
    return 1
  fi
  if agent-docs --docs-home "$workspace" --project-path "$workspace" \
    session status --session-id runtime-smoke --product codex \
    --state-home "$EVIDENCE_ARTIFACTS_DIR/missing-state" --format json \
    >"$EVIDENCE_ARTIFACTS_DIR/agent-docs.missing-state.json" 2>&1; then
    echo "runtime-smoke evidence: missing state unexpectedly found" >&2
    return 1
  fi
  python3 - "$EVIDENCE_ARTIFACTS_DIR" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
cases = (
    ("agent-docs.stale.json", "cli.agent-docs.session.verify.v1", "stale-activation"),
    ("agent-docs.missing-session.json", "cli.agent-docs.session.status.v1", "missing-activation"),
    ("agent-docs.empty-session-id.json", "cli.agent-docs.session.status.v1", "invalid-session-id"),
    ("agent-docs.missing-state.json", "cli.agent-docs.session.status.v1", "missing-activation"),
)
for relative, schema, code in cases:
    body = json.loads((root / relative).read_text())
    assert body["schema_version"] == schema, (relative, body)
    assert body["ok"] is False, (relative, body)
    assert body["error"]["code"] == code, (relative, body)
PY
}

run_parent_workflow_outcome_probe() {
  local out_dir="$EVIDENCE_ARTIFACTS_DIR/parent-workflow"
  local record="$out_dir/skill-usage.record.json"
  local browser_dir="$EVIDENCE_ARTIFACTS_DIR/parent-browser-record"
  local canary_dir="$EVIDENCE_ARTIFACTS_DIR/parent-canary-record"
  local browser_artifact="$browser_dir/local-artifact.txt"
  local request="Repair the feature, check its local web behavior, verify review fixes, and prepare delivery evidence"
  require_evidence_bin skill-usage || return 1
  require_evidence_bin browser-session || return 1
  require_evidence_bin canary-check || return 1
  skill-usage init --help 2>&1 | grep -q -- '--owner-kind'
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/test-first.verify.json"
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/review.verify.json"
  grep -q '"ok": true' "$EVIDENCE_ARTIFACTS_DIR/docs-impact.verify.json"
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/model.verify.json"
  grep -q '"status_code": 200' "$EVIDENCE_ARTIFACTS_DIR/web-evidence.capture.json"
  mkdir -p "$out_dir" "$browser_dir"
  printf 'parent browser outcome artifact\n' >"$browser_artifact"
  browser-session init --out "$browser_dir" --target "file://parent-outcome" \
    --goal "$request" --browser none --format json >"$out_dir/browser.init.json"
  browser-session record-step --out "$browser_dir" \
    --action "checked the controlled local page state" \
    --expectation "the requested local behavior is present" --status pass \
    --artifact "$browser_artifact" --format json >"$out_dir/browser.step.json"
  browser-session verify --out "$browser_dir" --format json >"$out_dir/browser.verify.json"
  grep -q '"complete": true' "$out_dir/browser.verify.json"
  canary-check run --out "$canary_dir" --name parent-local-check \
    --command "printf parent-outcome" --format json >"$out_dir/canary.run.json"
  canary-check verify --out "$canary_dir" --format json >"$out_dir/canary.verify.json"
  grep -q '"status": "pass"' "$out_dir/canary.verify.json"
  skill-usage init --out "$out_dir" --owner-kind workflow \
    --owner-id runtime-smoke.parent-engineering-outcome \
    --intent "complete a governed engineering delivery" \
    --user-request-summary "$request" --trigger project-policy \
    --cwd "$EVIDENCE_WORKSPACE" --format json >"$out_dir/init.json"
  skill-usage link-record --out "$out_dir" --type intent-activation \
    --path "$EVIDENCE_ARTIFACTS_DIR/agent-docs.verify.json" \
    --format json >"$out_dir/link-1.json"
  skill-usage link-record --out "$out_dir" --type test-first \
    --path "$EVIDENCE_ARTIFACTS_DIR/test-first-evidence/test-first-evidence.json" \
    --format json >"$out_dir/link-2.json"
  skill-usage link-record --out "$out_dir" --type rendered-browser \
    --path "$browser_dir/browser-session.json" --format json >"$out_dir/link-3.json"
  skill-usage link-record --out "$out_dir" --type command-canary \
    --path "$canary_dir/canary-check.json" --format json >"$out_dir/link-4.json"
  skill-usage link-record --out "$out_dir" --type static-http \
    --path "$EVIDENCE_ARTIFACTS_DIR/web-evidence/summary.json" \
    --format json >"$out_dir/link-5.json"
  skill-usage link-record --out "$out_dir" --type review \
    --path "$EVIDENCE_ARTIFACTS_DIR/review-evidence/review-evidence.json" \
    --format json >"$out_dir/link-6.json"
  skill-usage link-record --out "$out_dir" --type docs-disposition \
    --path "$EVIDENCE_ARTIFACTS_DIR/docs-impact-record/docs-impact.record.json" \
    --format json >"$out_dir/link-7.json"
  skill-usage link-record --out "$out_dir" --type model-check \
    --path "$EVIDENCE_ARTIFACTS_DIR/model-cross-check/model-cross-check.json" \
    --format json >"$out_dir/link-8.json"
  skill-usage record-validation --out "$out_dir" --command "parent outcome fixture" \
    --status pass --summary "all child records verified in workflow order" \
    --format json >"$out_dir/validation.json"
  skill-usage record-outcome --out "$out_dir" --status pass \
    --summary "engineering delivery fixture completed" --format json >"$out_dir/outcome.json"
  skill-usage verify --out "$out_dir" --format json >"$out_dir/verify.json"
  grep -q '"ok": true' "$out_dir/verify.json"
  python3 - "$record" <<'PY'
import json, sys
record = json.load(open(sys.argv[1], encoding="utf-8"))
owner = record.get("owner") or {}
assert owner.get("kind") == "workflow", owner
linked = record.get("linked_records") or []
assert [item.get("type") for item in linked] == [
    "intent-activation", "test-first", "rendered-browser", "command-canary",
    "static-http", "review", "docs-disposition", "model-check",
], linked
text = " ".join((record.get("intent", ""), record.get("user_request_summary", ""))).lower()
for forbidden in ("agent-docs", "browser-session", "canary-check", "web-evidence", "test-first-evidence", "review-evidence", "skill-usage", "docs-impact", "model-cross-check"):
    assert forbidden not in text, (forbidden, text)
PY
  test "$(find "$EVIDENCE_ARTIFACTS_DIR" -name skill-usage.record.json | wc -l | tr -d ' ')" = 1
}

run_model_cross_check_probe() {
  local out_dir="$EVIDENCE_ARTIFACTS_DIR/model-cross-check"
  local artifact="$EVIDENCE_ARTIFACTS_DIR/model-artifact.txt"
  require_evidence_bin model-cross-check || return 1
  mkdir -p "$out_dir"
  printf 'runtime smoke model cross-check artifact\n' >"$artifact"
  model-cross-check init \
    --out "$out_dir" \
    --prompt "runtime smoke fixture" \
    --primary-model primary-fixture \
    --checker-model checker-fixture \
    --criterion "records both roles without provider calls" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/model.init.json"
  model-cross-check record-observation \
    --out "$out_dir" \
    --role primary \
    --model primary-fixture \
    --verdict pass \
    --summary "primary observation fixture" \
    --artifact "$artifact" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/model.primary.json"
  model-cross-check record-observation \
    --out "$out_dir" \
    --role checker \
    --model checker-fixture \
    --verdict pass \
    --summary "checker observation fixture" \
    --artifact "$artifact" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/model.checker.json"
  model-cross-check verify \
    --out "$out_dir" \
    --format json >"$EVIDENCE_ARTIFACTS_DIR/model.verify.json"
  grep -q '"schema_version": "cli.model-cross-check.verify.v1"' "$EVIDENCE_ARTIFACTS_DIR/model.verify.json"
  grep -q '"ok": true' "$EVIDENCE_ARTIFACTS_DIR/model.verify.json"
  grep -q '"complete": true' "$EVIDENCE_ARTIFACTS_DIR/model.verify.json"
}

failures=0
record_case "evidence.web-evidence" "web-evidence captured local loopback HTTP fixture" run_web_evidence_probe
record_case "evidence.test-first-evidence" "test-first evidence waiver and final validation verified" run_test_first_evidence_probe
record_case "evidence.review-evidence" "review evidence finding and validation verified" run_review_evidence_probe
record_case "evidence.docs-impact" "docs-impact classified controlled untracked docs fixture" run_docs_impact_probe
record_case "evidence.model-cross-check" "model cross-check recorded primary and checker observations without provider calls" run_model_cross_check_probe
record_case "evidence.selective-control-plane" "pinned durable sessions and phase-aware pre-edit transitions passed" run_selective_intent_control_plane_probe
record_case "evidence.skill-usage" "one natural-language parent workflow owned ordered verified child evidence" run_parent_workflow_outcome_probe

exit "$failures"
