#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create-project-skill.sh <skill-name> [options]
  create-project-skill.sh --bridge-only [options]

Options:
  --description TEXT     Seed the generated SKILL.md description.
  --target both|codex    Default is both. Claude-only targets are unsupported.
  --codex-only           Shorthand for --target codex.
  --with-script          Create scripts/<skill-name>.sh.
  --with-tests           Create tests/.
  --with-references      Create references/.
  --with-fixtures        Create fixtures/.
  --with-bin             Create bin/.
  --with-wrapper NAME    Create .agents/scripts/NAME.sh wrapper.
  --with-pre-pr-stub     Create .agents/scripts/pre-pr.sh when missing.
  --bridge-only          Only create or verify .claude/skills bridge.
  --dry-run              Print planned actions without writing files.
  -h, --help             Show this help.

Removed flags:
  --target claude, --claude-only, and --link-only are not supported.
USAGE
}

die() {
  echo "create-project-skill: error: $*" >&2
  exit 1
}

usage_error() {
  echo "create-project-skill: error: $*" >&2
  usage >&2
  exit 2
}

is_skill_name() {
  case "$1" in
    "" | -* | *- | *[!a-z0-9-]*)
      return 1
      ;;
  esac
  case "$1" in
    project-?* | private-?*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_command_name() {
  case "$1" in
    "" | -* | *- | */* | *[!a-z0-9-]*)
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

title_from_name() {
  printf '%s' "$1" |
    awk -F- '{
      for (i = 1; i <= NF; i++) {
        $i = toupper(substr($i, 1, 1)) substr($i, 2)
      }
      out = $1
      for (i = 2; i <= NF; i++) out = out " " $i
      print out
    }'
}

write_skill_md() {
  local path="$1"
  local skill="$2"
  local description="$3"
  local heading
  heading="$(title_from_name "$skill")"

  cat >"$path" <<SKILL_EOF
---
name: $skill
description: >
  $description
argument-hint: "<arg-shape>"
allowed-tools: Bash, Read
---

# $heading

TODO: short paragraph describing what this project-local skill orchestrates and
when the user should invoke it.

## Contract

Prereqs:

- TODO: required commands, tools, git work tree conditions, and project state.

Inputs:

- Required:
  - \`<input>\` - TODO
- Optional:
  - \`<option>\` - TODO

Outputs:

- TODO: list the concrete things this skill reads, mutates, or produces.

Exit codes:

- \`0\`: success
- \`1\`: command failed or a prerequisite is missing
- \`2\`: usage error or invalid inputs

Failure modes:

- TODO: enumerate the conditions under which this skill aborts.

## Scripts

- Optional project-local helper scripts live under \`scripts/\`.

## Workflow

1. TODO: step.
2. TODO: step.

## Boundary

This is a project-local skill. It must not mutate runtime-kit manifests,
rendered product output, global runtime homes, credentials, sessions, or cache
state.
SKILL_EOF
}

write_skill_script() {
  local path="$1"
  local skill="$2"

  cat >"$path" <<SCRIPT_EOF
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  $skill.sh [options]

Options:
  -h, --help   Show this help.
USAGE
}

while [ "\$#" -gt 0 ]; do
  case "\${1:-}" in
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: \$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

echo "$skill.sh: not yet implemented" >&2
exit 1
SCRIPT_EOF
}

write_wrapper() {
  local path="$1"
  local skill="$2"

  cat >"$path" <<WRAPPER_EOF
#!/usr/bin/env bash
set -euo pipefail

repo_root="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/../.." && pwd)"
exec "\$repo_root/.agents/skills/$skill/scripts/$skill.sh" "\$@"
WRAPPER_EOF
}

write_pre_pr_stub() {
  local path="$1"

  cat >"$path" <<'PREPR_EOF'
#!/usr/bin/env bash
set -euo pipefail

echo ".agents/scripts/pre-pr.sh: fill in this project's validation gate" >&2
exit 1
PREPR_EOF
}

note_action() {
  printf '%s\n' "$*"
}

name=""
description="TODO: one-line description of what this project-local skill does."
target="both"
target_set=false
bridge_only=false
dry_run=false
with_script=false
with_tests=false
with_references=false
with_fixtures=false
with_bin=false
with_pre_pr=false
wrapper_name=""

while [ "$#" -gt 0 ]; do
  case "${1:-}" in
    --description)
      [ "$#" -ge 2 ] || usage_error "--description requires text"
      description="$2"
      shift 2
      ;;
    --target)
      [ "$#" -ge 2 ] || usage_error "--target requires both|codex"
      case "$2" in
        both | codex)
          target="$2"
          target_set=true
          ;;
        claude)
          usage_error "--target claude is unsupported; use --bridge-only for existing skills"
          ;;
        *)
          usage_error "unsupported --target value: $2"
          ;;
      esac
      shift 2
      ;;
    --codex-only)
      if [ "$target_set" = true ] && [ "$target" != "codex" ]; then
        usage_error "--codex-only conflicts with --target $target"
      fi
      target="codex"
      target_set=true
      shift
      ;;
    --claude-only)
      usage_error "--claude-only is unsupported; use --bridge-only for existing skills"
      ;;
    --link-only)
      usage_error "--link-only was removed; use --bridge-only"
      ;;
    --with-script)
      with_script=true
      shift
      ;;
    --with-tests)
      with_tests=true
      shift
      ;;
    --with-references)
      with_references=true
      shift
      ;;
    --with-fixtures)
      with_fixtures=true
      shift
      ;;
    --with-bin)
      with_bin=true
      shift
      ;;
    --with-wrapper)
      [ "$#" -ge 2 ] || usage_error "--with-wrapper requires a command name"
      wrapper_name="$2"
      shift 2
      ;;
    --with-pre-pr-stub)
      with_pre_pr=true
      shift
      ;;
    --bridge-only)
      bridge_only=true
      shift
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    -*)
      usage_error "unknown flag: $1"
      ;;
    *)
      if [ -n "$name" ]; then
        usage_error "unexpected positional argument: $1"
      fi
      name="$1"
      shift
      ;;
  esac
done

if [ -n "$name" ] && ! is_skill_name "$name"; then
  usage_error "skill name must be lowercase kebab-case and start with 'project-' or 'private-'"
fi
if [ -n "$wrapper_name" ] && ! is_command_name "$wrapper_name"; then
  usage_error "wrapper name must be lowercase kebab-case text"
fi
if [ "$bridge_only" = true ] && [ "$target" = "codex" ]; then
  usage_error "--bridge-only conflicts with --target codex"
fi
if [ "$bridge_only" = true ]; then
  if [ "$with_script" = true ] || [ "$with_tests" = true ] ||
    [ "$with_references" = true ] || [ "$with_fixtures" = true ] ||
    [ "$with_bin" = true ]; then
    usage_error "--bridge-only cannot create skill support folders"
  fi
fi
if [ "$bridge_only" = true ] && [ -n "$wrapper_name" ] && [ -z "$name" ]; then
  usage_error "--with-wrapper in bridge-only mode requires a skill name"
fi
if [ "$bridge_only" = false ] && [ -z "$name" ]; then
  usage >&2
  exit 2
fi
if [ -n "$wrapper_name" ]; then
  with_script=true
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || die "must run inside a git work tree"
cd "$repo_root"

if [ "$bridge_only" = true ]; then
  [ -d ".agents/skills" ] || die "missing .agents/skills; bridge-only requires existing project skills"
  if [ -n "$name" ]; then
    [ -d ".agents/skills/$name" ] || die "missing .agents/skills/$name"
  fi
else
  skill_dir=".agents/skills/$name"
  [ ! -e "$skill_dir" ] || die "$skill_dir already exists"
fi

if [ "$dry_run" = true ]; then
  note_action "create-project-skill dry-run:"
else
  note_action "create-project-skill apply:"
fi

if [ "$bridge_only" = false ]; then
  skill_dir=".agents/skills/$name"
  skill_md="$skill_dir/SKILL.md"
  script_file="$skill_dir/scripts/$name.sh"

  note_action "- create $skill_md"
  if [ "$dry_run" = false ]; then
    mkdir -p "$skill_dir"
    write_skill_md "$skill_md" "$name" "$description"
  fi

  if [ "$with_script" = true ]; then
    note_action "- create $script_file"
    if [ "$dry_run" = false ]; then
      mkdir -p "$skill_dir/scripts"
      write_skill_script "$script_file" "$name"
      chmod +x "$script_file"
    fi
  fi
  if [ "$with_tests" = true ]; then
    note_action "- create $skill_dir/tests/"
    [ "$dry_run" = true ] || mkdir -p "$skill_dir/tests"
  fi
  if [ "$with_references" = true ]; then
    note_action "- create $skill_dir/references/"
    [ "$dry_run" = true ] || mkdir -p "$skill_dir/references"
  fi
  if [ "$with_fixtures" = true ]; then
    note_action "- create $skill_dir/fixtures/"
    [ "$dry_run" = true ] || mkdir -p "$skill_dir/fixtures"
  fi
  if [ "$with_bin" = true ]; then
    note_action "- create $skill_dir/bin/"
    [ "$dry_run" = true ] || mkdir -p "$skill_dir/bin"
  fi
fi

if [ "$target" = "both" ] || [ "$bridge_only" = true ]; then
  symlink_path=".claude/skills"
  symlink_target="../.agents/skills"
  if [ -L "$symlink_path" ]; then
    current="$(readlink "$symlink_path")"
    [ "$current" = "$symlink_target" ] ||
      die "$symlink_path points at $current; expected $symlink_target"
    note_action "- verify $symlink_path -> $symlink_target"
  elif [ -e "$symlink_path" ]; then
    die "$symlink_path exists and is not a symlink"
  else
    note_action "- create $symlink_path -> $symlink_target"
    if [ "$dry_run" = false ]; then
      mkdir -p .claude
      ln -s "$symlink_target" "$symlink_path"
    fi
  fi

  if [ -f .gitignore ] && grep -qE '^\.claude/?$' .gitignore; then
    note_action "- verify .gitignore contains .claude/"
  else
    note_action "- add .claude/ to .gitignore"
    if [ "$dry_run" = false ]; then
      if [ -f .gitignore ]; then
        {
          printf '\n'
          printf '# Project-local Claude directory (skills live in .agents/skills/)\n'
          printf '.claude/\n'
        } >>.gitignore
      else
        {
          printf '# Project-local Claude directory (skills live in .agents/skills/)\n'
          printf '.claude/\n'
        } >.gitignore
      fi
    fi
  fi
fi

if [ -n "$wrapper_name" ]; then
  wrapper_path=".agents/scripts/$wrapper_name.sh"
  if [ -e "$wrapper_path" ]; then
    die "$wrapper_path already exists"
  fi
  if [ "$bridge_only" = true ]; then
    [ -n "$name" ] || die "--with-wrapper in bridge-only mode requires a skill name"
    [ -x ".agents/skills/$name/scripts/$name.sh" ] ||
      die "missing executable .agents/skills/$name/scripts/$name.sh"
  fi
  note_action "- create $wrapper_path"
  if [ "$dry_run" = false ]; then
    mkdir -p .agents/scripts
    write_wrapper "$wrapper_path" "$name"
    chmod +x "$wrapper_path"
  fi
fi

if [ "$with_pre_pr" = true ]; then
  pre_pr_path=".agents/scripts/pre-pr.sh"
  if [ -e "$pre_pr_path" ]; then
    note_action "- verify $pre_pr_path exists"
  else
    note_action "- create $pre_pr_path"
    if [ "$dry_run" = false ]; then
      mkdir -p .agents/scripts
      write_pre_pr_stub "$pre_pr_path"
      chmod +x "$pre_pr_path"
    fi
  fi
fi

note_action "create-project-skill: ok"
