#!/usr/bin/env bash
# Temporary runtime home helpers for the runtime smoke harness.

runtime_live_home() {
  local tmp_root="$1"
  local product="$2"
  printf '%s/live/%s' "$tmp_root" "$product"
}

runtime_state_home() {
  local tmp_root="$1"
  local product="$2"
  printf '%s/state/%s' "$tmp_root" "$product"
}

runtime_prepare_portable_source() {
  local source="$1"
  local snapshot="$2"
  local revision

  if ! git -C "$source" diff --quiet --ignore-submodules -- ||
    ! git -C "$source" diff --cached --quiet --ignore-submodules -- ||
    [ -n "$(git -C "$source" ls-files --others --exclude-standard)" ]; then
    echo "runtime-smoke: portable source must be clean; commit or stash reviewed changes" >&2
    return 1
  fi

  revision="$(git -C "$source" rev-parse HEAD)"
  mkdir -p "$snapshot"
  git -C "$snapshot" init -q
  git -C "$snapshot" remote add origin "$source"
  git -C "$snapshot" -c protocol.file.allow=always fetch -q --no-tags origin \
    "$revision:refs/heads/portable-source"
  git -C "$snapshot" -c advice.detachedHead=false checkout -q --detach "$revision"
  git -C "$snapshot" branch -q -D portable-source
  test "$(git -C "$snapshot" rev-parse HEAD)" = "$revision"
  git -C "$snapshot" diff --quiet --ignore-submodules --
  git -C "$snapshot" diff --cached --quiet --ignore-submodules --
  test -z "$(git -C "$snapshot" ls-files --others --exclude-standard)"
  printf '%s\n' "$snapshot"
}

runtime_prepare_revision_source() {
  local source="$1"
  local revision="$2"
  local snapshot="$3"

  git -C "$source" cat-file -e "$revision^{commit}"
  mkdir -p "$snapshot"
  git -C "$snapshot" init -q
  git -C "$snapshot" remote add origin "$source"
  git -C "$snapshot" -c protocol.file.allow=always fetch -q --no-tags origin \
    "$revision:refs/heads/portable-baseline"
  git -C "$snapshot" -c advice.detachedHead=false checkout -q --detach "$revision"
  git -C "$snapshot" branch -q -D portable-baseline
  test "$(git -C "$snapshot" rev-parse HEAD)" = "$revision"
  printf '%s\n' "$snapshot"
}

runtime_validate_expected_file() {
  local expected="$1"
  local sorted="$2"

  if [ ! -s "$expected" ]; then
    echo "runtime-smoke: expected skill pin missing or empty: $expected" >&2
    return 1
  fi
  if grep -n '^$' "$expected" >"$sorted.blank-lines" 2>&1; then
    echo "runtime-smoke: blank line(s) in $expected:" >&2
    cat "$sorted.blank-lines" >&2
    return 1
  fi
  sort -u "$expected" >"$sorted"
  if ! diff -u "$expected" "$sorted" >"$sorted.diff" 2>&1; then
    echo "runtime-smoke: expected skill pin is not sorted/unique: $expected" >&2
    cat "$sorted.diff" >&2
    return 1
  fi
}

runtime_collect_installed_skills() {
  local live_home="$1"
  local product="$2"

  case "$product" in
    codex)
      find "$live_home/plugins" -path '*/skills/*/SKILL.md' -print |
        sed "s#^$live_home/plugins/##" |
        sed 's#/skills/#.#' |
        sed 's#/SKILL\.md$##' |
        sort -u
      ;;
    *)
      find "$live_home/plugins" -path '*/skills/*/SKILL.md' -print |
        sed "s#^$live_home/plugins/##" |
        sed 's#/skills/#.#' |
        sed 's#/SKILL\.md$##' |
        sort -u
      ;;
  esac
}

