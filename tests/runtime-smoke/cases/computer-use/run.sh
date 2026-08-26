#!/usr/bin/env bash
# Deterministic probes for the direct macos-agent adapter skill contract.
# Functions are passed by name to the shared results harness.
# shellcheck disable=SC2317

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

CASE_ROOT="$TMP_ROOT/computer-use"
FAKE_BIN="$CASE_ROOT/bin"
CASE_ARTIFACTS="$ARTIFACTS_DIR/computer-use"
mkdir -p "$FAKE_BIN" "$CASE_ARTIFACTS"
REAL_MACOS_AGENT="$(command -v macos-agent || true)"

make_fake_macos_agent() {
  cat >"$FAKE_BIN/macos-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

write_journal() {
  local out_dir="$1"
  local command="$2"
  local transport="$3"
  local evidence_mode="$4"
  local status="$5"
  local failure_class="$6"
  local tool_profile="${7:-}"
  local tool_profile_json=""
  local backend_digest="${COMPUTER_USE_TEST_BACKEND_DIGEST:-sha256:synthetic}"
  local sequence=1
  local step_id=""

  local replay_class=safe
  local replay_argv='["see"]'
  local failure_json=null
  if [[ "$evidence_mode" == sensitive || "$status" != passed ]]; then
    replay_class=never
    replay_argv=null
  fi
  if [[ "$failure_class" != none ]]; then
    failure_json='"'"$failure_class"'"'
  fi
  if [[ -n "$tool_profile" ]]; then
    tool_profile_json=',"tool_profile":"'"$tool_profile"'"'
  fi
  if [[ -s "$out_dir/steps.jsonl" ]]; then
    sequence="$(( $(wc -l <"$out_dir/steps.jsonl") + 1 ))"
  fi
  printf -v step_id 'step-%06d' "$sequence"
  JOURNAL_STEP_ID="$step_id"

  mkdir -p "$out_dir/artifacts"
  printf '%s\n' "{\"schema_version\":\"macos-agent.journal.v2\",\"run_id\":\"synthetic-run\",\"adapter_version\":\"1.27.3\",\"peekaboo_tag\":\"v4.2.2\",\"peekaboo_commit\":\"05675b0b5e2c382146963e19493787d9dac0d45b\",\"backend_digest\":\"$backend_digest\",\"runtime\":\"app\",\"transport\":\"$transport\",\"evidence_mode\":\"$evidence_mode\"${tool_profile_json},\"started_at\":\"2026-08-23T00:00:00Z\",\"closed_at\":\"2026-08-23T00:00:01Z\",\"state\":\"closed\"}" >"$out_dir/manifest.json"
  printf '%s\n' '{"schema_version":"macos-agent.journal-step.v2","sequence":'"$sequence"',"id":"'"$step_id"'","correlation_id":"correlation-'"$(printf '%06d' "$sequence")"'","recorded_at":"2026-08-23T00:00:00Z","command":"'"$command"'","argv_shape":["fixture"],"replay_argv":'"$replay_argv"',"backend_digest":"'"$backend_digest"'","runtime":"app","transport":"'"$transport"'","status":"'"$status"'","failure_class":'"$failure_json"',"duration_ms":1,"retries":0,"replay_class":"'"$replay_class"'"}' >>"$out_dir/steps.jsonl"
  local total_steps passed_steps failed_steps policy_blocked_steps
  total_steps="$(wc -l <"$out_dir/steps.jsonl")"
  passed_steps="$(grep -c '"status":"passed"' "$out_dir/steps.jsonl" || true)"
  failed_steps="$(grep -c '"status":"failed"' "$out_dir/steps.jsonl" || true)"
  policy_blocked_steps="$(grep -c '"status":"policy_blocked"' "$out_dir/steps.jsonl" || true)"
  printf '%s\n' '{"schema_version":"macos-agent.artifact-index.v1","artifacts":[]}' >"$out_dir/artifacts/index.json"
  printf '%s\n' '{"schema_version":"macos-agent.journal-summary.v1","total_steps":'"$total_steps"',"passed":'"$passed_steps"',"failed":'"$failed_steps"',"unknown":0,"policy_blocked":'"$policy_blocked_steps"',"failure_signatures":[],"replay_candidates":[],"defect_candidates":[],"assertions":[],"residual_user_actions":[],"recovered_tail":false}' >"$out_dir/summary.json"
  printf '%s\n' '{"schema_version":"macos-agent.redaction.v1","rules":[],"suppressed_fields":[],"failures":[],"private_identifier_matches":0,"secret_matches":0}' >"$out_dir/redaction.json"
}

assert_compatible_journal() {
  local out_dir="$1"
  local transport="$2"
  local evidence_mode="$3"
  local tool_profile="${4:-}"
  if [[ ! -e "$out_dir/manifest.json" ]]; then
    return 0
  fi
  if ! python3 - "$out_dir/manifest.json" "$transport" "$evidence_mode" "$tool_profile" <<'PY'
import json
import pathlib
import sys

manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_profile = sys.argv[4] or None
expected_digest = "sha256:changed" if __import__("os").environ.get("COMPUTER_USE_TEST_BACKEND_DIGEST") == "sha256:changed" else "sha256:synthetic"
assert manifest["runtime"] == "app"
assert manifest["transport"] == sys.argv[2]
assert manifest["evidence_mode"] == sys.argv[3]
assert manifest.get("tool_profile") == expected_profile
assert manifest["backend_digest"] == expected_digest
PY
  then
    printf '%s\n' 'error: journal manifest does not match this execution session' >&2
    exit 74
  fi
}

args=()
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --format | --error-format)
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done
set -- "${args[@]}"

