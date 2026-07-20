#!/usr/bin/env bash
# scripts/ci/all.sh — agent-runtime-kit CI gate stack.
#
# Linear, ordered gate stack — do not parallelize. Each position prints a
# banner, runs its check, reports its elapsed wall-clock, and exits non-zero on
# the first failure. Positions are NOT run concurrently: several positions
# invoke `agent-runtime render` against the shared render cache and position 8's
# convergence acceptance asserts a clean working tree, so overlapping positions
# race the cache and that clean-tree check (measured flaky). See issue #689.
#
# Compatibility: must run on macOS (system bash 3.2) and Linux runners.
# Avoid associative arrays, mapfile, and `${var,,}` lowercasing.
#
# Required on PATH (installed via `brew install sympoies/tap/nils-cli`):
#   - agent-runtime  (subcommands: render, audit-drift, doctor)
#   - plan-tooling   (subcommand: validate)
#   - python3        (for offline runtime-smoke loopback/sample probes,
#                    and for parsing the skill-surface doctor JSON output)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Git hooks export repo-local GIT_* variables. They are correct for the hook
# process, but they leak into temp git repositories used by runtime smoke tests.
if git_local_env="$(git rev-parse --local-env-vars 2>/dev/null)"; then
  while IFS= read -r env_name; do
    [[ -n "$env_name" ]] && unset "$env_name"
  done <<<"$git_local_env"
fi

# Per-position wall-clock timing. `banner` closes out the previous position's
# timer before opening the next; `banner_final` closes the last one. Timings go
# to stderr so they never contaminate a position's captured stdout.
CI_ALL_LAST_TS=""
CI_ALL_LAST_POS=""

banner() {
  local position="$1"
  local title="$2"
  local now
  now="$(date +%s)"
  if [ -n "$CI_ALL_LAST_TS" ]; then
    printf '==[ ci/all.sh position %s took %ss ]==\n' \
      "$CI_ALL_LAST_POS" "$((now - CI_ALL_LAST_TS))" >&2
  fi
  CI_ALL_LAST_TS="$now"
  CI_ALL_LAST_POS="$position"
  printf '\n==[ ci/all.sh position %s ]== %s\n' "$position" "$title"
}

banner_final() {
  local now
  now="$(date +%s)"
  if [ -n "$CI_ALL_LAST_TS" ]; then
    printf '==[ ci/all.sh position %s took %ss ]==\n' \
      "$CI_ALL_LAST_POS" "$((now - CI_ALL_LAST_TS))" >&2
  fi
}

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "ci/all.sh: required binary not on PATH: $bin" >&2
    exit 127
  fi
}

require_bin agent-runtime
require_bin python3

is_linked_worktree() {
  local git_dir
  local git_common_dir
  git_dir="$(git rev-parse --git-dir 2>/dev/null || true)"
  git_common_dir="$(git rev-parse --git-common-dir 2>/dev/null || true)"
  [[ -n "$git_dir" && -n "$git_common_dir" && "$git_dir" != "$git_common_dir" ]]
}

allow_linked_worktree_extra_drift() {
  [[ "${AGENT_RUNTIME_KIT_HOOK_PHASE:-}" == "pre-push" ]] || return 1
  is_linked_worktree
}

run_root_audit_drift() {
  local audit_text
  local audit_status
  local audit_json
  local audit_json_status

  set +e
  audit_text="$(agent-runtime audit-drift 2>&1)"
  audit_status=$?
  set -e

  printf '%s\n' "$audit_text"
  if [[ "$audit_status" -eq 0 ]]; then
    return 0
  fi

  if ! allow_linked_worktree_extra_drift; then
    return "$audit_status"
  fi

  set +e
  audit_json="$(agent-runtime audit-drift --format json 2>&1)"
  audit_json_status=$?
  set -e

  if [[ "$audit_json_status" -gt 2 ]]; then
    printf '%s\n' "$audit_json" >&2
    return "$audit_status"
  fi

  if AUDIT_DRIFT_JSON="$audit_json" python3 - <<'PY'
import json
import os
import sys

try:
    payload = json.loads(os.environ["AUDIT_DRIFT_JSON"])
except (KeyError, json.JSONDecodeError):
    sys.exit(1)

allowed = []
blocking = []
for finding in payload.get("findings", []):
    severity = finding.get("severity")
    if severity in ("info", "suppressed"):
        continue
    if severity == "warn" and finding.get("class") == "extra":
        allowed.append(finding)
    else:
        blocking.append(finding)

if blocking or not allowed:
    sys.exit(1)

print(
    "ci/all.sh: linked-worktree pre-push allowed "
    f"{len(allowed)} live-install extra warn finding(s); "
    "clean-checkout CI remains strict."
)
PY
  then
    return 0
  fi

  return "$audit_status"
}

