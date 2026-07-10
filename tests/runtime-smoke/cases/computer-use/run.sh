#!/usr/bin/env bash
# Deterministic probes for the macOS computer-use skill helper.

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"

HELPER="$REPO_ROOT/core/skills/computer-use/macos-desktop/bin/macos_desktop.py"
CASE_ROOT="$TMP_ROOT/computer-use"
FAKE_BIN="$CASE_ROOT/bin"
REMOTE_HOME="$CASE_ROOT/remote-home"
CASE_ARTIFACTS="$ARTIFACTS_DIR/computer-use"
mkdir -p "$FAKE_BIN" "$REMOTE_HOME" "$CASE_ARTIFACTS"

make_fakes() {
  cat >"$FAKE_BIN/macos-agent" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

args=" $* "
if [[ "$args" == *" preflight "* ]]; then
  if [[ "${COMPUTER_USE_TEST_UNKNOWN_PERMISSIONS:-}" == "1" ]]; then
    printf '%s\n' '{"schema_version":1,"ok":true,"command":"preflight","result":{"status":"degraded","permissions":{"accessibility":"ready","ready":false,"hints":["Permission state is incomplete."]}}}'
    exit 0
  fi
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"preflight","result":{"status":"degraded","permissions":{"screen_recording":"missing","accessibility":"ready","automation":"ready","ready":false,"hints":["Enable Screen Recording for the terminal host."]}}}'
  exit 0
fi

if [[ "$args" == *" observe screenshot "* ]]; then
  output=""
  while [[ "$#" -gt 0 ]]; do
    if [[ "$1" == "--path" ]]; then
      output="$2"
      break
    fi
    shift
  done
  test -n "$output"
  mkdir -p "$(dirname "$output")"
  printf 'synthetic-png' >"$output"
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"observe.screenshot","result":{"captured":true}}'
  exit 0
fi

if [[ "$args" == *" scenario run "* ]]; then
  scenario=""
  while [[ "$#" -gt 0 ]]; do
    if [[ "$1" == "--file" ]]; then
      scenario="$2"
      break
    fi
    shift
  done
  test -s "$scenario"
  grep -q 'Synthetic App' "$scenario"
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"scenario.run","result":{"steps":2}}'
  exit 0
fi

if [[ "$args" == *" input key "* ]]; then
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"input.key","result":{"key":"escape","policy":{"retries":0}}}'
  exit 0
fi

if [[ "$args" == *" input move "* ]]; then
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"input.move","result":{"x":20,"y":30,"policy":{"retries":0}}}'
  exit 0
fi

if [[ "$args" == *" input drag "* ]]; then
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"input.drag","result":{"mods":["shift"],"policy":{"retries":0}}}'
  exit 0
fi

if [[ "$args" == *" input scroll "* ]]; then
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"input.scroll","result":{"mods":["shift"],"policy":{"retries":0}}}'
  exit 0
fi

if [[ "$args" == *" input click "* ]]; then
  printf '%s\n' '{"schema_version":1,"ok":true,"command":"input.click","result":{"mods":["cmd"],"policy":{"retries":0}}}'
  exit 0
fi

printf '%s\n' '{"schema_version":1,"ok":true,"command":"ax.list","result":{"nodes":[]}}'
SH

  cat >"$FAKE_BIN/ssh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    -o)
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

test "$#" -ge 2
host="$1"
shift
if [[ "$host" == "private-alias.invalid" ]]; then
  printf 'ssh: Could not resolve hostname %s: Name or service not known\n' "$host" >&2
  exit 255
fi
test "$host" = "example-mac"
HOME="${COMPUTER_USE_TEST_REMOTE_HOME:?}" PATH="${COMPUTER_USE_TEST_PATH:?}" bash -c "$1"
SH

  chmod +x "$FAKE_BIN/macos-agent" "$FAKE_BIN/ssh"
}

