#!/usr/bin/env bash
set -euo pipefail

required_version=v3.14.1
release_url=https://github.com/mvdan/sh/releases/tag/v3.14.1

if ! actual_version="$(shfmt --version 2>/dev/null)"; then
  printf 'shfmt qualification: require %s on PATH; install from %s\n' \
    "$required_version" "$release_url" >&2
  exit 1
fi

if [ "$actual_version" != "$required_version" ]; then
  printf 'shfmt qualification: require %s, found %s; install from %s\n' \
    "$required_version" "$actual_version" "$release_url" >&2
  exit 1
fi

printf 'shfmt qualification: using %s\n' "$actual_version" >&2
exec shfmt -i 2 -ci -d "$@"
