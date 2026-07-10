# macOS Computer Use Setup

## Install

Install the released nils-cli package on every Mac that will execute desktop
actions. The controlling Linux or macOS host only needs Python 3 and OpenSSH
when it uses `--host`.

```bash
brew tap sympoies/tap
brew install sympoies/tap/nils-cli
brew install cliclick im-select
brew install --cask hammerspoon
```

Enable the Hammerspoon CLI by adding this line to
`~/.hammerspoon/init.lua`, then reload Hammerspoon:

```lua
require("hs.ipc")
```

`osascript` and the macOS Accessibility APIs are supplied by macOS. The
`screen-record` binary ships with nils-cli and is useful for video evidence;
the skill's still-image path uses `macos-agent observe screenshot`.

## Permissions

In **System Settings > Privacy & Security**, grant the process that executes
`macos-agent`:

- **Accessibility** for pointer, keyboard, and AX actions.
- **Automation** when macOS asks permission to control System Events or an app.
- **Screen & System Audio Recording** (called **Screen Recording** on older
  macOS releases) for screenshots and recordings.

For an SSH target, grants may attach to the remote shell host rather than the
interactive terminal application. Run the skill preflight through the same
transport that automation will use; do not assume an interactive Terminal
grant also covers SSH. macOS may require an interactive user to approve a TCC
prompt, and some permission changes require the relevant process or login
session to restart.

## SSH

Configure authentication and host verification in the operator's normal
`~/.ssh/config`. Keep hostnames, usernames, private keys, and machine paths out
of public repositories. The skill accepts a runtime `--host <ssh-alias>` and
uses batch mode; it never writes SSH credentials or connection strings into
the managed runtime surfaces.

The remote Mac must have an active, unlocked graphical login session. SSH can
start commands but cannot create a usable WindowServer session on a logged-out
or locked Mac.

## Verify

```bash
macos-agent --version # must be 1.21.13 or newer
macos-agent --format json preflight --include-probes
macos-agent --format json apps list
macos-agent --format json windows list --on-screen-only
```

For remote verification, run the skill helper with `--host` and an `agent-out`
directory. Permission gaps are written to `pending-user-actions.json`; resolve
them when an interactive operator is available, while continuing tests that do
not require the blocked capability.

## Capability Baseline

The portable baseline follows common public Computer Use action families:
`click`, `double_click`, `scroll`, `type`, `wait`, `keypress`, `drag`, `move`,
and `screenshot`, including mouse buttons, click counts, and modifiers. The
upstream action references used to define the baseline are:

- <https://developers.openai.com/api/docs/guides/tools-computer-use#possible-computer-use-actions>
- <https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool#available-actions>

`input click --count 2|3` covers double/triple click; `--button` covers
right/middle click; click/drag/scroll accept `--mods`; AX-selector screenshots
provide a focused-region/zoom equivalent. The runtime intentionally exposes
atomic drag instead of independent mouse-down/mouse-up across CLI invocations,
because a timeout or transport disconnect between those calls can leave input
held on the desktop.