command="${1:-}"
shift || true
case "$command" in
  backend)
    test "${1:-}" = status
    printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"backend.status","result":{"locked_tag":"v4.2.2","locked_commit":"05675b0b5e2c382146963e19493787d9dac0d45b","strict":false,"security_posture":"full","cli_notarization_policy":"required","installed":true,"verified":true,"current":{"tag":"v4.2.2","commit":"05675b0b5e2c382146963e19493787d9dac0d45b","installed_at":"2026-08-23T00:00:00Z"},"previous":null,"app_owned":true,"dry_run":false}}'
    ;;
  capabilities)
    printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"capabilities","result":{"transport":["local","ssh"],"interfaces":["exec","mcp_stdio"],"runtime":["app","daemon","auto","process"],"tool_profiles":["observe","interact","extended"],"disabled":["agent","analyze","audio","browser","clipboard","config","credentials","http_mcp","image","mcp_agent","permission_mutation","shell","sse_mcp"]}}'
    ;;
  doctor)
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --host)
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"doctor","result":{"locked_tag":"v4.2.2","strict":true,"ready":true,"backend":{"locked_tag":"v4.2.2","active_tag":"v4.2.2","rollback_active":false,"strict":true,"security_posture":"full","ready":true,"checks":[{"id":"notary","status":"pass","message":"required notarization passed"}]},"runtime":{"id":"runtime","status":"pass","message":"ready"},"permissions":{"id":"permissions","status":"pass","message":"ready"},"bridge":{"id":"bridge","status":"pass","message":"ready"},"capabilities":[]}}'
    ;;
  exec)
    out_dir=""
    transport=local
    evidence_mode=minimal
    expected=""
    intent=""
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --host)
          transport=ssh
          shift 2
          ;;
        --out-dir)
          out_dir="$2"
          shift 2
          ;;
        --evidence-mode)
          evidence_mode="$2"
          shift 2
          ;;
        --intent)
          intent="$2"
          shift 2
          ;;
        --runtime | --timeout-seconds)
          shift 2
          ;;
        --expected)
          expected="$2"
          shift 2
          ;;
        --)
          shift
          break
          ;;
        *)
          shift
          ;;
      esac
    done
    test -n "$out_dir"
    assert_compatible_journal "$out_dir" "$transport" "$evidence_mode"
    upstream_command="${1:-unknown}"
    case "$upstream_command" in
      action | click | type | press | scroll | drag | move | set-value | window | app | menu | dialog | dock | space | capture | paste)
        if [[ -z "$expected" ]]; then
          printf '%s\n' 'error: mutating command requires an observable --expected postcondition' >&2
          exit 78
        fi
        ;;
    esac
    if [[ "$intent" == 'Exercise synthetic wrong-target handling' ]]; then
      write_journal "$out_dir" "exec.$upstream_command" "$transport" "$evidence_mode" failed wrong_target
      printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"exec","result":{"transport":"'"$transport"'","runtime":"app","evidence_mode":"'"$evidence_mode"'","journal_step":"'"$JOURNAL_STEP_ID"'","upstream":{"exit_code":9,"timed_out":false,"stdout_truncated":false,"stderr_truncated":false,"diagnostic":"synthetic exec stopped after a significant wrong-target failure"}}}'
      exit 70
    fi
    write_journal "$out_dir" "exec.$upstream_command" "$transport" "$evidence_mode" passed none
    printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"exec","result":{"transport":"'"$transport"'","runtime":"app","evidence_mode":"'"$evidence_mode"'","journal_step":"'"$JOURNAL_STEP_ID"'","upstream":{"exit_code":0,"timed_out":false,"stdout_truncated":false,"stderr_truncated":false,"json":{"success":true}}}}'
    ;;
  mcp)
    out_dir=""
    transport=local
    profile=interact
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --host)
          transport=ssh
          shift 2
          ;;
        --out-dir)
          out_dir="$2"
          shift 2
          ;;
        --tool-profile)
          profile="$2"
          shift 2
          ;;
        --runtime)
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    assert_compatible_journal "$out_dir" "$transport" sensitive "$profile"
    input="$(cat)"
    case "$profile" in
      observe)
        tools_json='[{"name":"see"},{"name":"inspect_ui"},{"name":"permissions"},{"name":"sleep"},{"name":"verify_state"}]'
        ;;
      interact)
        tools_json='[{"name":"see"},{"name":"inspect_ui"},{"name":"permissions"},{"name":"sleep"},{"name":"verify_state"},{"name":"click"},{"name":"type"},{"name":"press"},{"name":"scroll"},{"name":"drag"},{"name":"move"},{"name":"set_value"},{"name":"action"},{"name":"window"},{"name":"app"},{"name":"menu"}]'
        ;;
      extended)
        tools_json='[{"name":"see"},{"name":"inspect_ui"},{"name":"permissions"},{"name":"sleep"},{"name":"verify_state"},{"name":"click"},{"name":"type"},{"name":"press"},{"name":"scroll"},{"name":"drag"},{"name":"move"},{"name":"set_value"},{"name":"action"},{"name":"window"},{"name":"app"},{"name":"menu"},{"name":"dialog"},{"name":"dock"},{"name":"space"},{"name":"capture"},{"name":"paste"}]'
        ;;
    esac
    if [[ "$input" == *'"name":"shell"'* ]]; then
      write_journal "$out_dir" mcp.tools_call "$transport" sensitive policy_blocked policy "$profile"
      printf '%s\n' \
        '{"jsonrpc":"2.0","id":1,"error":{"code":-32001,"message":"tool denied by adapter profile"}}' \
        '{"jsonrpc":"2.0","id":2,"result":{"tools":'"$tools_json"'}}'
      exit 0
    fi
    write_journal "$out_dir" mcp "$transport" sensitive passed none "$profile"
    printf '%s\n' '{"jsonrpc":"2.0","id":2,"result":{"tools":'"$tools_json"'}}'
    ;;
  journal)
    journal_command="${1:-}"
    shift || true
    out_dir=""
    while [[ "$#" -gt 0 ]]; do
      case "$1" in
        --out-dir)
          out_dir="$2"
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    test -s "$out_dir/manifest.json"
    case "$journal_command" in
      summarize)
        printf '%s' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"journal.summarize","result":'
        cat "$out_dir/summary.json"
        printf '}\n'
        ;;
      review)
        failed_step="$(grep '"status":"failed"' "$out_dir/steps.jsonl" | tail -1 | sed -E 's/.*"id":"([^"]+)".*/\1/')"
        review='{"schema_version":"macos-agent.journal-review.v1","candidates":[{"signature":"exec.click:wrong_target","count":1,"significant":true,"proposed_owner":"runtime_skill_policy","step_ids":["'"$failed_step"'"]}],"clean":false}'
        printf '%s\n' "$review" >"$out_dir/review.json"
        printf '%s\n' '{"schema_version":"macos-agent.adapter.v3","ok":true,"command":"journal.review","result":'"$review"'}'
        ;;
      replay-plan)
        python3 - "$out_dir/steps.jsonl" "$out_dir/manifest.json" <<'PY'
import json
import pathlib
import sys

steps = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
manifest = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
rows = []
for step in steps:
    replay_class = step["replay_class"]
    if replay_class == "never":
        eligible, reason = False, "never"
    elif manifest["transport"] == "ssh":
        eligible, reason = False, "remote journal replay is not supported"
    else:
        eligible, reason = True, "eligible"
    rows.append({"id": step["id"], "replay_class": replay_class, "eligible": eligible, "reason": reason})
print(json.dumps({"schema_version":"macos-agent.adapter.v3","ok":True,"command":"journal.replay-plan","result":{"steps":rows}}, separators=(",", ":")))
PY
        ;;
      *)
        exit 64
        ;;
    esac
    ;;
  *)
    exit 64
    ;;