# -----------------------------------------------------------------------------
# Position 1 — nils-cli minimum/validated policy (version-alignment doctor)
#
# Delegates to `agent-runtime doctor --class version-alignment`, released in
# nils-cli v0.28.0 (sympoies/nils-cli#636), instead of the prior hand-rolled
# shell + python floor compare. The class reads the machine-readable pin
# manifest `docs/source/nils-cli-pin.yaml`: `minimum_supported_tag` controls
# admission, `validated_tag` controls reproducibility, and `required_clis[]`
# retains per-binary floors. A host below minimum blocks. A host above validated
# warns but continues into every downstream behavior gate; this avoids making a
# routine host upgrade fail solely because the exact validated snapshot lags.
#
# The doctor emits a remediation-quality banner naming both versions and every
# offending check, and exits non-zero (2) on block, so this gate is a thin
# exit-code wrapper — no markdown parse or python version compare needed. The
# human-readable surface snapshot stays in `docs/source/nils-cli-surface.md`;
# the YAML manifest is the gate's pin source. Keep the two in lock-step.
# -----------------------------------------------------------------------------
banner 1 "nils-cli minimum/validated policy vs agent-runtime"
PIN_MANIFEST="docs/source/nils-cli-pin.yaml"
if [ ! -f "$PIN_MANIFEST" ]; then
  echo "ci/all.sh: nils-cli version policy not found: $PIN_MANIFEST" >&2
  exit 1
fi
if ! agent-runtime doctor --class version-alignment --pin "$PIN_MANIFEST" --format text; then
  echo >&2
  echo "ci/all.sh: nils-cli version policy failed (see doctor block above)" >&2
  echo >&2
  echo "  Remediation:" >&2
  echo "  - Host below minimum: brew upgrade sympoies/tap/nils-cli" >&2
  echo "  - Consumed behavior changed: update policy through meta:nils-cli-bump" >&2
  echo "    and refresh consumers; ordinary uptake moves validated only, while an" >&2
  echo "    intentional compatibility retirement may move minimum." >&2
  echo "    The skill updates $PIN_MANIFEST, docs/source/nils-cli-surface.md," >&2
  echo "    any affected SKILL bodies," >&2
  echo "    runtime-smoke fixtures, and goldens that referenced the retired surface." >&2
  exit 1
fi
python3 tests/ci/test_nils_cli_version_policy.py
echo "ci/all.sh: nils-cli policy admitted host; downstream sentinel reached"

# -----------------------------------------------------------------------------
# Position 2 — plan bundle and skill lifecycle governance validation
#
# This is intentionally after version admission: no nils-cli surface other
# than the schema-v2 doctor may execute before a below-minimum host is blocked.
# -----------------------------------------------------------------------------
require_bin plan-tooling
banner 2 "plan-tooling validate + skill-governance audit"
plan-tooling validate --format text --explain
bash scripts/ci/skill-governance-audit.sh
bash scripts/ci/skill-governance-audit.sh --fixture count-refresh
bash scripts/ci/skill-governance-audit.sh --fixture codex-plugin
bash scripts/ci/skill-governance-audit.sh --fixture description-limit
bash scripts/ci/skill-governance-audit.sh --fixture exposure-contract
bash scripts/ci/skill-governance-audit.sh --fixture create
bash scripts/ci/skill-governance-audit.sh --fixture remove
bash tests/skill-exposure-contract/run.sh

# -----------------------------------------------------------------------------
# Position 3 — render home prompts and codex
# -----------------------------------------------------------------------------
banner 3 "agent-runtime render --target home-prompt + --product codex"
agent-runtime render --target home-prompt
agent-runtime render --target home-prompt --product codex
agent-runtime render --target home-prompt --product claude
agent-runtime render --target home-prompt --product hermes
agent-runtime render --product codex

# -----------------------------------------------------------------------------
# Position 4 — render claude
# -----------------------------------------------------------------------------
banner 4 "agent-runtime render --product claude + --product hermes"
agent-runtime render --product claude
agent-runtime render --product hermes

# -----------------------------------------------------------------------------
# Position 5 — render shared support matrix
# -----------------------------------------------------------------------------
banner 5 "agent-runtime render --target support-matrix"
agent-runtime render --target support-matrix

# -----------------------------------------------------------------------------
# Position 6 — golden diff (rendered build vs committed golden tree)
# -----------------------------------------------------------------------------
banner 6 "git diff --exit-code tests/golden/ (after --update-golden refresh)"
agent-runtime render --target home-prompt >/dev/null
agent-runtime render --target home-prompt --update-golden >/dev/null
agent-runtime render --target home-prompt --product codex >/dev/null
agent-runtime render --target home-prompt --product claude >/dev/null
agent-runtime render --target home-prompt --product hermes >/dev/null
agent-runtime render --product codex --update-golden >/dev/null
agent-runtime render --product claude --update-golden >/dev/null
agent-runtime render --product hermes --update-golden >/dev/null
agent-runtime render --target support-matrix --update-golden >/dev/null
git diff --exit-code -- tests/golden/

