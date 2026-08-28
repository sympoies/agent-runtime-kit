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
#   heredoc-in-  bash 3.2 does not treat the body of a heredoc opened inside
#   substitution `$( … )` as opaque: it scans the body as shell text, counting
#                parentheses and tracking quote state. An embedded program with
#                an unbalanced bracket or a lone apostrophe therefore breaks the
#                enclosing substitution, and the whole file stops parsing. Read
#                the program with a top-level heredoc and pass it on stdin.
#   bash32-parse The exact oracle: when the host has a bash 3.x, every tracked
#                shell source must parse under it.
#
# The two rules cover different ground on purpose. `bash32-parse` is exact and
# whole-repo but only runs where a bash 3.x exists, so a Linux-only CI run never
# sees it. `heredoc-in-substitution` is static and runs anywhere, and is scoped
# to `core/hooks` — the files the host's system bash executes on every prompt
# and tool call, where a parse failure is both silent (hooks fail soft) and
# total. `scripts/` and `tests/` still contain the construct with bodies that
# happen to balance; they are covered by the parse oracle rather than a ban that
# would demand rewriting them all.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SELF_TEST=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/ci/macos-portability-audit.sh [--self-test]

Fails when a tracked shell source uses a construct that macOS cannot run:

  * an array expanded as `"${name[@]}"` without the `"${name[@]+...}"` guard
    that system bash 3.2 needs under `set -u`;
  * `find -printf` or `stat -c`, which exist only in the GNU versions;
  * a heredoc opened inside `$( … )` under core/hooks, whose body bash 3.2
    scans as shell text instead of treating it as opaque.

When the host has a bash 3.x, every tracked shell source must also parse under
it. That check is skipped, with a notice, where no bash 3.x exists.

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

