# docker/ — standalone Linux image for Codex + Claude

A single-folder Docker setup that builds a Linux image where **Codex CLI** and
**Claude Code** both run on top of the shared `agent-runtime-kit` surface
(skills, hooks, docs, and the `nils-cli` primitives).

Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/77>

> Status: published to GHCR on release, with a multi-arch build + smoke-test
> gate in the release workflow (see [Publishing](#publishing)). Scope is
> intentionally Linux-only and host-independent — macOS-only surfaces (Alfred
> CLIs, `macos-agent`, `screen-record`, `op-ssh-sign`) are out of scope.

Everything Docker-related is contained in this folder. The build context is the
repository root (the image bakes the source so the rendered `~/.claude` /
`~/.codex` symlinks resolve), but the context is trimmed by
`Dockerfile.dockerignore` (a BuildKit per-Dockerfile ignore) so nothing is
added at the repo root.

## Layout

| File | Purpose |
| --- | --- |
| `Dockerfile` | Two-stage build: fetch `nils-cli` Linux binaries, then assemble the Node-based runtime. |
| `Dockerfile.dockerignore` | BuildKit per-Dockerfile context filter (keeps Docker out of the repo root). |
| `build.sh` | Validated build entrypoint: reads `validated_tag` and release digests from `docs/source/nils-cli-pin.yaml`. |
| `compose.yaml` | Convenience wrapper for interactive use. |
| `entrypoint.sh` | Prints a capability banner, optionally applies a runtime Zsh repo, and execs the requested command. |
| `env.example` | Template for `docker/.env` (auth passthrough; gitignored). |
| `fixtures/zsh-kit-setup/` | Safe local fixture hook used by the image-level `zsh-kit setup --apply` smoke. |
| `smoke-zsh-kit-apply.sh` | Container-internal e2e smoke that creates a fixture Git repo, applies it through `zsh-kit`, and asserts the result. |

## Build

From the repository root. The recommended entrypoint is `docker/build.sh`,
which takes the exact validated nils-cli release and digests from
`docs/source/nils-cli-pin.yaml` so packaging never follows an ambient host:

```bash
docker/build.sh                      # -> agent-runtime-kit:dev
docker/build.sh -t agent-runtime-kit:1.0.9    # custom tag
docker/build.sh -n                   # dry-run: print the resolved command
docker/build.sh -- --no-cache        # pass extra flags to `docker build`
```

Plain `docker build` / `compose build` also work, but fall back to the
`NILS_CLI_VERSION` default baked into the `Dockerfile` (not the policy file):

```bash
docker build -f docker/Dockerfile -t agent-runtime-kit:dev .
docker compose -f docker/compose.yaml build
```

The image targets the host architecture (`linux/amd64` or `linux/arm64`)
automatically via `TARGETARCH`.

## Run

```bash
# Interactive zsh shell with claude / codex / agent-runtime / nils-cli on PATH
docker run --rm -it agent-runtime-kit:dev

# One-shot a CLI
docker run --rm -it agent-runtime-kit:dev claude --version
docker run --rm -it agent-runtime-kit:dev codex --version
docker run --rm -it agent-runtime-kit:dev zsh --version
docker run --rm -it agent-runtime-kit:dev zsh-kit --version
docker run --rm -it agent-runtime-kit:dev \
  bash -lc '$AGENT_KIT_SRC/docker/smoke-zsh-kit-apply.sh'

# Operate on a host project
docker run --rm -it -v "$PWD:/work" -w /work agent-runtime-kit:dev
```

Via compose (reads `docker/.env` if present):

```bash
cp docker/env.example docker/.env   # then fill in keys
docker compose -f docker/compose.yaml run --rm agent
```

The default shell starts in `/home/agent`. Use `-w /work` when you bind-mount a
project and want the shell to start there.

## Auth

Auth is supplied at runtime and never baked into the image:

- **Claude Code** — `ANTHROPIC_API_KEY`, or `claude login` inside the
  container, or mount a credentials file to `~/.claude/.credentials.json`.
- **Codex CLI** — `OPENAI_API_KEY`, or `codex login`, or mount
  `~/.codex/auth.json`.
- **forge-cli / gh** — `GH_TOKEN` (or `GITHUB_TOKEN`).
- **forge-cli / glab** — `GITLAB_TOKEN` (or `GL_TOKEN`).
- **zsh-kit setup** — runtime Git credentials for the operator-supplied Zsh
  repo, such as `GH_TOKEN` with `gh auth setup-git`, or mounted SSH credentials.

```bash
docker run --rm -it -e ANTHROPIC_API_KEY -e OPENAI_API_KEY agent-runtime-kit:dev
```

## Runtime Zsh setup

The image includes public `zsh` and the released `zsh-kit` binary, but it does
not bake any personal shell repository or private setup scripts. Supply the Zsh
repository URL and auth at runtime:

```bash
docker run --rm -it \
  -e ZSH_SETUP_REPO_URL="https://github.com/your-org/your-zsh-config.git" \
  -e ZSH_SETUP_FEATURES="docker" \
  -e ZSH_SETUP_INSTALL_TOOLS="skip" \
  -e GH_TOKEN \
  agent-runtime-kit:dev
```

When `ZSH_SETUP_REPO_URL` is present, the entrypoint runs
`zsh-kit setup --apply --write-zshenv` before the requested command. The
released `zsh-kit >= 1.0.9` bootstrap writes a container `~/.zshenv` that
preserves `ZDOTDIR`, exports `ZSH_FEATURES`, and sources `$ZDOTDIR/.zshenv`.
Additional knobs:

- `ZSH_SETUP_DEST` — destination directory, default `$HOME/.config/zsh`
- `ZSH_SETUP_FEATURES` — forwarded feature CSV, default `docker`
- `ZSH_SETUP_INSTALL_TOOLS` — forwarded tool policy, default `skip`
- `ZSH_SETUP_BRANCH` / `ZSH_SETUP_REF` — optional checkout selector
- `ZSH_SETUP_FORCE=1` — allow guarded overwrite/update paths

Use `--dry-run` first when validating a new repo hook:

```bash
docker run --rm -it \
  -e ZSH_SETUP_REPO_URL="https://github.com/your-org/your-zsh-config.git" \
  agent-runtime-kit:dev \
  bash -lc 'zsh-kit setup --repo "$ZSH_SETUP_REPO_URL" \
    --dest /tmp/zsh-kit-dry-run \
    --dry-run --features docker --install-tools skip'
```

The release workflow also runs a fixture apply smoke that does not require
network auth or a private repository:

```bash
docker run --rm -it agent-runtime-kit:dev \
  bash -lc '$AGENT_KIT_SRC/docker/smoke-zsh-kit-apply.sh'
```

That script creates a temporary local Git repository inside the container,
applies it with `zsh-kit setup --apply`, and asserts both the JSON envelope and
hook-created marker files. It also checks that the image does not start with a
baked `$HOME/.config/zsh` or `/opt/private-skills` tree.

## What's inside

- **Base**: `node:26-trixie-slim` pinned by digest — Debian 13, glibc 2.41
  (Node ≥18 for both CLIs; glibc for their native binaries). Trixie, not
  bookworm: the `nils-cli` release binaries require GLIBC ≥ 2.39, which
  bookworm's 2.36 cannot satisfy.
- **Shell runtime**: Debian `zsh` plus a generic first-run floor (`starship`,
  `zoxide`, `eza`, `git-delta`, `tree`, `neovim`, `libnotify-bin`) and
  `zsh-kit` for runtime shell setup from an operator-supplied repo URL/path.
  Personal shell repos are fetched or mounted at runtime, not copied into the
  image.
- **AI CLIs**: `@anthropic-ai/claude-code` and `@openai/codex` via the
  committed `docker/npm-cli-pins/package-lock.json` integrity pins.
- **nils-cli**: prebuilt Linux release tarball (`agent-runtime`, `agent-docs`,
  `semantic-commit`, `forge-cli`, `plan-tooling`, `plan-issue`, `zsh-kit`, …
  ~40 binaries),
  pinned to the version and Linux release digests in
  `docs/source/nils-cli-pin.yaml`, then verified against both that in-repo
  SHA256 pin and the published `.sha256`. No Linuxbrew.
- **Core CLI tools** (`cli-tools.yaml` `core` profile): `ripgrep`, `fd`, `fzf`,
  `jq`, `yq`, `gh`, `glab`, `bat`.
- **Rendered runtime**: `agent-runtime render` + `install` activate the shared
  surface into `~/.claude` and `~/.codex`, plus the `AGENT_HOME.md` policy
  symlinks (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`).

## Publishing

Released images are published to the GitHub Container Registry (GHCR) at
`ghcr.io/sympoies/agent-runtime-kit` for `linux/amd64` + `linux/arm64`. Versions
are CalVer (`vYYYY.MM.DD`); cutting a GitHub Release fires
`.github/workflows/publish-image.yml`, which resolves the `nils-cli` pin,
smoke-tests an `amd64` build, then pushes the multi-arch image tagged with the
date and `latest`. The pushed image includes BuildKit provenance/SBOM
attestations and a GitHub provenance attestation for the immutable image digest.
See [`../RELEASING.md`](../RELEASING.md) for the full process.

```bash
docker pull ghcr.io/sympoies/agent-runtime-kit:latest
```

To verify a dated release before running it:

```bash
docker buildx imagetools inspect ghcr.io/sympoies/agent-runtime-kit:2026.05.30
gh attestation verify \
  oci://ghcr.io/sympoies/agent-runtime-kit:2026.05.30 \
  -R sympoies/agent-runtime-kit
```

## Known gaps / review follow-ups

These are deliberate v1 simplifications, to revisit after review:

- macOS-only skills remain rendered but inert (their CLIs are absent); not yet
  pruned from the in-container surface.
- Private skills are **not** baked in. The private-skill overlay
  (`scripts/sync-private-skills.sh`, sourced from `$AGENT_PRIVATE_SKILLS_HOME`)
  lives outside the build context and is intentionally excluded — these skills
  are personal and machine-local, so baking them into a shareable image would
  be wrong. To use them in a container, mount the private source tree and run
  the overlay at runtime (the script is a no-op when its source is absent):

  ```bash
  docker run --rm -it \
    -v "$AGENT_PRIVATE_SKILLS_HOME:/opt/private-skills:ro" \
    -e AGENT_PRIVATE_SKILLS_HOME=/opt/private-skills \
    agent-runtime-kit:dev \
    bash -lc '$AGENT_KIT_SRC/scripts/sync-private-skills.sh --apply; exec bash'
  ```

- Auth is env/login/mount only; no helper for importing host credentials.
- The image is built + smoke-tested + published only on release (see
  [Publishing](#publishing)); there is no per-PR image build gate yet, so a
  change that breaks the Docker build is only caught at release time.