# -----------------------------------------------------------------------------
# Position 7 — audit-drift (root sweep + four hermetic fixtures)
# -----------------------------------------------------------------------------
banner 7 "agent-runtime audit-drift (root + tests/drift fixtures)"
run_root_audit_drift

drift_fixtures=(
  agent-home-leak
  docs-home-mismatch
  rendered-target-diff
  source-manifest-missing
)

for fixture in "${drift_fixtures[@]}"; do
  fixture_root="tests/drift/${fixture}"
  expected_txt="${fixture_root}/expected.txt"
  expected_exit_file="${fixture_root}/expected.exit"
  if [[ ! -f "$expected_txt" || ! -f "$expected_exit_file" ]]; then
    echo "ci/all.sh: drift fixture missing expected artifacts: $fixture_root" >&2
    exit 1
  fi
  expected_exit="$(cat "$expected_exit_file")"
  printf 'drift fixture: %s (expected exit=%s)\n' "$fixture" "$expected_exit"
  set +e
  actual_output="$(agent-runtime audit-drift --source-root "${fixture_root}/" 2>&1)"
  actual_exit=$?
  set -e
  if [[ "$actual_exit" != "$expected_exit" ]]; then
    echo "ci/all.sh: drift fixture $fixture exit mismatch: got=$actual_exit expected=$expected_exit" >&2
    echo "$actual_output" >&2
    exit 1
  fi
  if ! diff -u "$expected_txt" <(printf '%s\n' "$actual_output") >/tmp/ci-all-drift.diff 2>&1; then
    echo "ci/all.sh: drift fixture $fixture output mismatch:" >&2
    cat /tmp/ci-all-drift.diff >&2
    exit 1
  fi
done

# -----------------------------------------------------------------------------
# Position 8 — supply-chain hardening + surface registry schema + executable acceptance
# -----------------------------------------------------------------------------
banner 8 "security hardening audit + validate surfaces manifest + executable acceptance"
python3 scripts/ci/security-hardening-audit.py
bash tests/ci/expect-command-failure.sh
bash scripts/ci/expect-command-failure.sh \
  "ci/all.sh: invalid surface acceptance fixture rejected as expected" \
  "ci/all.sh: invalid surface acceptance fixture unexpectedly passed" \
  bash scripts/ci/validate-surfaces-manifest.sh \
    tests/surfaces/invalid-acceptance.yaml
ACCEPTANCE_OUT_DIR="${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/ci-all/surface-acceptance"
ACCEPTANCE_CODEX_HOME="${ACCEPTANCE_OUT_DIR}/codex-home"
rm -rf "$ACCEPTANCE_CODEX_HOME"
mkdir -p "$ACCEPTANCE_CODEX_HOME"
ln -s "$REPO_ROOT/build/codex/AGENT_HOME.md" "$ACCEPTANCE_CODEX_HOME/AGENTS.md"
CODEX_HOME="$ACCEPTANCE_CODEX_HOME" bash scripts/ci/validate-surfaces-manifest.sh --execute-acceptance

# -----------------------------------------------------------------------------
# Position 9 — Codex skill-surface shape diagnostic (preflight, not live)
#
# Shape validation only. Live Codex Desktop discovery still requires
# `codex debug prompt-input` in a fresh session — see
# docs/plans/2026-06-20-codex-plugin-marketplace-adoption/ for the live acceptance
# protocol. The expected check count is documented in that plan's execution
# state; bump SHAPE_EXPECTED_MIN_CHECKS together with a recorded reason.
# -----------------------------------------------------------------------------
SHAPE_EXPECTED_MIN_CHECKS=21
SHAPE_OUT_DIR="${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/ci-all"
mkdir -p "$SHAPE_OUT_DIR"
SHAPE_JSON="$SHAPE_OUT_DIR/shape-diagnostic.json"
SHAPE_SUMMARY="$SHAPE_OUT_DIR/shape-diagnostic.summary"

banner 9 "agent-runtime doctor --class skill-surface --product codex"
agent-runtime doctor \
  --class skill-surface \
  --product codex \
  --format json \
  --source-root "$REPO_ROOT" \
  >"$SHAPE_JSON"

SHAPE_VERDICT="$(
  SHAPE_JSON_PATH="$SHAPE_JSON" \
    SHAPE_EXPECTED_MIN_CHECKS="$SHAPE_EXPECTED_MIN_CHECKS" \
    python3 - <<'PY'
