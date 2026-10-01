# shellcheck shell=bash
# scripts/lib/runtime-python.sh — resolve the Python interpreter host scripts use.
#
# Sourced by scripts/setup.sh and scripts/sync-runtime-surfaces.sh. Their
# inline programs need Python 3.11+ (tomllib), and macOS login shells often
# resolve `python3` to the system 3.9 interpreter ahead of Homebrew's, so never
# trust bare `python3` on PATH.
#
# Compatibility: macOS system bash 3.2 and Linux bash.
#
# Search order:
#   1. AGENT_RUNTIME_PYTHON (must itself be 3.11+; never silently skipped)
#   2. python3.14 ... python3.11 on PATH
#   3. Homebrew python3 at fixed prefixes (AGENT_RUNTIME_PYTHON_FALLBACKS
#      replaces this list; tests set it empty to stay hermetic)
#   4. python3 on PATH, only when it is new enough

RUNTIME_PYTHON=""
RUNTIME_PYTHON_REJECTED=""

runtime_python_is_supported() {
  "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
}

runtime_python_note_rejected() {
  local version
  version="$("$1" --version 2>&1 | head -n 1)" || version=""
  RUNTIME_PYTHON_REJECTED="${RUNTIME_PYTHON_REJECTED}  - $1${2:+ ($2)}: ${version:-not runnable}
"
}

# Set RUNTIME_PYTHON to a Python 3.11+ interpreter; return 1 when none exists.
resolve_runtime_python() {
  local candidate
  local path
  local fallbacks

  RUNTIME_PYTHON_REJECTED=""
  if [ -n "${AGENT_RUNTIME_PYTHON:-}" ]; then
    if runtime_python_is_supported "$AGENT_RUNTIME_PYTHON"; then
      RUNTIME_PYTHON="$AGENT_RUNTIME_PYTHON"
      return 0
    fi
    runtime_python_note_rejected "$AGENT_RUNTIME_PYTHON" AGENT_RUNTIME_PYTHON
    return 1
  fi

  fallbacks="${AGENT_RUNTIME_PYTHON_FALLBACKS-${HOMEBREW_PREFIX:+$HOMEBREW_PREFIX/bin/python3 }/opt/homebrew/bin/python3 /usr/local/bin/python3}"
  for candidate in python3.14 python3.13 python3.12 python3.11 $fallbacks python3; do
    case "$candidate" in
      /*) [ -x "$candidate" ] || continue; path="$candidate" ;;
      *) path="$(command -v "$candidate" 2>/dev/null)" || continue ;;
    esac
    if runtime_python_is_supported "$path"; then
      RUNTIME_PYTHON="$path"
      return 0
    fi
    runtime_python_note_rejected "$path"
  done
  return 1
}

runtime_python_missing_message() {
  printf 'error: Python 3.11+ is required, but no suitable interpreter was found.\n' >&2
  if [ -n "$RUNTIME_PYTHON_REJECTED" ]; then
    printf 'Rejected candidates:\n%s' "$RUNTIME_PYTHON_REJECTED" >&2
  fi
  cat >&2 <<'EOF'
Install Python 3.11+ (macOS: `brew install python@3`; Linux: your distribution's
python3 package), or set AGENT_RUNTIME_PYTHON=/path/to/python3.11-or-newer.
Changing shell PATH order is not required.
EOF
}

# Resolve once or stop the calling script before it mutates anything.
require_runtime_python() {
  [ -n "$RUNTIME_PYTHON" ] && return 0
  if ! resolve_runtime_python; then
    runtime_python_missing_message
    return 1
  fi
}

# Run the resolved interpreter, resolving lazily for library-mode callers.
runtime_python() {
  require_runtime_python || return $?
  "$RUNTIME_PYTHON" "$@"
}