runtime_doctor_block_count() {
  local doctor_log="$1"
  local first_line
  first_line="$(sed -n '1p' "$doctor_log")"
  printf '%s\n' "$first_line" | sed -n 's/.* block=\([0-9][0-9]*\).*/\1/p'
}

runtime_install_product() {
  local repo_root="$1"
  local tmp_root="$2"
  local product="$3"
  local artifacts_dir="$4"
  local live_home state_home expected observed declared sorted install_log doctor_log
  local installed_doctor_json receipt_summary doctor_exit block_count expected_revision

  live_home="$(runtime_live_home "$tmp_root" "$product")"
  state_home="$(runtime_state_home "$tmp_root" "$product")"
  expected="$repo_root/tests/sandbox/${product}/expected-skills.txt"
  observed="$artifacts_dir/${product}.observed-skills.txt"
  declared="$artifacts_dir/${product}.declared-skills.txt"
  sorted="$artifacts_dir/${product}.expected.sorted"
  install_log="$artifacts_dir/${product}.install.log"
  doctor_log="$artifacts_dir/${product}.doctor.log"
  installed_doctor_json="$artifacts_dir/${product}.installed-runtime.json"
  receipt_summary="$artifacts_dir/${product}.receipt-summary.json"

  mkdir -p "$live_home" "$state_home" "$artifacts_dir"
  runtime_validate_expected_file "$expected" "$sorted" || return 1

  if ! agent-runtime render \
    --source-root "$repo_root" \
    --product "$product" >"$artifacts_dir/${product}.render.log" 2>&1; then
    echo "runtime-smoke: render failed for $product" >&2
    cat "$artifacts_dir/${product}.render.log" >&2
    return 1
  fi

  if ! agent-runtime install \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay \
    --apply >"$install_log" 2>&1; then
    echo "runtime-smoke: install --apply failed for $product" >&2
    cat "$install_log" >&2
    return 1
  fi

  runtime_collect_installed_skills "$live_home" "$product" >"$observed"
  if [ ! -s "$observed" ]; then
    echo "runtime-smoke: no installed SKILL.md surfaces found for $product" >&2
    cat "$install_log" >&2
    return 1
  fi
  if ! diff -u "$expected" "$observed" >"$artifacts_dir/${product}.skills.diff" 2>&1; then
    echo "runtime-smoke: installed skill mismatch for $product" >&2
    cat "$artifacts_dir/${product}.skills.diff" >&2
    return 1
  fi

  if ! agent-runtime list-skills \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --format json >"$artifacts_dir/${product}.list-skills.json" 2>&1; then
    echo "runtime-smoke: list-skills failed for $product" >&2
    cat "$artifacts_dir/${product}.list-skills.json" >&2
    return 1
  fi
  python3 - "$artifacts_dir/${product}.list-skills.json" "$declared" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
pathlib.Path(sys.argv[2]).write_text(
    "".join(f"{item['id']}\n" for item in sorted(data["skills"], key=lambda item: item["id"])),
    encoding="utf-8",
)
PY
  if ! diff -u "$expected" "$declared" >"$artifacts_dir/${product}.declared-skills.diff" 2>&1; then
    echo "runtime-smoke: list-skills mismatch for $product" >&2
    cat "$artifacts_dir/${product}.declared-skills.diff" >&2
    return 1
  fi

  set +e
  agent-runtime doctor \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay >"$doctor_log" 2>&1
  doctor_exit=$?
  set -e

  block_count="$(runtime_doctor_block_count "$doctor_log")"
  if [ -z "$block_count" ]; then
    echo "runtime-smoke: could not parse doctor block count for $product (exit=$doctor_exit)" >&2
    cat "$doctor_log" >&2
    return 1
  fi
  if [ "$block_count" != "0" ]; then
    echo "runtime-smoke: doctor reported blocking findings for $product (exit=$doctor_exit)" >&2
    cat "$doctor_log" >&2
    return 1
  fi

  if ! agent-runtime doctor \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay \
    --class installed-runtime \
    --format json >"$installed_doctor_json" 2>&1; then
    echo "runtime-smoke: installed-runtime doctor failed for $product" >&2
    cat "$installed_doctor_json" >&2
    return 1
  fi
  expected_revision="$(git -C "$repo_root" rev-parse HEAD)"
  if ! python3 "$SCRIPT_DIR/lib/verify-install-receipt.py" \
    "$installed_doctor_json" \
    "$receipt_summary" \
    "$repo_root" \
    "$product" \
    "$expected_revision"; then
    echo "runtime-smoke: installed-runtime receipt mismatch for $product" >&2
    cat "$installed_doctor_json" >&2
    return 1
  fi
  python3 - "$installed_doctor_json" "$artifacts_dir/${product}.tampered-receipt.json" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
data["installed_runtime"]["receipt"]["managed_entries"][0]["digest"] = "sha256:" + "0" * 64
pathlib.Path(sys.argv[2]).write_text(json.dumps(data) + "\n", encoding="utf-8")
PY
  if python3 "$SCRIPT_DIR/lib/verify-install-receipt.py" \
    "$artifacts_dir/${product}.tampered-receipt.json" \
    "$artifacts_dir/${product}.tampered-summary.json" \
    "$repo_root" \
    "$product" \
    "$expected_revision" >"$artifacts_dir/${product}.tampered-receipt.stdout" 2>&1; then
    echo "runtime-smoke: independent receipt verifier accepted tampered digest for $product" >&2
    return 1
  fi

  # shellcheck disable=SC2034 # consumed by run.sh after this sourced helper returns
  RUNTIME_SMOKE_SKILL_COUNT="$(wc -l <"$observed" | tr -d ' ')"
  return 0
}