import json
import os
import sys

path = os.environ["SHAPE_JSON_PATH"]
expected_min = int(os.environ["SHAPE_EXPECTED_MIN_CHECKS"])
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

exit_code = data.get("exit_code")
checks = data.get("checks")
ok = data.get("ok")
warn = data.get("warn")
block = data.get("block")
findings = data.get("findings") or []
boundary = data.get("acceptance_boundary", "")

errors = []
if exit_code != 0:
    errors.append("doctor exit_code=%r (expected 0)" % exit_code)
if not isinstance(checks, int) or checks < expected_min:
    errors.append(
        "checks=%r below documented baseline %d "
        "(bump SHAPE_EXPECTED_MIN_CHECKS in scripts/ci/all.sh "
        "and record the reason in "
        "docs/plans/2026-06-20-codex-plugin-marketplace-adoption/"
        "2026-06-20-codex-plugin-marketplace-adoption-execution-state.md)"
        % (checks, expected_min)
    )
if ok != checks:
    errors.append("ok=%r != checks=%r" % (ok, checks))
if warn != 0:
    errors.append("warn=%r (expected 0)" % warn)
if block != 0:
    errors.append("block=%r (expected 0)" % block)
if findings:
    errors.append("findings present: %d entries" % len(findings))

print("checks=%s ok=%s warn=%s block=%s exit_code=%s findings=%d"
      % (checks, ok, warn, block, exit_code, len(findings)))
print("acceptance-boundary: %s" % boundary)
if errors:
    print()
    print("skill-surface shape gate FAILED:")
    for err in errors:
        print("  - " + err)
    sys.exit(1)
PY
)" || {
  printf '%s\n' "$SHAPE_VERDICT" >&2
  printf '%s\n' "$SHAPE_VERDICT" >"$SHAPE_SUMMARY"
  echo "ci/all.sh: skill-surface shape gate failed (artifact: $SHAPE_JSON)" >&2
  exit 1
}
printf '%s\n' "$SHAPE_VERDICT"
printf '%s\n' "$SHAPE_VERDICT" >"$SHAPE_SUMMARY"

# -----------------------------------------------------------------------------
# Position 10 — sandbox install rehearsal
# -----------------------------------------------------------------------------
banner 10 "sandbox install rehearsal (dry-run skill-list diff)"
bash scripts/ci/sandbox-install-rehearsal.sh

# -----------------------------------------------------------------------------
# Position 11 — deterministic runtime skill smoke
# -----------------------------------------------------------------------------
banner 11 "runtime skill deterministic smoke"
bash tests/runtime-smoke/run.sh --mode deterministic

# -----------------------------------------------------------------------------
# Position 12 — project-local overlay smoke
# -----------------------------------------------------------------------------
banner 12 "project-local overlay smoke"
bash tests/projects/project-local-smoke/run.sh

# -----------------------------------------------------------------------------
# Position 13 — agent-hook policy and shared hook contract smoke
# -----------------------------------------------------------------------------
banner 13 "agent-hook policy + shared hook contract smoke"
bash tests/agent-hook/run.sh
bash tests/hooks/run.sh

# -----------------------------------------------------------------------------
# Position 14 — version-baseline mirror consistency (deterministic, no network)
# -----------------------------------------------------------------------------
banner 14 "version-baseline mirror consistency audit"
python3 scripts/ci/version-baseline-audit.py check

# -----------------------------------------------------------------------------
# Position 15 — rendered product leakage audit
# -----------------------------------------------------------------------------
banner 15 "product leakage audit"
bash scripts/ci/product-leak-audit.sh --self-test
bash scripts/ci/product-leak-audit.sh

# -----------------------------------------------------------------------------
# Position 16 — memory policy, retired-reference audit, and product routing
# -----------------------------------------------------------------------------
banner 16 "memory runtime policy + retired-reference audit"
bash tests/memory-runtime/run.sh

# -----------------------------------------------------------------------------
# Position 17 — context budget audit (#601 P1 visible context budgets)
#
# Measures the always-on and per-intent context surfaces (rendered AGENT_HOME,
# representative project-dev edit-phase required reading, startup memory, and the
# unchanged-prompt route cue) against the issue's byte budgets. Fails closed when
# a surface exceeds its target without an explicit, tracked override, so context
# growth is a reviewable decision rather than invisible drift. The rendered
# build/<product>/AGENT_HOME.md artifacts measured here are produced by
# positions 3-6 above; --self-test proves the classifier before the real gate.
# -----------------------------------------------------------------------------
banner 17 "context budget audit (#601 P1)"
python3 scripts/ci/context-budget-audit.py --self-test
python3 scripts/ci/context-budget-audit.py check

banner_final
printf '\nci/all.sh: positions 1-17 OK\n'
