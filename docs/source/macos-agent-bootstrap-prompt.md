# macOS Agent Bootstrap Prompt

## Purpose

This document is a reusable prompt for asking an agent on another macOS host to
install or reinstall:

- `graysurf/zsh-kit`
- `graysurf/agent-runtime-kit`
- the released `sympoies/tap/nils-cli` Homebrew surface that provides
  `agent-runtime`, `zsh-kit`, `agent-docs`, and related tools

The intended operator is non-technical. The prompt therefore defaults to a clean
reinstall path, but requires explicit consent before moving any existing files.

## Placement

This is repo-wide host bootstrap guidance, not a one-off discussion artifact and
not a skill-owned implementation note. It belongs under `docs/source/` as
canonical source documentation until superseded.

## Copyable Prompt

Copy the following prompt into the agent session on the target Mac.

````text
You are helping a non-technical user set up their macOS shell and agent runtime.
Use plain English. Explain what you are about to change before you change it.

Goal:
1. Install or cleanly reinstall graysurf/zsh-kit at $HOME/.config/zsh.
2. Install or cleanly reinstall graysurf/agent-runtime-kit at
   $HOME/.config/agent-runtime-kit.
3. Install the current Homebrew release of sympoies/tap/nils-cli, which provides
   agent-runtime, zsh-kit, agent-docs, and related tools.
4. Activate Codex and Claude runtime surfaces through agent-runtime.
5. Verify the installation with real commands and report the results.

Hard safety rules:
- Before moving, deleting, overwriting, or reinstalling anything, explain the
  impact and ask the user to reply exactly: I approve the clean reinstall
- Do not permanently delete old files. Move old install paths into a timestamped
  backup folder.
- Do not delete all of $HOME/.codex or all of $HOME/.claude. Those folders may
  contain login state, auth files, sessions, history, or user-specific settings.
- Do not touch $HOME/.ssh, browser data, macOS Keychain, unrelated dotfiles, or
  any secrets.
- Do not run apply steps before a dry-run when the tool supports dry-run.
- If a conflict or unknown state appears, stop and explain it. Do not guess.
- Treat authentication as a separate user-owned step. Do not ask the user to
  paste private keys or API keys into chat.

First message to the user:

I can do a clean reinstall to avoid problems from old versions of zsh-kit,
agent-runtime-kit, or nils-cli. I will move these old paths into a backup folder
instead of deleting them:

- $HOME/.config/zsh
- $HOME/.config/agent-runtime-kit
- $HOME/.zshenv

I will reinstall nils-cli through Homebrew. I will not delete $HOME/.codex,
$HOME/.claude, SSH keys, browser data, Keychain entries, private tokens, or
unrelated dotfiles.

Please reply exactly:

I approve the clean reinstall

After the user approves, run these steps.

1. Start strict shell mode, set standard runtime homes, and create a backup
   folder.

```bash
set -euo pipefail

export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export CODEX_AGENT_STATE_HOME="${CODEX_AGENT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/codex}"

stamp="$(date +%Y%m%d-%H%M%S)"
backup_root="$HOME/.local/state/agent-runtime-kit/bootstrap-backups/$stamp"
mkdir -p "$backup_root"
echo "CODEX_HOME: $CODEX_HOME"
echo "Backup root: $backup_root"
```

2. Install Homebrew if needed, then put brew on PATH for this shell.

```bash
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is missing. Installing Homebrew may ask for the user's macOS password."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi

command -v brew
brew --version
```

3. Move old install paths into the backup folder.

```bash
move_if_exists() {
  src="$1"
  name="$2"
  if [ -e "$src" ] || [ -L "$src" ]; then
    echo "Moving $src -> $backup_root/$name"
    mv "$src" "$backup_root/$name"
  fi
}

move_if_exists "$HOME/.config/zsh" "zsh"
move_if_exists "$HOME/.config/agent-runtime-kit" "agent-runtime-kit"
move_if_exists "$HOME/.zshenv" "zshenv"
```

4. Reinstall nils-cli from the Homebrew tap.

```bash
brew tap sympoies/tap
brew uninstall --force nils-cli 2>/dev/null || true
brew install sympoies/tap/nils-cli

agent-runtime --version
zsh-kit --version
agent-docs --version
```

5. Clone and install agent-runtime-kit.

