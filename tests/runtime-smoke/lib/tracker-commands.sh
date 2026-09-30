#!/usr/bin/env bash
# Which program-tracker path a runtime-smoke case must exercise.
#
# `forge-cli issue tracker` first shipped after the pin's minimum_supported_tag,
# so the exact-minimum lane takes the manual path. Any newer forge-cli must
# ship the commands: a failing probe there is a failure, never a fallback.

# Succeed when dotted version $1 is lower than or equal to $2.
tracker_commands_version_le() {
  local IFS=.
  local -a left right
  local i l r
  read -r -a left <<<"$1"
  read -r -a right <<<"$2"
  for i in 0 1 2; do
    l="${left[$i]:-0}"
    r="${right[$i]:-0}"
    if ((10#$l < 10#$r)); then
      return 0
    fi
    if ((10#$l > 10#$r)); then
      return 1
    fi
  done
  return 0
}

# Print `tracker` when the commands are available, `manual` when forge-cli is
# at or below the supported minimum and lacks them, and `missing` otherwise
# (including an unreadable version), which the caller must treat as a failure.
tracker_commands_mode() {
  local pin="$REPO_ROOT/docs/source/nils-cli-pin.yaml"
  local minimum installed
  if forge-cli issue tracker --help >/dev/null 2>&1; then
    echo tracker
    return 0
  fi
  minimum="$(sed -n -E 's/^[[:space:]]*minimum_supported_tag:[[:space:]]*"?v?([0-9]+\.[0-9]+\.[0-9]+)"?.*/\1/p' "$pin" | head -1)"
  installed="$(forge-cli --version 2>/dev/null | sed -n -E 's/^forge-cli ([0-9]+\.[0-9]+\.[0-9]+).*/\1/p' | head -1)"
  if [ -n "$minimum" ] && [ -n "$installed" ] &&
    tracker_commands_version_le "$installed" "$minimum"; then
    echo manual
  else
    echo missing
  fi
}
