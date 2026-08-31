#!/usr/bin/env bash
# Search the development log (docs/source/devlog/*.md).
# Usage: scripts/devlog-search.sh <term> [YYYY-MM]
#   <term>    case-insensitive literal search string (required)
#   YYYY-MM   restrict to one month file (optional)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="docs/source/devlog"
term="${1:-}"
month="${2:-}"
USAGE="usage: scripts/devlog-search.sh <term> [YYYY-MM]"

if ! cd "$ROOT"; then
  echo "unable to enter the repository root" >&2
  exit 1
fi

if [ "$#" -gt 2 ] || [ -z "$term" ]; then
  echo "$USAGE" >&2
  exit 2
fi

if [ -n "$month" ]; then
  if [[ ! "$month" =~ ^[0-9]{4}-(0[1-9]|1[0-2])$ ]]; then
    echo "$USAGE" >&2
    exit 2
  fi
  files=("$DIR/$month.md")
else
  files=("$DIR"/????-??.md)
fi

if [ ! -e "${files[0]}" ]; then
  echo "no devlog month files found under $DIR" >&2
  exit 1
fi

if ! grep -n -i -F -- "$term" "${files[@]}"; then
  echo "(no matches for '$term')" >&2
  exit 1
fi