```bash
git clone https://github.com/graysurf/agent-runtime-kit.git "$HOME/.config/agent-runtime-kit"
cd "$HOME/.config/agent-runtime-kit"

bash scripts/setup.sh --profile core --skip-homebrew-install --dry-run
bash scripts/setup.sh --profile core --skip-homebrew-install

bash scripts/sync-runtime-surfaces.sh \
  --source-root "$HOME/.config/agent-runtime-kit" \
  --apply
```

6. Install zsh-kit. Dry-run first, then apply.

```bash
zsh-kit setup \
  --repo https://github.com/graysurf/zsh-kit.git \
  --dest "$HOME/.config/zsh" \
  --write-zshenv \
  --install-tools skip \
  --dry-run

zsh-kit setup \
  --repo https://github.com/graysurf/zsh-kit.git \
  --dest "$HOME/.config/zsh" \
  --write-zshenv \
  --install-tools skip \
  --apply
```

7. Verify zsh-kit.

```bash
cd "$HOME/.config/zsh"

zsh -f ./bootstrap/zsh-kit-setup.zsh \
  --install-tools skip \
  --dry-run \
  --smoke

./tests/run.zsh
./tools/check.zsh --smoke

zsh -ic 'print -r -- "ZDOTDIR=$ZDOTDIR"; command -v zsh-kit; command -v agent-runtime'
```

8. Verify agent-runtime-kit.

```bash
cd "$HOME/.config/agent-runtime-kit"

agent-docs --docs-home "$PWD" --project-path "$PWD" \
  audit --target project --strict

codex_state_home="$CODEX_AGENT_STATE_HOME"
claude_state_home="${CLAUDE_KIT_STATE_HOME:-$HOME/.local/state/agent-runtime-kit/claude}"

agent-runtime doctor \
  --source-root "$HOME/.config/agent-runtime-kit" \
  --product codex \
  --live-home "${CODEX_HOME:-$HOME/.codex}" \
  --state-home "$codex_state_home" \
  --class skill-surface \
  --format json

agent-runtime doctor \
  --source-root "$HOME/.config/agent-runtime-kit" \
  --product claude \
  --live-home "$HOME/.claude" \
  --state-home "$claude_state_home" \
  --class skill-surface \
  --format json

if command -v claude >/dev/null 2>&1; then
  claude plugins list
  claude plugin details meta
else
  echo "Claude CLI is not on PATH; skipped claude plugins list."
fi
```

9. If Codex CLI is available, verify prompt input. If it is not available, report
   this as skipped, not failed.

```bash
if command -v codex >/dev/null 2>&1; then
  codex debug prompt-input
else
  echo "Codex CLI is not on PATH; skipped codex debug prompt-input."
fi
```

10. Optional tool installation for zsh-kit. Keep this separate from the shell
    takeover step.

```bash
cd "$HOME/.config/zsh"
./install-tools.zsh --dry-run
```

Ask the user before running the installer:

The shell setup is complete. zsh-kit can also install missing command-line tools
through Homebrew. This is optional and may take time. Reply exactly
"Install zsh-kit tools" if you want me to continue.

If the user approves:

```bash
cd "$HOME/.config/zsh"
./install-tools.zsh --yes
```

Final report format:
- Installed: yes/no
- Backup folder: <path>
- agent-runtime version: <output>
- zsh-kit version: <output>
- agent-docs audit: pass/fail
- zsh-kit smoke: pass/fail
- Codex doctor: pass/fail
- Claude doctor: pass/fail
- Codex plugins list: pass/fail/skipped
- Claude plugins list: pass/fail/skipped
- Codex prompt-input: pass/fail/skipped
- Optional zsh-kit tools: installed/skipped
- Next step for the user: close and reopen Terminal

If any step fails:
- Stop.
- Tell the user which command failed.
- Summarize the important error text.
- Do not continue with later apply steps.
````

## Notes For Maintainers

- The reinstall policy intentionally moves old state into
  `$HOME/.local/state/agent-runtime-kit/bootstrap-backups/<timestamp>/` instead
  of deleting it.
- `--install-tools skip` is the default shell setup path. Tool installation is a
  separate opt-in because it can install or update many Homebrew packages.
- `agent-runtime install` and `sync-runtime-surfaces.sh` own managed Codex and
  Claude runtime surfaces. The prompt deliberately avoids deleting all of
  `$HOME/.codex` or `$HOME/.claude`.
