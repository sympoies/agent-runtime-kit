#!/usr/bin/env bash
# Result helpers for the runtime smoke harness.

results_init() {
  RESULTS_FILE="$1"
  : >"$RESULTS_FILE"
}

results_add() {
  local id="$1"
  local product="$2"
  local status="$3"
  local skill_count="$4"
  local note="$5"
  printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$product" "$status" "$skill_count" "$note" >>"$RESULTS_FILE"
}

results_record_case() {
  local id="$1"
  local note="$2"
  local status
  shift 2

  set +e
  (
    set -e
    "$@"
  )
  status=$?
  set -e

  if [ "$status" -eq 0 ]; then
    results_add "$id" "shared-cli" "pass" "1" "$note"
  else
    results_add "$id" "shared-cli" "fail" "0" "$note"
    # shellcheck disable=SC2034
    failures=1
  fi

  return 0
}

results_count_status() {
  local status="$1"
  awk -F '\t' -v status="$status" '$3 == status { count++ } END { print count + 0 }' "$RESULTS_FILE"
}

results_total() {
  awk 'END { print NR + 0 }' "$RESULTS_FILE"
}

json_escape() {
  sed 's/\\/\\\\/g; s/"/\\"/g'
}

results_print_json() {
  local mode="$1"
  local pass_count fail_count skip_count blocked_count
  pass_count="$(results_count_status pass)"
  fail_count="$(results_count_status fail)"
  skip_count="$(results_count_status skip-host-capability)"
  blocked_count="$(results_count_status blocked-design)"

  printf '{\n'
  printf '  "schema_version": 1,\n'
  printf '  "mode": "%s",\n' "$mode"
  printf '  "counts": {\n'
  printf '    "pass": %s,\n' "$pass_count"
  printf '    "fail": %s,\n' "$fail_count"
  printf '    "skip-host-capability": %s,\n' "$skip_count"
  printf '    "blocked-design": %s\n' "$blocked_count"
  printf '  },\n'
  printf '  "results": [\n'

  awk -F '\t' '
    function esc(value) {
      gsub(/\\/, "\\\\", value)
      gsub(/"/, "\\\"", value)
      return value
    }
    {
      if (NR > 1) {
        printf ",\n"
      }
      printf "    {\"id\":\"%s\",\"product\":\"%s\",\"status\":\"%s\",\"skill_count\":%s,\"note\":\"%s\"}",
        esc($1), esc($2), esc($3), $4, esc($5)
    }
    END {
      printf "\n"
    }
  ' "$RESULTS_FILE"

  printf '  ]\n'
  printf '}\n'
}

results_print_text() {
  local mode="$1"
  local pass_count fail_count skip_count blocked_count total_count
  pass_count="$(results_count_status pass)"
  fail_count="$(results_count_status fail)"
  skip_count="$(results_count_status skip-host-capability)"
  blocked_count="$(results_count_status blocked-design)"
  total_count="$(results_total)"

  printf 'runtime-smoke: mode=%s total=%s pass=%s fail=%s skip-host-capability=%s blocked-design=%s\n' \
    "$mode" "$total_count" "$pass_count" "$fail_count" "$skip_count" "$blocked_count"
  awk -F '\t' '{ printf "  %s product=%s status=%s skill_count=%s note=%s\n", $1, $2, $3, $4, $5 }' "$RESULTS_FILE"
}

results_has_failures() {
  local fail_count blocked_count
  fail_count="$(results_count_status fail)"
  blocked_count="$(results_count_status blocked-design)"
  if [ "$fail_count" -gt 0 ] || [ "$blocked_count" -gt 0 ]; then
    return 0
  fi
  return 1
}

results_validate_unique_ids() {
  local duplicates
  duplicates="$(cut -f1 "$RESULTS_FILE" | sort | uniq -d)"
  if [ -n "$duplicates" ]; then
    echo "runtime-smoke: duplicate result ids:" >&2
    echo "$duplicates" >&2
    return 1
  fi
}