esac
SH
  chmod +x "$FAKE_BIN/macos-agent"
}

assert_journal() {
  local out_dir="$1"
  test -s "$out_dir/manifest.json"
  test -s "$out_dir/steps.jsonl"
  test -s "$out_dir/artifacts/index.json"
  test -s "$out_dir/summary.json"
  test -s "$out_dir/redaction.json"
  python3 - "$out_dir" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
expected = {
    "manifest.json": "macos-agent.journal.v2",
    "artifacts/index.json": "macos-agent.artifact-index.v1",
    "summary.json": "macos-agent.journal-summary.v1",
    "redaction.json": "macos-agent.redaction.v1",
}
for relative, schema in expected.items():
    payload = json.loads((root / relative).read_text(encoding="utf-8"))
    assert payload["schema_version"] == schema, (relative, payload)
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
assert manifest["state"] == "closed", manifest
for field in ("backend_digest", "runtime", "transport", "evidence_mode", "started_at", "closed_at"):
    assert field in manifest, (field, manifest)
step = json.loads((root / "steps.jsonl").read_text(encoding="utf-8").splitlines()[0])
assert step["schema_version"] == "macos-agent.journal-step.v2", step
for field in ("id", "command", "transport", "status", "replay_class"):
    assert field in step, (field, step)
PY
}

