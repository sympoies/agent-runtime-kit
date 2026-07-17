#!/usr/bin/env bash

set -u

if [ "$#" -lt 3 ]; then
  echo "usage: expect-command-failure.sh <expected-message> <unexpected-message> <command> [args...]" >&2
  exit 64
fi

expected_message="$1"
unexpected_message="$2"
shift 2

if "$@"; then
  printf '%s\n' "$unexpected_message" >&2
  exit 1
fi

printf '%s\n' "$expected_message"
