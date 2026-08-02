#!/usr/bin/env bash
# Offline smoke coverage for scripts/release.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ARTIFACTS_DIR="${ARTIFACTS_DIR:-${CLAUDE_KIT_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit}/out/tests/release-script-smoke}"
rm -rf "$ARTIFACTS_DIR"
mkdir -p "$ARTIFACTS_DIR/bin"

cat >"$ARTIFACTS_DIR/bin/git" <<EOF
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  rev-parse)
    case "\${2:-}" in
      --show-toplevel)
        printf '%s\n' "$REPO_ROOT"
        ;;
      HEAD)
        printf '%s\n' "2222222222222222222222222222222222222222"
        ;;
      *)
        echo "git stub: unexpected rev-parse args: \$*" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "git stub: unexpected args: \$*" >&2
    exit 2
    ;;
esac
EOF

cat >"$ARTIFACTS_DIR/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  printf '%s\n' "sympoies/agent-runtime-kit"
  exit 0
fi

if [ "$1" = "release" ] && [ "$2" = "view" ]; then
  case " $* " in
    *" --json url "*)
      printf '%s\n' "https://github.com/sympoies/agent-runtime-kit/releases/tag/v2026.06.04"
      exit 0
      ;;
    *)
      exit 1
      ;;
  esac
fi

if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  printf '%s\n' "created"
  exit 0
fi

if [ "$1" = "run" ] && [ "$2" = "list" ]; then
  cat <<'JSON'
[
  {
    "databaseId": 111,
    "headSha": "1111111111111111111111111111111111111111",
    "url": "https://github.com/sympoies/agent-runtime-kit/actions/runs/111"
  },
  {
    "databaseId": 222,
    "headSha": "2222222222222222222222222222222222222222",
    "url": "https://github.com/sympoies/agent-runtime-kit/actions/runs/222"
  }
]
JSON
  exit 0
fi

if [ "$1" = "run" ] && [ "$2" = "view" ]; then
  case "$3" in
    222)
      printf '%s\n' "https://github.com/sympoies/agent-runtime-kit/actions/runs/222"
      exit 0
      ;;
    *)
      echo "gh stub: stale run selected: $3" >&2
      exit 3
      ;;
  esac
fi

if [ "$1" = "run" ] && [ "$2" = "watch" ]; then
  [ "$3" = "222" ] || {
    echo "gh stub: stale run watched: $3" >&2
    exit 3
  }
  printf '%s\n' "watched 222"
  exit 0
fi

echo "gh stub: unexpected args: $*" >&2
exit 2
EOF

chmod +x "$ARTIFACTS_DIR/bin/git" "$ARTIFACTS_DIR/bin/gh"

output="$ARTIFACTS_DIR/release-script.out"
PATH="$ARTIFACTS_DIR/bin:$PATH" \
  bash "$REPO_ROOT/scripts/release.sh" \
  --execute \
  --version v2026.06.04 \
  --skip-main-check \
  --skip-clean-check \
  --skip-public-verify \
  --timeout 1 \
  >"$output" 2>&1

grep -q "actions/runs/222" "$output"
if grep -q "actions/runs/111" "$output"; then
  echo "release-script smoke: stale run was selected" >&2
  cat "$output" >&2
  exit 1
fi

printf 'release-script smoke: OK artifacts=%s\n' "$ARTIFACTS_DIR"