runtime_product_config_path() {
  local live_home="$1"
  local product="$2"
  case "$product" in
    codex) printf '%s/config.toml\n' "$live_home" ;;
    claude) printf '%s/settings.json\n' "$live_home" ;;
    *) return 2 ;;
  esac
}

runtime_write_plugin_stubs() {
  local stub_bin="$1"
  mkdir -p "$stub_bin"
  cat >"$stub_bin/codex" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "plugin --help" | "plugin marketplace --help") exit 0 ;;
  "plugin list --json") printf '%s\n' '{"installed":[],"available":[]}' ; exit 0 ;;
  "plugin marketplace list --json") printf '%s\n' '{"marketplaces":[]}' ; exit 0 ;;
esac
printf 'codex %s\n' "$*" >>"$PLUGIN_STUB_LOG"
SH
  cat >"$stub_bin/claude" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  "plugins list --json") printf '%s\n' '[]' ; exit 0 ;;
  "plugin marketplace list --json") printf '%s\n' '[]' ; exit 0 ;;
esac
printf 'claude %s\n' "$*" >>"$PLUGIN_STUB_LOG"
SH
  chmod +x "$stub_bin/codex" "$stub_bin/claude"
}

runtime_activate_product_registry() {
  local repo_root="$1"
  local product="$2"
  local live_home="$3"
  local state_home="$4"
  local artifacts_dir="$5"
  local stub_bin="$artifacts_dir/stub-bin"
  local log="$artifacts_dir/${product}.plugin-registry.log"

  runtime_write_plugin_stubs "$stub_bin"
  : >"$log"
  (
    export PATH="$stub_bin:$PATH"
    export PLUGIN_STUB_LOG="$log"
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$repo_root/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$repo_root"
    APPLY=1
    case "$product" in
      codex)
        preflight_codex_plugin_registry "$live_home"
        sync_codex_plugin_registry "$live_home" "$state_home"
        ;;
      claude)
        preflight_claude_plugin_registry "$live_home"
        sync_claude_plugin_registry "$live_home" "$state_home"
        ;;
    esac
  ) >"$artifacts_dir/${product}.plugin-registry.stdout.log" 2>&1

  # The registry helper above is isolated; the caller's product is unchanged.
  # shellcheck disable=SC2031
  python3 - "$repo_root" "$product" "$log" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
