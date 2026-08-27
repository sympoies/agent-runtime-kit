#!/usr/bin/env bash
# Audit shell sources for constructs that fail on macOS but pass on Linux CI.
#
# Compatibility: macOS system bash 3.2 and Linux bash.
#
# Every rule here guards the same blind spot: this repository's CI runs on Linux
# with GNU tooling and bash 5, while its scripts and hooks run on macOS with BSD
# tooling and system bash 3.2. A construct that only GNU or only bash 4 accepts
# is invisible to CI and fatal on the host.
#
#   empty-array  Under `set -u`, bash 3.2 treats `"${arr[@]}"` on an EMPTY array
#                as an unbound variable and aborts; bash 4.4+ does not.
#                `"${arr[@]+"${arr[@]}"}"` expands identically everywhere and
#                yields zero words when empty.
#   gnu-only     `find -printf` and `stat -c` do not exist in the BSD versions
#                macOS ships. Both have portable spellings, and both have
#                already shipped here as silent macOS-only failures.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SELF_TEST=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/ci/macos-portability-audit.sh [--self-test]

Fails when a tracked shell source uses a construct that macOS cannot run:

  * an array expanded as `"${name[@]}"` without the `"${name[@]+...}"` guard
    that system bash 3.2 needs under `set -u`;
  * `find -printf` or `stat -c`, which exist only in the GNU versions.

  --self-test  Prove each detector fires on a known-bad fixture and spares the
               portable form, then exit.
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
      printf 'macos-portability-audit: unknown argument: %s\n' "$1" >&2
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
GNU_ONLY = (
    ("find -printf", re.compile(r'(?<![-\w])-printf(?![-\w])')),
    ("stat -c", re.compile(r'\bstat\s+-c\b')),
)

# The detector has to spell both the bad and the guarded form, in its own
# documentation and in its self-test fixture, so it cannot audit itself.
SELF = "macos-portability-audit.sh"

findings = []
for root in sys.argv[1:]:
    for path in sorted(pathlib.Path(root).rglob("*.sh")):
        if not path.is_file() or path.name == SELF:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            # A full-line comment is prose, including the prose that documents
            # these very rules.
            if line.lstrip().startswith("#"):
                continue
            if UNGUARDED.search(GUARDED.sub("", line)):
                findings.append(f"{path}:{number}: empty-array: {line.strip()}")
            for label, rule in GNU_ONLY:
                if rule.search(line):
                    findings.append(f"{path}:{number}: gnu-only ({label}): {line.strip()}")
print("\n".join(findings))
PY
}

if [ "$SELF_TEST" -eq 1 ]; then
  fixture="$(mktemp -d)"
  trap 'rm -rf "$fixture"' EXIT
  printf 'bad=()\nprintf "%%s" "${bad[@]}"\n' >"$fixture/known-bad-array.sh"
  printf 'find . -printf "%%%%f\\n"\n' >"$fixture/known-bad-find.sh"
  printf "stat -c '%%%%a' x\n" >"$fixture/known-bad-stat.sh"
  printf 'ok=()\nprintf "%%s" "${ok[@]+"${ok[@]}"}"\nfind . -print\nstat -f "%%%%Lp" x\n' \
    >"$fixture/known-good.sh"
  found="$(scan "$fixture")"
  for bad in known-bad-array known-bad-find known-bad-stat; do
    if ! printf '%s\n' "$found" | grep -q "$bad.sh"; then
      echo "macos-portability-audit: self-test FAILED — detector missed $bad" >&2
      exit 1
    fi
  done
  if printf '%s\n' "$found" | grep -q 'known-good.sh'; then
    echo "macos-portability-audit: self-test FAILED — detector flagged a portable form" >&2
    exit 1
  fi
  echo "macos-portability-audit: self-test OK"
  exit 0
fi

# Scoped to the shipped scripts and hooks. The runtime-smoke suite under tests/
# is excluded on purpose: it embeds shell fixtures as string literals, where the
# same spelling is data rather than code, and it already runs on macOS directly,
# so a real fault there fails the probe instead of hiding.
findings="$(scan "$REPO_ROOT/scripts" "$REPO_ROOT/core")"

if [ -n "$findings" ]; then
  echo "macos-portability-audit: FAIL — these do not run on macOS:" >&2
  printf '%s\n' "$findings" >&2
  echo >&2
  echo 'empty-array: spell it "${name[@]+"${name[@]}"}" — identical everywhere' >&2
  echo '             else, and zero words when the array is empty.' >&2
  echo 'gnu-only:    `find -print` with the prefix stripped by sed replaces' >&2
  echo '             `-printf`; `stat -f` is the BSD spelling of `stat -c`.' >&2
  exit 1
fi

echo "macos-portability-audit: OK"
