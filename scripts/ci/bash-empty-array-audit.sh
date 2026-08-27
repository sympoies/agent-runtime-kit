#!/usr/bin/env bash
# Audit shell sources for array expansions that abort on macOS system bash.
#
# Compatibility: macOS system bash 3.2 and Linux bash.
#
# Under `set -u`, bash 3.2 treats `"${arr[@]}"` on an EMPTY array as an unbound
# variable and aborts. Bash 4.4+ does not, so the fault is invisible on Linux CI
# and only surfaces on a macOS host — which is exactly where these scripts and
# hooks run. `"${arr[@]+"${arr[@]}"}"` expands identically on every version and
# yields zero words when the array is empty, so it is always the safe spelling.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SELF_TEST=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/ci/bash-empty-array-audit.sh [--self-test]

Fails when a tracked shell source expands an array as `"${name[@]}"` without the
`"${name[@]+...}"` guard that macOS system bash 3.2 needs under `set -u`.

  --self-test  Prove the detector fires on a known-bad fixture and spares the
               guarded form, then exit.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --self-test)
      SELF_TEST=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      printf 'bash-empty-array-audit: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# The guarded form *contains* the unguarded spelling as a substring, so the
# guarded occurrences are removed before the remainder is searched.
scan() {
  python3 - "$@" <<'PY'
import pathlib
import re
import sys

GUARDED = re.compile(r'"\$\{([A-Za-z_][A-Za-z0-9_]*)\[@\]\+"\$\{\1\[@\]\}"\}"')
UNGUARDED = re.compile(r'"\$\{[A-Za-z_][A-Za-z0-9_]*\[@\]\}"')

# The detector has to spell both the bad and the guarded form, in its own
# documentation and in its self-test fixture, so it cannot audit itself.
SELF = "bash-empty-array-audit.sh"

findings = []
for root in sys.argv[1:]:
    for path in sorted(pathlib.Path(root).rglob("*.sh")):
        if not path.is_file() or path.name == SELF:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if UNGUARDED.search(GUARDED.sub("", line)):
                findings.append(f"{path}:{number}:{line.strip()}")
print("\n".join(findings))
PY
}

if [ "$SELF_TEST" -eq 1 ]; then
  fixture="$(mktemp -d)"
  trap 'rm -rf "$fixture"' EXIT
  printf 'bad=()\nprintf "%%s" "${bad[@]}"\n' >"$fixture/known-bad.sh"
  printf 'ok=()\nprintf "%%s" "${ok[@]+"${ok[@]}"}"\n' >"$fixture/known-good.sh"
  found="$(scan "$fixture")"
  if ! printf '%s\n' "$found" | grep -q 'known-bad.sh'; then
    echo "bash-empty-array-audit: self-test FAILED — detector missed the bad fixture" >&2
    exit 1
  fi
  if printf '%s\n' "$found" | grep -q 'known-good.sh'; then
    echo "bash-empty-array-audit: self-test FAILED — detector flagged the guarded form" >&2
    exit 1
  fi
  echo "bash-empty-array-audit: self-test OK"
  exit 0
fi

findings="$(scan "$REPO_ROOT/scripts" "$REPO_ROOT/core")"

if [ -n "$findings" ]; then
  echo "bash-empty-array-audit: FAIL — unguarded array expansions abort on macOS bash 3.2 under set -u:" >&2
  printf '%s\n' "$findings" >&2
  echo >&2
  echo 'Spell each one "${name[@]+"${name[@]}"}"; it is identical everywhere else' >&2
  echo 'and yields zero words when the array is empty.' >&2
  exit 1
fi

echo "bash-empty-array-audit: OK"