run_direct_adapter_probe() {
  make_fake_macos_agent
  test -x "$REAL_MACOS_AGENT"

  local local_out="$CASE_ROOT/local"
  local remote_out="$CASE_ROOT/remote"
  local mutation_out="$CASE_ROOT/mutation"
  local sensitive_out="$CASE_ROOT/sensitive"
  local failed_flow_out="$CASE_ROOT/failed-flow"
  local mcp_out="$CASE_ROOT/mcp"
  local secret='SYNTHETIC_SECRET_CANARY_7f90'

  "$REAL_MACOS_AGENT" capabilities --format json >"$CASE_ARTIFACTS/capabilities.json"
  python3 - "$CASE_ARTIFACTS/capabilities.json" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["schema_version"] == "macos-agent.adapter.v3", payload
assert payload["command"] == "capabilities", payload
result = payload["result"]
assert result["transport"] == ["local", "ssh"], result
assert result["interfaces"] == ["exec", "mcp_stdio"], result
assert result["runtime"] == ["app", "daemon", "auto", "process"], result
assert result["tool_profiles"] == ["observe", "interact", "extended"], result
for denied in ("browser", "permission_mutation", "shell", "http_mcp", "sse_mcp"):
    assert denied in result["disabled"], (denied, result)
PY

  PATH="$FAKE_BIN:$PATH" macos-agent backend status --format json >"$CASE_ARTIFACTS/backend-status.json"
  python3 - "$CASE_ARTIFACTS/backend-status.json" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["schema_version"] == "macos-agent.adapter.v3", payload
assert payload["command"] == "backend.status", payload
result = payload["result"]
assert set(result) == {
    "locked_tag", "locked_commit", "strict", "security_posture",
    "cli_notarization_policy", "installed", "verified", "current",
    "previous", "app_owned", "dry_run",
}, result
assert result["verified"] is True, result
assert result["security_posture"] == "full", result
assert set(result["current"]) == {"tag", "commit", "installed_at"}, result
PY

  PATH="$FAKE_BIN:$PATH" macos-agent doctor --strict --format json >"$CASE_ARTIFACTS/local-doctor.json"
  PATH="$FAKE_BIN:$PATH" macos-agent doctor --host example-mac --strict --format json >"$CASE_ARTIFACTS/remote-doctor.json"
  python3 - "$CASE_ARTIFACTS/local-doctor.json" "$CASE_ARTIFACTS/remote-doctor.json" <<'PY'
import json
import pathlib
import sys

for path in sys.argv[1:]:
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "macos-agent.adapter.v3", payload
    assert payload["command"] == "doctor", payload
    result = payload["result"]
    assert set(result) == {
        "locked_tag", "strict", "ready", "backend", "runtime",
        "permissions", "bridge", "capabilities",
    }, result
    assert "transport" not in result, result
    assert set(result["backend"]) == {
        "locked_tag", "active_tag", "rollback_active", "strict",
        "security_posture", "ready", "checks",
    }, result["backend"]
    checks = [result["runtime"], result["permissions"], result["bridge"], *result["capabilities"], *result["backend"]["checks"]]
    assert all(set(check) == {"id", "status", "message"} for check in checks), checks
    assert all(check["status"] == "pass" for check in checks), checks
PY

  PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$local_out" --intent 'Inspect the synthetic app' --runtime app -- see --app 'Synthetic App' --json >"$CASE_ARTIFACTS/local-exec.json"
  PATH="$FAKE_BIN:$PATH" macos-agent exec --host example-mac --out-dir "$remote_out" --intent 'Inspect the synthetic app remotely' --runtime app -- see --app 'Synthetic App' --json >"$CASE_ARTIFACTS/remote-exec.json"
  python3 - "$CASE_ARTIFACTS/local-exec.json" "$CASE_ARTIFACTS/remote-exec.json" <<'PY'
import json
import pathlib
import sys

for path in sys.argv[1:]:
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "macos-agent.adapter.v3", payload
    assert payload["command"] == "exec", payload
    result = payload["result"]
    assert set(result) == {"transport", "runtime", "evidence_mode", "journal_step", "upstream"}, result
    assert set(result["upstream"]) == {
        "exit_code", "timed_out", "stdout_truncated", "stderr_truncated", "json",
    }, result["upstream"]
PY
  assert_journal "$local_out"
  assert_journal "$remote_out"
  grep -q '"transport":"local"' "$local_out/manifest.json"
  grep -q '"transport":"ssh"' "$remote_out/manifest.json"
  if PATH="$FAKE_BIN:$PATH" macos-agent mcp --out-dir "$local_out" --tool-profile interact --runtime app >"$CASE_ARTIFACTS/mixed-exec-mcp.stdout.txt" 2>"$CASE_ARTIFACTS/mixed-exec-mcp.stderr.txt"; then
    return 1
  fi
  grep -q 'journal manifest does not match this execution session' "$CASE_ARTIFACTS/mixed-exec-mcp.stderr.txt"
  if PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$local_out" --intent 'Change evidence mode' --evidence-mode sensitive -- see --app 'Synthetic App' --json >"$CASE_ARTIFACTS/mixed-evidence.stdout.txt" 2>"$CASE_ARTIFACTS/mixed-evidence.stderr.txt"; then
    return 1
  fi
  grep -q 'journal manifest does not match this execution session' "$CASE_ARTIFACTS/mixed-evidence.stderr.txt"
  if COMPUTER_USE_TEST_BACKEND_DIGEST=sha256:changed PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$local_out" --intent 'Reuse after backend change' --runtime app -- see --app 'Synthetic App' --json >"$CASE_ARTIFACTS/mixed-backend.stdout.txt" 2>"$CASE_ARTIFACTS/mixed-backend.stderr.txt"; then
    return 1
  fi
  grep -q 'journal manifest does not match this execution session' "$CASE_ARTIFACTS/mixed-backend.stderr.txt"
  PATH="$FAKE_BIN:$PATH" macos-agent journal replay-plan --out-dir "$remote_out" --format json >"$CASE_ARTIFACTS/remote-replay-plan.json"
  python3 - "$CASE_ARTIFACTS/remote-replay-plan.json" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
row = payload["result"]["steps"][0]
assert row["replay_class"] == "safe", row
assert row["eligible"] is False, row
assert "remote" in row["reason"], row
PY

  if PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$mutation_out" -- click --app 'Synthetic App' --on Submit --json >"$CASE_ARTIFACTS/unguarded-mutation.stdout.txt" 2>"$CASE_ARTIFACTS/unguarded-mutation.stderr.txt"; then
    return 1
  fi
  grep -q 'observable --expected postcondition' "$CASE_ARTIFACTS/unguarded-mutation.stderr.txt"

  PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$mutation_out" --intent 'Submit the synthetic fixture' --expected 'The fixture reports submitted' --runtime app -- click --app 'Synthetic App' --on Submit --json >"$CASE_ARTIFACTS/guarded-mutation.json"
  assert_journal "$mutation_out"

  PATH="$FAKE_BIN:$PATH" macos-agent exec --out-dir "$sensitive_out" --intent 'Enter a private synthetic value' --expected 'The private fixture reports populated' --evidence-mode sensitive -- type --app 'Synthetic App' --text "$secret" --json >"$CASE_ARTIFACTS/sensitive-exec.json"
  assert_journal "$sensitive_out"
  grep -q '"evidence_mode":"sensitive"' "$sensitive_out/manifest.json"
  PATH="$FAKE_BIN:$PATH" macos-agent journal replay-plan --out-dir "$sensitive_out" --format json >"$CASE_ARTIFACTS/sensitive-replay-plan.json"
  grep -q '"replay_class":"never"' "$CASE_ARTIFACTS/sensitive-replay-plan.json"

  PATH="$FAKE_BIN:$PATH" macos-agent exec --host example-mac --out-dir "$failed_flow_out" --intent 'Observe before the synthetic flow mutation' --runtime app -- see --app 'Synthetic App' --json >"$CASE_ARTIFACTS/failed-flow-observe.json"
  if PATH="$FAKE_BIN:$PATH" macos-agent exec --host example-mac --out-dir "$failed_flow_out" --intent 'Exercise synthetic wrong-target handling' --expected 'The synthetic target changes' --runtime app -- click --app 'Synthetic App' --on Missing --json >"$CASE_ARTIFACTS/failed-flow.json" 2>"$CASE_ARTIFACTS/failed-flow.stderr.txt"; then
    return 1
  fi
  test ! -s "$CASE_ARTIFACTS/failed-flow.stderr.txt"
  python3 - "$CASE_ARTIFACTS/failed-flow.json" <<'PY'
import json
import pathlib
import sys

payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["schema_version"] == "macos-agent.adapter.v3", payload
assert payload["command"] == "exec", payload
result = payload["result"]
assert set(result) == {"transport", "runtime", "evidence_mode", "journal_step", "upstream"}, result
assert set(result["upstream"]) == {
    "exit_code", "timed_out", "stdout_truncated", "stderr_truncated", "diagnostic",
}, result["upstream"]
assert result["upstream"]["exit_code"] != 0, result
assert result["journal_step"] == "step-000002", result
PY
  assert_journal "$failed_flow_out"
  PATH="$FAKE_BIN:$PATH" macos-agent journal summarize --out-dir "$failed_flow_out" --format json >"$CASE_ARTIFACTS/failed-flow-summary.json"
  PATH="$FAKE_BIN:$PATH" macos-agent journal review --out-dir "$failed_flow_out" --format json >"$CASE_ARTIFACTS/failed-flow-review.json"
  PATH="$FAKE_BIN:$PATH" macos-agent journal replay-plan --out-dir "$failed_flow_out" --format json >"$CASE_ARTIFACTS/failed-flow-replay-plan.json"
  python3 - "$failed_flow_out/steps.jsonl" "$CASE_ARTIFACTS/failed-flow-summary.json" "$CASE_ARTIFACTS/failed-flow-review.json" "$CASE_ARTIFACTS/failed-flow-replay-plan.json" <<'PY'
import json
import pathlib
import sys

steps = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
assert [(row["id"], row["command"], row["status"], row["replay_class"]) for row in steps] == [
    ("step-000001", "exec.see", "passed", "safe"),
    ("step-000002", "exec.click", "failed", "never"),
], steps
summary = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))["result"]
assert (summary["total_steps"], summary["passed"], summary["failed"]) == (2, 1, 1), summary
review = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))["result"]
assert review["candidates"][0]["step_ids"] == ["step-000002"], review
plan = json.loads(pathlib.Path(sys.argv[4]).read_text(encoding="utf-8"))["result"]["steps"]
assert [(row["id"], row["replay_class"], row["eligible"]) for row in plan] == [
    ("step-000001", "safe", False),
    ("step-000002", "never", False),
], plan
PY
  grep -q '"significant":true' "$CASE_ARTIFACTS/failed-flow-review.json"
  grep -q '"proposed_owner":"runtime_skill_policy"' "$CASE_ARTIFACTS/failed-flow-review.json"
  if grep -q '"provider_mutation"' "$CASE_ARTIFACTS/failed-flow-review.json"; then
    return 1
  fi

  for profile in observe interact extended; do
    PATH="$FAKE_BIN:$PATH" macos-agent mcp --out-dir "$mcp_out-$profile" --tool-profile "$profile" --runtime app >"$CASE_ARTIFACTS/mcp-$profile.json"
    python3 - "$CASE_ARTIFACTS/mcp-$profile.json" "$profile" <<'PY'