run_probe() {
  test -x "$HELPER"
  make_fakes

  local local_out="$CASE_ROOT/local"
  local unknown_out="$CASE_ROOT/unknown-permissions"
  local remote_out="$CASE_ROOT/remote"
  local capture="$CASE_ROOT/captured.png"
  local scenario="$CASE_ROOT/scenario.json"
  local invalid_err="$CASE_ARTIFACTS/invalid-host.stderr.txt"

  printf '%s\n' '{"name":"synthetic","steps":[{"action":"activate","app":"Synthetic App"},{"action":"wait","ms":10}]}' >"$scenario"

  PATH="$FAKE_BIN:$PATH" python3 "$HELPER" preflight --out-dir "$local_out" \
    >"$CASE_ARTIFACTS/local-preflight.json"
  grep -q '"status": "degraded"' "$CASE_ARTIFACTS/local-preflight.json"
  grep -q 'screen_recording' "$local_out/pending-user-actions.json"

  PATH="$FAKE_BIN:$PATH" COMPUTER_USE_TEST_UNKNOWN_PERMISSIONS=1 \
    python3 "$HELPER" preflight --out-dir "$unknown_out" \
    >"$CASE_ARTIFACTS/unknown-permissions-preflight.json"
  grep -q 'screen_recording' "$unknown_out/pending-user-actions.json"
  grep -q '"status": "unknown"' "$unknown_out/pending-user-actions.json"

  PATH="$FAKE_BIN:$PATH" COMPUTER_USE_TEST_REMOTE_HOME="$REMOTE_HOME" COMPUTER_USE_TEST_PATH="$FAKE_BIN:$PATH" \
    python3 "$HELPER" run --host example-mac --out-dir "$remote_out" -- ax list --app "Synthetic App" \
    >"$CASE_ARTIFACTS/remote-run.json"
  grep -q '"transport": "ssh"' "$CASE_ARTIFACTS/remote-run.json"
  grep -q '"ok": true' "$CASE_ARTIFACTS/remote-run.json"

  local action command_slug
  for action in \
    'input key --key escape' \
    'input move --x 20 --y 30' \
    'input click --x 20 --y 30 --mods cmd' \
    'input drag --from-x 20 --from-y 30 --to-x 40 --to-y 50 --mods shift' \
    'input scroll --delta-y -1 --unit line --mods shift'; do
    command_slug="$(printf '%s' "$action" | awk '{print $1 "." $2}')"
    # shellcheck disable=SC2086
    PATH="$FAKE_BIN:$PATH" python3 "$HELPER" run --out-dir "$local_out" -- $action \
      >"$CASE_ARTIFACTS/${command_slug}.json"
    grep -q "\"command\": \"${command_slug}\"" "$CASE_ARTIFACTS/${command_slug}.json"
    grep -q '"retries": 0' "$CASE_ARTIFACTS/${command_slug}.json"
  done

  PATH="$FAKE_BIN:$PATH" COMPUTER_USE_TEST_REMOTE_HOME="$REMOTE_HOME" COMPUTER_USE_TEST_PATH="$FAKE_BIN:$PATH" \
    python3 "$HELPER" capture --host example-mac --out-dir "$remote_out" --path "$capture" -- --app "Synthetic App" \
    >"$CASE_ARTIFACTS/remote-capture.json"
  test "$(cat "$capture")" = "synthetic-png"

  PATH="$FAKE_BIN:$PATH" COMPUTER_USE_TEST_REMOTE_HOME="$REMOTE_HOME" COMPUTER_USE_TEST_PATH="$FAKE_BIN:$PATH" \
    python3 "$HELPER" scenario --host example-mac --out-dir "$remote_out" --file "$scenario" \
    >"$CASE_ARTIFACTS/remote-scenario.json"
  grep -q '"ok": true' "$CASE_ARTIFACTS/remote-scenario.json"

  if PATH="$FAKE_BIN:$PATH" python3 "$HELPER" run --host=-unsafe --out-dir "$remote_out" -- apps list \
    >"$CASE_ARTIFACTS/invalid-host.stdout.txt" 2>"$invalid_err"; then
    return 1
  fi
  grep -q 'must not start with' "$invalid_err"

  if PATH="$FAKE_BIN:$PATH" python3 "$HELPER" run --host private-alias.invalid \
    --out-dir "$remote_out" -- apps list \
    >"$CASE_ARTIFACTS/ssh-failure.json" 2>"$CASE_ARTIFACTS/ssh-failure.stderr.txt"; then
    return 1
  fi
  grep -q '<ssh-target>' "$CASE_ARTIFACTS/ssh-failure.json"
  ! rg -n 'private-alias\.invalid' "$CASE_ARTIFACTS/ssh-failure.json" "$remote_out/session.jsonl"

  test -s "$local_out/session.jsonl"
  test -s "$remote_out/session.jsonl"
  ! rg -n '/home/|/Users/|HostName|IdentityFile|BEGIN OPENSSH PRIVATE KEY' \
    "$REPO_ROOT/core/skills/computer-use" "$CASE_ARTIFACTS"
}

failures=0
results_record_case \
  "computer-use.macos-desktop" \
  "local and SSH transports preserve structured output, artifacts, degraded permissions, scenarios, and safe host parsing" \
  run_probe

exit "$failures"
