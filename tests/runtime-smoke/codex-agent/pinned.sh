#!/usr/bin/env bash
# Run acceptance against the validated release, verifying Linux archive bytes.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
pin="$REPO_ROOT/docs/source/nils-cli-pin.yaml"
tag="$(sed -n 's/^  validated_tag: "\([^"]*\)"/\1/p' "$pin")"
case "$(uname -s):$(uname -m)" in
  Linux:x86_64) checksum_key=linux_amd64 ;;
  Linux:aarch64 | Linux:arm64) checksum_key=linux_arm64 ;;
  *)
    echo "codex-agent acceptance: use the released platform package at validated_tag; archive pins cover Linux only" >&2
    exit 2
    ;;
esac
checksum="$(sed -n "s/^    $checksum_key: \"\([^\"]*\)\"/\1/p" "$pin")"
[ -n "$tag" ] && [ -n "$checksum" ]
export NILS_RELEASE_SHA256="$checksum"
exec bash "$REPO_ROOT/scripts/dev/with-nils-version.sh" "release:$tag" -- "$@"