import json
import pathlib
import sys

frames = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
assert frames, "MCP emitted no JSON-RPC frames"
assert all(frame.get("jsonrpc") == "2.0" for frame in frames), frames
assert all(frame.get("schema_version") != "macos-agent.adapter.v3" for frame in frames), frames
actual = [tool["name"] for tool in frames[-1]["result"]["tools"]]
observe = ["see", "inspect_ui", "permissions", "sleep", "verify_state"]
interact = observe + ["click", "type", "press", "scroll", "drag", "move", "set_value", "action", "window", "app", "menu"]
extended = interact + ["dialog", "dock", "space", "capture", "paste"]
expected = {"observe": observe, "interact": interact, "extended": extended}[sys.argv[2]]
assert actual == expected, (sys.argv[2], actual)
for retired in ("hotkey", "swipe", "scenario", "shell"):
    assert retired not in actual, (retired, actual)
PY
    assert_journal "$mcp_out-$profile"
  done
  printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"shell","arguments":{}}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' |
    PATH="$FAKE_BIN:$PATH" macos-agent mcp --out-dir "$mcp_out-denied" --tool-profile extended >"$CASE_ARTIFACTS/mcp-denied.stdout.txt" 2>"$CASE_ARTIFACTS/mcp-denied.stderr.txt"
  test ! -s "$CASE_ARTIFACTS/mcp-denied.stderr.txt"
  python3 - "$CASE_ARTIFACTS/mcp-denied.stdout.txt" <<'PY'
