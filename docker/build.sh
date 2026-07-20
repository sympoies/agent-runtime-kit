#!/usr/bin/env bash
# docker/build.sh — build the agent-runtime-kit image with the nils-cli version
# taken from docs/source/nils-cli-pin.yaml (the repo's authoritative validated
# packaging role). scripts/ci/all.sh admits the version policy at Position 1
# and verifies packaging digest consistency at Position 8. This keeps the
# packaged version single-sourced: bump validated_tag and the image follows.
#
# Usage:
#   docker/build.sh [-t TAG] [-n] [-- <extra docker build args>]
#
# Examples:
#   docker/build.sh                          # -> agent-runtime-kit:dev
#   docker/build.sh -t agent-runtime-kit:0.30.1
#   docker/build.sh -n                       # print the resolved command only
#   docker/build.sh -- --platform linux/amd64 --no-cache
#
# Compatibility: macOS system bash 3.2 and Linux bash. No bash-4 features.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="$REPO_ROOT/docs/source/nils-cli-pin.yaml"
DOCKERFILE="$REPO_ROOT/docker/Dockerfile"

IMAGE_TAG="agent-runtime-kit:dev"
DRY_RUN=0
EXTRA=""

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    -t | --tag)
      [ "$#" -ge 2 ] || {
        echo "error: $1 requires a value" >&2
        exit 2
      }
      IMAGE_TAG="$2"
      shift 2
      ;;
    -n | --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA="$*"
      break
      ;;
    *)
      echo "error: unknown argument: $1 (use -- to pass docker build flags)" >&2
      exit 2
      ;;
  esac
done

[ -f "$PIN_FILE" ] || {
  echo "error: pin file not found: $PIN_FILE" >&2
  exit 1
}

# Resolve validated_tag (e.g. "v1.25.0"). Prefer yq; fall back to sed so the
# script works on a host without yq.
PIN=""
NILS_SHA256_AMD64=""
NILS_SHA256_ARM64=""
if command -v yq >/dev/null 2>&1; then
  PIN="$(yq -r '.nils_cli.validated_tag' "$PIN_FILE" 2>/dev/null || true)"
  NILS_SHA256_AMD64="$(yq -r '.nils_cli.release_sha256.linux_amd64' "$PIN_FILE" 2>/dev/null || true)"
  NILS_SHA256_ARM64="$(yq -r '.nils_cli.release_sha256.linux_arm64' "$PIN_FILE" 2>/dev/null || true)"
fi
if [ -z "$PIN" ] || [ "$PIN" = "null" ]; then
  PIN="$(sed -n -E 's/^[[:space:]]*validated_tag:[[:space:]]*"?([^"#]+)"?.*/\1/p' "$PIN_FILE" | head -1)"
  PIN="$(printf '%s' "$PIN" | tr -d '[:space:]')"
fi
if [ -z "$NILS_SHA256_AMD64" ] || [ "$NILS_SHA256_AMD64" = "null" ]; then
  NILS_SHA256_AMD64="$(sed -n -E 's/^[[:space:]]*linux_amd64:[[:space:]]*"?([0-9a-f]{64})"?.*/\1/p' "$PIN_FILE" | head -1)"
fi
if [ -z "$NILS_SHA256_ARM64" ] || [ "$NILS_SHA256_ARM64" = "null" ]; then
  NILS_SHA256_ARM64="$(sed -n -E 's/^[[:space:]]*linux_arm64:[[:space:]]*"?([0-9a-f]{64})"?.*/\1/p' "$PIN_FILE" | head -1)"
fi
[ -n "$PIN" ] || {
  echo "error: could not read nils_cli.validated_tag from $PIN_FILE" >&2
  exit 1
}
[ -n "$NILS_SHA256_AMD64" ] && [ -n "$NILS_SHA256_ARM64" ] || {
  echo "error: could not read nils_cli.release_sha256 linux digests from $PIN_FILE" >&2
  exit 1
}

echo "nils-cli validated : $PIN  (from docs/source/nils-cli-pin.yaml)"
echo "nils-cli sha : linux/amd64=$NILS_SHA256_AMD64 linux/arm64=$NILS_SHA256_ARM64"
echo "image tag    : $IMAGE_TAG"

# shellcheck disable=SC2086  # EXTRA is an intentional word-split passthrough.
set -- docker build -f "$DOCKERFILE" \
  --build-arg "NILS_CLI_VERSION=$PIN" \
  --build-arg "NILS_CLI_SHA256_AMD64=$NILS_SHA256_AMD64" \
  --build-arg "NILS_CLI_SHA256_ARM64=$NILS_SHA256_ARM64" \
  -t "$IMAGE_TAG" \
  $EXTRA \
  "$REPO_ROOT"

printf '+ '
printf '%q ' "$@"
printf '\n'
if [ "$DRY_RUN" = "1" ]; then
  exit 0
fi
exec "$@"