# A separate detector, because this one needs a stateful walk rather than a
# per-line regex: heredoc bodies must be consumed so their text never reaches
# the scanner, and `$(` nests.
scan_heredoc() {
  python3 - "$@" <<'PY'
import pathlib
import sys

def heredoc_opens_in_substitution(text):
    """Line numbers where a heredoc is opened inside an unclosed `$( … )`.

    bash 3.2 does not treat such a heredoc's body as opaque: it scans it as
    shell text, so an unbalanced bracket or a lone apostrophe in an embedded
    program breaks the enclosing substitution.
    """
    lines = text.splitlines()
    findings = []
    depth = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        pending = []
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                end = line.find("'", i + 1)
                i = n if end < 0 else end + 1
                continue
            if ch == '"':
                # Command substitution is still live inside double quotes, so
                # step through rather than skipping to the closing quote.
                j = i + 1
                while j < n:
                    if line[j] == "\\":
                        j += 2
                        continue
                    if line[j] == '"':
                        break
                    if line.startswith("$(", j):
                        break
                    j += 1
                if j < n and line.startswith("$(", j):
                    i = j
                    continue
                i = n if j >= n else j + 1
                continue
            if ch == "#" and (i == 0 or line[i - 1].isspace()):
                break
            if line.startswith("$((", i):
                end = line.find("))", i)
                i = n if end < 0 else end + 2
                continue
            if line.startswith("$(", i):
                depth += 1
                i += 2
                continue
            if ch == ")" and depth > 0:
                depth -= 1
                i += 1
                continue
            if line.startswith("<<<", i):
                i += 3
                continue
            if line.startswith("<<", i):
                j = i + 2
                if j < n and line[j] == "-":
                    j += 1
                while j < n and line[j].isspace():
                    j += 1
                quote = ""
                if j < n and line[j] in "'\"":
                    quote = line[j]
                    j += 1
                start = j
                while j < n and (line[j].isalnum() or line[j] in "_-."):
                    j += 1
                delimiter = line[start:j]
                if quote and j < n and line[j] == quote:
                    j += 1
                if delimiter:
                    pending.append(delimiter)
                    if depth > 0:
                        findings.append((index + 1, line.strip()))
                i = j
                continue
            i += 1
        # Consume each heredoc body so its text never reaches the scanner.
        index += 1
        for delimiter in pending:
            while index < len(lines) and lines[index].strip() != delimiter:
                index += 1
            index += 1
    return findings


results = []
for root in sys.argv[1:]:
    for path in sorted(pathlib.Path(root).rglob("*.sh")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, snippet in heredoc_opens_in_substitution(text):
            results.append(f"{path}:{number}: heredoc-in-substitution: {snippet}")
print("\n".join(results))
PY
}

# The exact oracle. `bash -n` under a real bash 3.x is the only check that sees
# every 3.2-only construct rather than the ones a rule was written for; it is
# also the check a Linux CI run cannot perform.
bash32_parse() {
  local shell="$1"
  local failures=""
  local file
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    [ -f "$REPO_ROOT/$file" ] || continue
    if ! output="$("$shell" -n "$REPO_ROOT/$file" 2>&1)"; then
      failures="${failures}${file}:
$(printf '%s\n' "$output" | sed 's/^/    /')
"
    fi
  done <<EOF
$(git -C "$REPO_ROOT" ls-files '*.sh' 2>/dev/null || true)
EOF
  printf '%s' "$failures"
}

# The system bash is the one whose version matters; a newer bash earlier on PATH
# is not what a `#!/usr/bin/env bash` hook gets when /bin/bash comes first.
bash32_binary() {
  if [ -x /bin/bash ] && /bin/bash --version 2>/dev/null | head -1 | grep -q 'version 3\.'; then
    echo /bin/bash
  fi
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

  # The heredoc detector gets its own fixtures: the bad form, plus the three
  # spellings it must NOT flag — a heredoc at top level, a here-string (`<<<`,
  # whose body is never delimiter-scanned), and the hoisted rewrite that
  # replaces the bad form.
  heredoc_fixture="$(mktemp -d)"
  trap 'rm -rf "$fixture" "$heredoc_fixture"' EXIT
  # The body carries the unbalanced bracket that makes this fatal, so the
  # static rule and the parse oracle are proven on one identical case.
  printf 'x="$(cat <<%sEOF%s\nbody (\nEOF\n)"\n' "'" "'" \
    >"$heredoc_fixture/known-bad-heredoc.sh"
  printf 'cat <<%sEOF%s\nbody (\nEOF\ny="$(printf %s%%s%s "$x")"\n' "'" "'" '"' '"' \
    >"$heredoc_fixture/known-good-toplevel.sh"
  printf 'IFS= read -r -d %s%s prog <<%sEOF%s || true\nbody (\nEOF\nz="$(python3 - <<<"$prog")"\n' \
    "'" "'" "'" "'" >"$heredoc_fixture/known-good-hoisted.sh"
  heredoc_found="$(scan_heredoc "$heredoc_fixture")"
  if ! printf '%s\n' "$heredoc_found" | grep -q 'known-bad-heredoc.sh'; then
    echo "macos-portability-audit: self-test FAILED — missed heredoc-in-substitution" >&2
    exit 1
  fi
  if printf '%s\n' "$heredoc_found" | grep -q 'known-good-'; then
    echo "macos-portability-audit: self-test FAILED — heredoc rule flagged a portable form" >&2
    printf '%s\n' "$heredoc_found" >&2
    exit 1
  fi

  # And the oracle must actually reject the construct it exists for, so a
  # skipped bash 3.x is visibly a skip rather than a silent pass.
  self_bash32="$(bash32_binary)"
  if [ -n "$self_bash32" ]; then
    if "$self_bash32" -n "$heredoc_fixture/known-bad-heredoc.sh" 2>/dev/null; then
      echo "macos-portability-audit: self-test FAILED — the parse oracle accepted" >&2
      echo "  the known-bad heredoc fixture, so it is not testing what it claims." >&2
      exit 1
    fi
    if ! "$self_bash32" -n "$heredoc_fixture/known-good-hoisted.sh" 2>/dev/null; then
      echo "macos-portability-audit: self-test FAILED — the parse oracle rejected" >&2
      echo "  the hoisted rewrite this audit tells callers to use." >&2
      exit 1
    fi
    echo "macos-portability-audit: self-test OK (bash 3.x oracle available)"
  else
    echo "macos-portability-audit: self-test OK (no bash 3.x; parse oracle skipped)"
  fi
  exit 0
fi

# Scoped to the shipped scripts and hooks. The runtime-smoke suite under tests/
# is excluded on purpose: it embeds shell fixtures as string literals, where the
# same spelling is data rather than code, and it already runs on macOS directly,
# so a real fault there fails the probe instead of hiding.
findings="$(scan "$REPO_ROOT/scripts" "$REPO_ROOT/core")"

# Scoped to the hooks: see the header for why the ban stops there.
heredoc_findings="$(scan_heredoc "$REPO_ROOT/core/hooks")"
if [ -n "$heredoc_findings" ]; then
  findings="${findings:+$findings
}$heredoc_findings"
fi

bash32="$(bash32_binary)"
if [ -n "$bash32" ]; then
  parse_failures="$(bash32_parse "$bash32")"
  if [ -n "$parse_failures" ]; then
    echo "macos-portability-audit: FAIL — these do not parse under $bash32:" >&2
    printf '%s' "$parse_failures" >&2
    exit 1
  fi
else
  echo "macos-portability-audit: no bash 3.x here; parse oracle skipped." >&2
fi

if [ -n "$findings" ]; then
  echo "macos-portability-audit: FAIL — these do not run on macOS:" >&2
  printf '%s\n' "$findings" >&2
  echo >&2
  echo 'empty-array: spell it "${name[@]+"${name[@]}"}" — identical everywhere' >&2
  echo '             else, and zero words when the array is empty.' >&2
  echo 'gnu-only:    `find -print` with the prefix stripped by sed replaces' >&2
  echo '             `-printf`; `stat -f` is the BSD spelling of `stat -c`.' >&2
  echo 'heredoc-in-substitution: read the program with a top-level heredoc into' >&2
  echo '             a variable, then pass it on stdin with `<<<"$var"`.' >&2
  exit 1
fi

echo "macos-portability-audit: OK"