import json
import pathlib
import sys

frames = [json.loads(line) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
assert len(frames) == 2, frames
assert frames[0]["id"] == 1 and frames[0]["error"]["code"] == -32001, frames
assert frames[1]["id"] == 2 and "result" in frames[1], frames
PY
  grep -q '"status":"policy_blocked"' "$mcp_out-denied/steps.jsonl"

  if rg -n --fixed-strings "$secret" "$CASE_ROOT" "$CASE_ARTIFACTS"; then
    return 1
  fi
  if rg -n 'example-mac|/home/|/Users/|HostName|IdentityFile|BEGIN OPENSSH PRIVATE KEY' \
    "$local_out" "$remote_out" "$mutation_out" "$sensitive_out" "$failed_flow_out" "$mcp_out"-* "$CASE_ARTIFACTS"; then
    return 1
  fi
}

assert_homogeneous_run_contract() {
  local skill="$1"

  grep -Fq 'for one interface and' "$skill"
  grep -Fq 'backend_digest, runtime, transport, evidence_mode,' "$skill"
  grep -Fq '512-step journal rotation bound' "$skill"
  grep -Fq "exec_out=\"\$session_root/local-exec-minimal-app\"" "$skill"
  grep -Fq "flow_out=\"\$session_root/local-flow-minimal-app\"" "$skill"
  grep -Fq "mcp_out=\"\$session_root/local-mcp-sensitive-app-observe\"" "$skill"
  grep -Fq "mkdir -p \"\$exec_out\"" "$skill"
  grep -Fq "mkdir -p \"\$flow_out\"" "$skill"
  grep -Fq "mkdir -p \"\$mcp_out\"" "$skill"
  grep -Fq "run_out=\"\$exec_out\"" "$skill"
  grep -Fq "journal summarize --out-dir \"\$run_out\"" "$skill"
  grep -Fq "journal review --out-dir \"\$run_out\"" "$skill"
  grep -Fq "journal replay-plan --out-dir \"\$run_out\"" "$skill"
  python3 - "$skill" <<'PY'
import pathlib
import sys

text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
required_counts = {
    "or after any backend install, rollback, or\nreplacement:": 1,
    'macos-agent exec \\\n  --out-dir "$exec_out" \\\n  --intent "Inspect Calculator controls" \\': 1,
    'macos-agent exec \\\n  --out-dir "$exec_out" \\\n  --intent "Clear Calculator" \\\n  --expected "Calculator display is zero" \\': 1,
    'macos-agent exec \\\n  --out-dir "$flow_out" \\\n  --intent "Observe the first flow state" \\': 1,
    'macos-agent exec \\\n  --out-dir "$flow_out" \\\n  --intent "Perform the reviewed next step" \\': 1,
    'macos-agent mcp --out-dir "$mcp_out" --runtime app --tool-profile observe': 1,
    'macos-agent journal replay-step \\\n  --out-dir "$run_out" \\': 1,
}
for required, expected_count in required_counts.items():
    assert text.count(required) == expected_count, (required, text.count(required))
PY
}