product = sys.argv[2]
log = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8").splitlines()
if product == "codex":
    manifest_path = root / "targets/codex/.agents/plugins/marketplace.json"
    prefix = "codex plugin add "
    suffix = ""
else:
    manifest_path = root / "targets/claude/.claude-plugin/marketplace.json"
    prefix = "claude plugin install "
    suffix = " --scope user"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
marketplace = manifest["name"]
expected = sorted(f"{item['name']}@{marketplace}{suffix}" for item in manifest["plugins"])
observed = sorted(line.removeprefix(prefix) for line in log if line.startswith(prefix))
assert expected and len(expected) == len(set(expected))
assert len(observed) == len(set(observed))
assert observed == expected, (product, observed, expected)
PY
}

runtime_remove_retired_surface() {
  local repo_root="$1"
  local product="$2"
  local live_home="$3"
  (
    # shellcheck disable=SC1091
    SYNC_RUNTIME_SURFACES_LIB=1 . "$repo_root/scripts/sync-runtime-surfaces.sh"
    SOURCE_ROOT="$repo_root"
    APPLY=1
    cleanup_retired_managed_product_links "$product" "$live_home"
  )
}

runtime_assert_operator_config() {
  local product="$1"
  local config_path="$2"
  case "$product" in
    codex)
      grep -q '^keep = true$' "$config_path"
      ;;
    claude)
      python3 - "$config_path" <<'PY'
import json
import pathlib
import sys

data = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["userKeep"] is True
PY
      ;;
  esac
}