run_skill_and_matrix_contract_probe() {
  local skill="$REPO_ROOT/core/skills/computer-use/macos-desktop/SKILL.md.tera"
  local setup="$REPO_ROOT/core/skills/computer-use/macos-desktop/references/setup.md"
  local matrix="$REPO_ROOT/docs/source/macos-agent-capability-matrix.md"

  test ! -e "$REPO_ROOT/core/skills/computer-use/macos-desktop/bin/macos_desktop.py"
  test ! -e "$REPO_ROOT/core/skills/computer-use/macos-desktop/scripts/macos-desktop.sh"

  grep -Fq 'macos-agent backend install' "$skill"
  grep -Fq 'macos-agent doctor' "$skill"
  grep -Fq 'macos-agent exec' "$skill"
  grep -Fq 'Peekaboo v4 removed the `.peekaboo.json` runner.' "$skill"
  if grep -Fq 'macos-agent scenario' "$skill"; then
    return 1
  fi
  grep -Fq 'macos-agent mcp' "$skill"
  grep -Fq 'macos-agent journal summarize' "$skill"
  grep -Fq 'macos-agent journal review' "$skill"
  grep -Fq 'cold app-runtime state,' "$skill"
  grep -Fq 'not a terminal blocker.' "$skill"
  grep -Fq 'Bootstrap it autonomously with one bounded read-only' "$skill"
  grep -Fq 'rerun strict doctor and capabilities before any mutation' "$skill"
  assert_homogeneous_run_contract "$skill"
  grep -Fq 'Never create an issue automatically' "$skill"
  grep -Fq 'docs/source/macos-agent-capability-matrix.md' "$skill"
  if grep -Fq 'macos-desktop.sh' "$skill"; then
    return 1
  fi
  if grep -Fq 'Python' "$skill"; then
    return 1
  fi

  grep -Fq 'macos-agent backend install --strict --format json' "$setup"
  grep -Fq 'Cold GUI Bridge Recovery' "$setup"
  grep -Fq 'Do not reinstall' "$setup"
  grep -Fq 'an already verified backend for this state.' "$setup"
  if grep -Eq 'brew install .*peekaboo|npx .*peekaboo|latest' "$setup"; then
    return 1
  fi

  test -s "$matrix"
  for status in supported adapter optional disabled unsupported; do
    grep -Eq "\\| ${status} \\|" "$matrix"
  done
  for capability in 'Local / SSH execution' 'Execution journal' 'MCP stdio' 'MCP HTTP/SSE' 'Browser DOM/CDP' 'Locked/logged-out desktop'; do
    grep -Fq "$capability" "$matrix"
  done
  grep -Fq 'Evidence' "$matrix"
  grep -Fq 'As of `v1.27.3`' "$REPO_ROOT/docs/source/nils-cli-surface.md"
  grep -Fq 'guarded multi-step flows' "$REPO_ROOT/core/skills/README.md"
  grep -Fq 'guarded exec-flow postconditions' "$REPO_ROOT/manifests/skill-dispositions.yaml"
  if rg -n 'retaining screenshots, scenarios|scenario assertions' \
    "$REPO_ROOT/core/skills/README.md" \
    "$REPO_ROOT/manifests/skill-dispositions.yaml"; then
    return 1
  fi
  if rg -n 'reduced distribution posture|may remain non-blocking' "$skill"; then
    return 1
  fi

  for product in codex claude hermes; do
    rendered_contract_prepare_product "$product"
    rendered="$REPO_ROOT/build/$product/plugins/computer-use/skills/macos-desktop/SKILL.md"
    expected_root="$REPO_ROOT/tests/golden/$product/plugins/computer-use/skills/macos-desktop/expected"
    test -s "$rendered"
    grep -Fq 'macos-agent exec' "$rendered"
    assert_homogeneous_run_contract "$rendered"
    if grep -Fq 'macos-desktop.sh' "$rendered"; then
      return 1
    fi
    test ! -e "$REPO_ROOT/build/$product/plugins/computer-use/skills/macos-desktop/bin/macos_desktop.py"
    test ! -e "$REPO_ROOT/build/$product/plugins/computer-use/skills/macos-desktop/scripts/macos-desktop.sh"
    (
      cd "$(dirname "$rendered")"
      find . -type f -print | sort
    ) >"$CASE_ARTIFACTS/$product-rendered-files.txt"
    (
      cd "$expected_root"
      find . -type f -print | sort
    ) >"$CASE_ARTIFACTS/$product-golden-files.txt"
    diff -u "$CASE_ARTIFACTS/$product-rendered-files.txt" "$CASE_ARTIFACTS/$product-golden-files.txt"
  done
}

assert_surface_routing_contract() {
  local skill="$1"

  # Deterministic-first surface selection ladder.
  grep -Fq '## Surface Selection' "$skill"
  grep -Fq 'Prefer the most deterministic surface that can prove the outcome' "$skill"
  grep -Fq 'App Intents / Shortcuts' "$skill"
  grep -Fq 'Scripting dictionary' "$skill"
  grep -Fq 'run outside the adapter' "$skill"
  grep -Fq 'shell remains hard-disabled' "$skill"
  grep -Fq 'State the selected rung' "$skill"

  # Reciprocal browser-test handoff; this skill still claims no DOM capability.
  grep -Fq 'browser-test' "$skill"
  grep -Fq 'DOM, selector, or rendered-page claim' "$skill"
  grep -Fq 'owns signed-in session state' "$skill"

  # Accessibility-degeneracy gate before mutation.
  grep -Fq '## Accessibility Health Gate' "$skill"
  grep -Fq 'Judge accessibility health before the first mutation' "$skill"
  grep -Fq 'degenerate' "$skill"
  grep -Fq 'Continuing to probe a degenerate tree is a false-success risk' "$skill"

  # Declarative rerunnable flow fixtures.
  grep -Fq 'references/flow-fixtures.md' "$skill"
  grep -Fq 'is not the rerun mechanism' "$skill"

  # Stability convergence threshold in the acceptance standard.
  grep -Fq 'independent runs' "$skill"
  grep -Fq 'postcondition success rate' "$skill"
  grep -Fq 'unattended-safe' "$skill"

  # The ladder must not reintroduce retired or hard-denied mechanics.
  if grep -Fq 'macos-agent scenario' "$skill"; then
    return 1
  fi
}

run_surface_routing_contract_probe() {
  local skill="$REPO_ROOT/core/skills/computer-use/macos-desktop/SKILL.md.tera"
  local fixtures="$REPO_ROOT/core/skills/computer-use/macos-desktop/references/flow-fixtures.md"
  local matrix="$REPO_ROOT/docs/source/macos-agent-capability-matrix.md"
  local routing="$REPO_ROOT/core/policies/browser-test-routing.md"
  local pin="$REPO_ROOT/docs/source/nils-cli-pin.yaml"
  local surface="$REPO_ROOT/docs/source/nils-cli-surface.md"
  local product rendered

  assert_surface_routing_contract "$skill"

  # The flow-fixture reference exists, defines the shape, and keeps the runner
  # on the already-published chained exec mechanics.
  test -s "$fixtures"
  grep -Fq 'expected:' "$fixtures"
  grep -Fq 'steps:' "$fixtures"
  grep -Fq 'reset:' "$fixtures"
  grep -Fq 'macos-agent exec' "$fixtures"
  grep -Fq 'is not the rerun mechanism' "$fixtures"
  grep -Fq 'Every mutating step declares an observable postcondition' "$fixtures"
  if grep -Fq 'macos-agent scenario' "$fixtures"; then
    return 1
  fi
  # Prepare every product before asserting the rendered reference so this case
  # does not depend on an earlier case having built the render tree.
  for product in codex claude hermes; do
    rendered_contract_prepare_product "$product"
  done
  rendered_contract_assert_reference computer-use macos-desktop references/flow-fixtures.md

  # The matrix names the browser route instead of only denying DOM access, and
  # publishes the negative application classes.
  grep -Fq 'Degenerate-AX application classes' "$matrix"
  grep -Fq 'browser-test' "$matrix"
  grep -Fq 'core/policies/browser-test-routing.md' "$matrix"
  grep -Fq 'Backend freshness audit' "$matrix"

  # The routing policy points back at the desktop route in both directions.
  grep -Fq 'macos-desktop' "$routing"
  grep -Fq 'hands DOM-level, selector, and rendered-page claims back here' "$routing"

  # Deterministic, network-free backend-freshness mirror agreement: the matrix,
  # the pin, and the consumed-surface note must name the same Peekaboo release.
  # Exactly one v4 release may be named. Reducing a multi-release set would hide
  # the ambiguity this audit exists to catch, and `sort` is lexicographic, so a
  # future v4.10.x would otherwise order below v4.2.2.
  local matrix_backends matrix_backend
  matrix_backends="$(sed -n 's/.*Peekaboo \(v4\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' "$matrix" | sort -u)"
  test "$(printf '%s\n' "$matrix_backends" | grep -c .)" -eq 1
  matrix_backend="$matrix_backends"
  grep -Fq "Peekaboo $matrix_backend" "$pin"
  grep -Fq "Peekaboo \`$matrix_backend\`" "$surface"

  for product in codex claude hermes; do
    rendered_contract_prepare_product "$product"
    rendered="$REPO_ROOT/build/$product/plugins/computer-use/skills/macos-desktop/SKILL.md"
    test -s "$rendered"
    assert_surface_routing_contract "$rendered"
  done
}

assert_live_recovery_contract() {
  local skill="$1"

  # A real cold app runtime blocks `permissions` and `bridge` together under the
  # generic probe diagnostic, so the recovery must key on that pair rather than
  # on bridge-specific text that a cold runtime never emits.
  grep -Fq 'blocked checks are limited to `permissions` and `bridge`' "$skill"
  grep -Fq 'required capability probe failed' "$skill"

  # The v4 outcome envelope is dispatch metadata, never the verdict.
  grep -Fq '### Reading The Outcome Envelope' "$skill"
  grep -Fq 'mutation_dispatched' "$skill"
  grep -Fq 'is the normal result of a background accessibility-action delivery' "$skill"
  grep -Fq 'never score it failed on `effect` alone' "$skill"
  grep -Fq 'observe_before_retry' "$skill"

  # A partial inventory is recovered by exact process identity, not reported as
  # a blocker and not retried blindly against the same name.
  grep -Fq '### Partial Application Inventory' "$skill"
  grep -Fq 'Application inventory was incomplete' "$skill"
  grep -Fq -e '--expected-process-start-identity' "$skill"
  grep -Fq 'retarget on a fresh observation, not a blind retry' "$skill"

  # Identity targeting narrows the target; it must never read as a widening.
  grep -Fq 'stricter than name targeting' "$skill"
  grep -Fq 'not resolved from the declared target in this run is out of scope' "$skill"
}

run_live_recovery_contract_probe() {
  local skill="$REPO_ROOT/core/skills/computer-use/macos-desktop/SKILL.md.tera"
  local fixtures="$REPO_ROOT/core/skills/computer-use/macos-desktop/references/flow-fixtures.md"
  local matrix="$REPO_ROOT/docs/source/macos-agent-capability-matrix.md"
  local product rendered

  assert_live_recovery_contract "$skill"

  # The matrix publishes each live-verified recovery and the one honest
  # negative: SSH journals do not accumulate, so a fixture cannot read its
  # stability rate back from them until the adapter defect is fixed.
  grep -Fq '| Cold app-runtime bootstrap | supported |' "$matrix"
  grep -Fq '| Outcome envelope interpretation | supported |' "$matrix"
  grep -Fq '| Partial-inventory identity retargeting | supported |' "$matrix"
  grep -Fq '| SSH journal step accumulation | unsupported |' "$matrix"
  grep -Fq 'sympoies/nils-cli#1512' "$matrix"

  # The fixture format carries the same caveat, so a fixture author does not
  # plan a stability rate the SSH journal cannot supply.
  grep -Fq 'sympoies/nils-cli#1512' "$fixtures"

  for product in codex claude hermes; do
    rendered_contract_prepare_product "$product"
    rendered="$REPO_ROOT/build/$product/plugins/computer-use/skills/macos-desktop/SKILL.md"
    test -s "$rendered"
    assert_live_recovery_contract "$rendered"
  done
}

failures=0
results_record_case \
  "computer-use.macos-desktop" \
  "direct adapter routing preserves journal, privacy, postcondition, local/SSH, MCP ceiling, and review contracts" \
  run_direct_adapter_probe
results_record_case \
  "computer-use.capability-contract" \
  "source and rendered skills remove duplicate mechanics and publish complete capability choices" \
  run_skill_and_matrix_contract_probe
results_record_case \
  "computer-use.surface-routing-contract" \
  "source and rendered skills publish deterministic-first surface selection, the accessibility health gate, the reciprocal browser handoff, rerunnable flow fixtures, the stability threshold, and backend freshness" \
  run_surface_routing_contract_probe
results_record_case \
  "computer-use.live-recovery-contract" \
  "source and rendered skills publish the cold-start signature, the outcome envelope reading, and identity retargeting for a partial inventory" \
  run_live_recovery_contract_probe
exit "$failures"