runtime_convergence_product() {
  local repo_root="$1"
  local prior_root="$2"
  local tmp_root="$3"
  local product="$4"
  local artifacts_dir="$5"
  local live_home state_home config_path rollback_path baseline_surface operator_surface
  local idempotent_log public_summary baseline_skill_count

  live_home="$(runtime_live_home "$tmp_root" "$product")"
  state_home="$(runtime_state_home "$tmp_root" "$product")"
  config_path="$(runtime_product_config_path "$live_home" "$product")"
  baseline_surface="$artifacts_dir/${product}.baseline-managed-surface"
  operator_surface="$artifacts_dir/${product}.operator-owned"
  idempotent_log="$artifacts_dir/${product}.idempotent-install.log"
  public_summary="$artifacts_dir/${product}.portable-summary.json"
  mkdir -p "$live_home" "$state_home" "$artifacts_dir"

  case "$product" in
    codex)
      printf '[user]\nkeep = true\n' >"$config_path"
      rollback_path="$live_home/.agents/plugins/marketplace.json"
      ;;
    claude)
      printf '{"userKeep":true}\n' >"$config_path"
      rollback_path="$live_home/.claude-plugin/marketplace.json"
      ;;
  esac
  printf 'operator-owned\n' >"$live_home/operator-owned.txt"
  cp "$live_home/operator-owned.txt" "$operator_surface"

  runtime_install_product "$prior_root" "$tmp_root" "$product" "$artifacts_dir/baseline" || return 1
  baseline_skill_count="$(
    wc -l <"$artifacts_dir/baseline/${product}.observed-skills.txt" | tr -d '[:space:]'
  )"
  [ "$baseline_skill_count" = "66" ] || return 1
  runtime_assert_operator_config "$product" "$config_path" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1
  cp -L "$rollback_path" "$baseline_surface"

  agent-runtime render \
    --source-root "$repo_root" \
    --product "$product" >"$artifacts_dir/${product}.upgrade-render.log" 2>&1 || return 1
  agent-runtime install \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay \
    --apply >"$artifacts_dir/${product}.upgrade-first-apply.log" 2>&1 || return 1
  runtime_assert_operator_config "$product" "$config_path" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  runtime_remove_retired_surface "$repo_root" "$product" "$live_home" \
    >"$artifacts_dir/${product}.retired-cleanup-first.log" 2>&1 || return 1
  agent-runtime prune-stale \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --no-overlay \
    --apply --format json >"$artifacts_dir/${product}.prune-first.json" 2>&1 || return 1
  runtime_activate_product_registry \
    "$repo_root" "$product" "$live_home" "$state_home" "$artifacts_dir/head-first" || return 1
  runtime_install_product \
    "$repo_root" "$tmp_root" "$product" "$artifacts_dir/head-first" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  runtime_install_product \
    "$prior_root" "$tmp_root" "$product" "$artifacts_dir/rollback" || return 1
  runtime_activate_product_registry \
    "$prior_root" "$product" "$live_home" "$state_home" "$artifacts_dir/rollback" || return 1
  runtime_assert_operator_config "$product" "$config_path" || return 1
  cmp "$baseline_surface" "$rollback_path" || return 1
  [ "$(
    wc -l <"$artifacts_dir/rollback/${product}.observed-skills.txt" | tr -d '[:space:]'
  )" = "$baseline_skill_count" ] || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  agent-runtime install \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay \
    --apply >"$artifacts_dir/${product}.upgrade-second-apply.log" 2>&1 || return 1
  runtime_remove_retired_surface "$repo_root" "$product" "$live_home" \
    >"$artifacts_dir/${product}.retired-cleanup.log" 2>&1 || return 1
  test ! -e "$live_home/plugins/browser" || return 1
  test ! -e "$live_home/plugins/evidence" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  agent-runtime prune-stale \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --no-overlay \
    --apply --format json >"$artifacts_dir/${product}.prune.json" 2>&1 || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1
  runtime_activate_product_registry \
    "$repo_root" "$product" "$live_home" "$state_home" "$artifacts_dir" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1
  runtime_install_product "$repo_root" "$tmp_root" "$product" "$artifacts_dir/upgrade" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  agent-runtime install \
    --source-root "$repo_root" \
    --product "$product" \
    --live-home "$live_home" \
    --state-home "$state_home" \
    --no-overlay \
    --apply >"$idempotent_log" 2>&1 || return 1
  grep -q 'changes=0' "$idempotent_log" || return 1
  runtime_assert_operator_config "$product" "$config_path" || return 1
  cmp "$operator_surface" "$live_home/operator-owned.txt" || return 1

  python3 - \
    "$artifacts_dir/baseline/${product}.receipt-summary.json" \
    "$artifacts_dir/upgrade/${product}.receipt-summary.json" \
    "$public_summary" \
    "$RUNTIME_SMOKE_SKILL_COUNT" \
    "$baseline_skill_count" <<'PY'
import json
import pathlib
import re
import sys

baseline = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
receipt = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
skill_count = int(sys.argv[4])
baseline_skill_count = int(sys.argv[5])
assert baseline["source_revision"] != receipt["source_revision"]
assert baseline["managed_entry_count"] > receipt["managed_entry_count"]
assert baseline_skill_count == 66
assert skill_count == 26
summary = {
    "schema": "portable-convergence-summary.v1",
    "product": receipt["product"],
    "baseline_revision": baseline["source_revision"],
    "source_revision": receipt["source_revision"],
    "baseline_skill_count": baseline_skill_count,
    "skill_count": skill_count,
    "receipt_verified": receipt["verified"],
    "rollback_verified": True,
    "upgrade_verified": True,
    "retired_pruned": True,
    "registry_activated": True,
    "idempotent": True,
}
text = json.dumps(summary, sort_keys=True) + "\n"
for forbidden in (r"/Users/", r"/home/", r"ssh://", r"@[0-9]", r"token"):
    assert re.search(forbidden, text, re.I) is None, forbidden
pathlib.Path(sys.argv[3]).write_text(text, encoding="utf-8")
PY
}
