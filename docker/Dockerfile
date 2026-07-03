# syntax=docker/dockerfile:1.7
# =============================================================================
# agent-runtime-kit — standalone Linux image for Codex CLI + Claude Code.
#
# Tracking issue: https://github.com/graysurf/agent-runtime-kit/issues/77
# Scope: Linux-only / host-independent. macOS-only surfaces (Alfred CLIs,
# macos-agent, screen-record, op-ssh-sign) are intentionally out of scope.
#
# All Docker assets live under docker/. Build from the repo root:
#   docker build -f docker/Dockerfile -t agent-runtime-kit:dev .
# or:
#   docker compose -f docker/compose.yaml build
#
# The build context is the repo ROOT (the image bakes the source so the live
# ~/.claude and ~/.codex symlinks resolve). docker/Dockerfile.dockerignore
# trims the context so no repo-root .dockerignore is needed.
# =============================================================================

# Fallback only. The pin-aligned entrypoint `docker/build.sh` passes the version
# from docs/source/nils-cli-pin.yaml; keep this default and the SHA256 args in
# step with that pin for plain `docker build` users.
ARG NILS_CLI_VERSION=v1.20.6
ARG CLAUDE_CODE_VERSION=2.1.191
ARG CODEX_VERSION=0.142.2
ARG GH_VERSION=2.65.0
ARG GLAB_VERSION=1.101.0
ARG YQ_VERSION=v4.44.6
ARG NILS_CLI_SHA256_AMD64=220186b7364dabf864e057f8e04b6c86fe79dd4fb546f5f144dfab533f979db9
ARG NILS_CLI_SHA256_ARM64=679b7449ab5283587c02c922d9bc94ba4da9f79ee2a84bbcfb0728da5a3aef42
ARG GH_SHA256_AMD64=762569efe785082b7d1feb06995efece1a9cecce16da8503ac6fdbcbea04085b
ARG GH_SHA256_ARM64=8bcec9f3ee5c7c3700359a75da774c71221064a0ba017537795aa32ac8bbb481
ARG GLAB_SHA256_AMD64=f8f40309a622416b769a455a85509bae7800070cd023466f2d33d8ee82f3fc61
ARG GLAB_SHA256_ARM64=201cca73881e09d17c7c45801dee4541a9f999ebd9348abc44e0caac7787464b
ARG YQ_SHA256_AMD64=0c2b24e645b57d8e7c0566d18643a6d4f5580feeea3878127354a46f2a1e4598
ARG YQ_SHA256_ARM64=9477ac3cc447b6c083986129e35af8122eb2b938fe55c9c3e40436fb966e5813

# -----------------------------------------------------------------------------
# Stage 1 — fetch nils-cli prebuilt Linux binaries.
#
# nils-cli ships the agent-runtime, agent-docs, semantic-commit, forge-cli,
# plan-tooling, plan-issue, plan-archive, zsh-kit (and ~35 more) binaries as a
# single release tarball. We download the arch-matched tarball and verify it
# against the in-repo SHA256 pin and published .sha256 sidecar — no Linuxbrew
# required.
# -----------------------------------------------------------------------------
FROM debian:trixie-slim@sha256:28de0877c2189802884ccd20f15ee41c203573bd87bb6b883f5f46362d24c5c2 AS nils
ARG NILS_CLI_VERSION
ARG NILS_CLI_SHA256_AMD64
ARG NILS_CLI_SHA256_ARM64
ARG TARGETARCH
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates tar; \
    rm -rf /var/lib/apt/lists/*; \
    case "$TARGETARCH" in \
      amd64) triple="x86_64-unknown-linux-gnu"; expected="${NILS_CLI_SHA256_AMD64}" ;; \
      arm64) triple="aarch64-unknown-linux-gnu"; expected="${NILS_CLI_SHA256_ARM64}" ;; \
      *) echo "unsupported TARGETARCH=$TARGETARCH" >&2; exit 1 ;; \
    esac; \
    test -n "$expected"; \
    base="https://github.com/sympoies/nils-cli/releases/download/${NILS_CLI_VERSION}"; \
    file="nils-cli-${NILS_CLI_VERSION}-${triple}.tar.gz"; \
    cd /tmp; \
    curl -fsSL -o "$file" "${base}/${file}"; \
    curl -fsSL -o "${file}.sha256" "${base}/${file}.sha256"; \
    published="$(cut -d' ' -f1 "${file}.sha256")"; \
    test "$expected" = "$published" || { echo "nils-cli digest pin mismatch for ${file}: expected ${expected}, published ${published}" >&2; exit 1; }; \
    echo "${expected}  ${file}" | sha256sum -c -; \
    mkdir -p /opt/nils; \
    tar -xzf "$file" -C /opt/nils --strip-components=1; \
    test -x /opt/nils/bin/agent-runtime

# -----------------------------------------------------------------------------
# Stage 2 — runtime image.
# Node base gives Node + npm for Claude Code and Codex CLI (both Node-launched,
# glibc-linked native binaries — hence Debian, not Alpine).
#
# Debian *trixie* (glibc 2.41), not bookworm (glibc 2.36): the nils-cli
# `*-unknown-linux-gnu` release binaries require GLIBC_2.39, so bookworm cannot
# run `agent-runtime`. Keep this at trixie (or newer) while the pinned nils-cli
# needs glibc ≥ 2.39.
# -----------------------------------------------------------------------------
FROM node:26-trixie-slim@sha256:a1d9d671994fc2d26e297ac56b4b1522a8bc7fa71c43b14cd1b1fe6c5116f7dc AS runtime
ARG CLAUDE_CODE_VERSION
ARG CODEX_VERSION
ARG GH_VERSION
ARG GLAB_VERSION
ARG YQ_VERSION
ARG GH_SHA256_AMD64
ARG GH_SHA256_ARM64
ARG GLAB_SHA256_AMD64
ARG GLAB_SHA256_ARM64
ARG YQ_SHA256_AMD64
ARG YQ_SHA256_ARM64
ENV DEBIAN_FRONTEND=noninteractive

# OCI labels. `image.source` links the published GHCR package to this repo
# (and shows it under the repo's Packages) for any build path; the CI publish
# workflow also injects revision / created via docker/metadata-action.
LABEL org.opencontainers.image.source="https://github.com/graysurf/agent-runtime-kit" \
      org.opencontainers.image.title="agent-runtime-kit" \
      org.opencontainers.image.description="Standalone Linux image for Codex CLI + Claude Code on the agent-runtime-kit surface"

# OS deps + the cli-tools.yaml "core" profile, mapped to Debian packages.
# python3 is required by the rendered hook scripts (*.py guardrails). The shell
# tools are the generic zsh first-run floor; personal shell repos are still
# supplied at runtime, not baked into this image.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates curl git openssh-client tar xz-utils gnupg less bash zsh \
      python3 \
      ripgrep fd-find fzf jq bat \
      starship zoxide eza git-delta tree neovim libnotify-bin; \
    rm -rf /var/lib/apt/lists/*; \
    # Debian renames fd->fdfind and bat->batcat; expose the documented names.
    ln -sf "$(command -v fdfind)" /usr/local/bin/fd; \
    ln -sf "$(command -v batcat)" /usr/local/bin/bat

# gh, glab, and yq are installed from arch-matched release binaries.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) gh_sha="${GH_SHA256_AMD64}"; glab_sha="${GLAB_SHA256_AMD64}"; yq_sha="${YQ_SHA256_AMD64}" ;; \
      arm64) gh_sha="${GH_SHA256_ARM64}"; glab_sha="${GLAB_SHA256_ARM64}"; yq_sha="${YQ_SHA256_ARM64}" ;; \
      *) echo "unsupported Debian architecture=$arch" >&2; exit 1 ;; \
    esac; \
    test -n "$gh_sha"; test -n "$glab_sha"; test -n "$yq_sha"; \
    gh_file="gh_${GH_VERSION}_linux_${arch}.tar.gz"; \
    gh_base="https://github.com/cli/cli/releases/download/v${GH_VERSION}"; \
    curl -fsSL -o "/tmp/${gh_file}" "${gh_base}/${gh_file}"; \
    curl -fsSL -o /tmp/gh-checksums.txt "${gh_base}/gh_${GH_VERSION}_checksums.txt"; \
    gh_published="$(awk -v file="$gh_file" '$2 == file { print $1; exit }' /tmp/gh-checksums.txt)"; \
    test "$gh_sha" = "$gh_published" || { echo "gh digest pin mismatch for ${gh_file}: expected ${gh_sha}, published ${gh_published}" >&2; exit 1; }; \
    cd /tmp; \
    echo "${gh_sha}  ${gh_file}" | sha256sum -c -; \
    tar -xzf "/tmp/${gh_file}" -C /tmp; \
    install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh; \
    glab_file="glab_${GLAB_VERSION}_linux_${arch}.tar.gz"; \
    glab_base="https://gitlab.com/gitlab-org/cli/-/releases/v${GLAB_VERSION}/downloads"; \
    curl -fsSL -o "/tmp/${glab_file}" "${glab_base}/${glab_file}"; \
    curl -fsSL -o /tmp/glab-checksums.txt "${glab_base}/checksums.txt"; \
    glab_published="$(awk -v file="$glab_file" '$2 == file { print $1; exit }' /tmp/glab-checksums.txt)"; \
    test "$glab_sha" = "$glab_published" || { echo "glab digest pin mismatch for ${glab_file}: expected ${glab_sha}, published ${glab_published}" >&2; exit 1; }; \
    echo "${glab_sha}  ${glab_file}" | sha256sum -c -; \
    tar -xzf "/tmp/${glab_file}" -C /tmp; \
    install -m 0755 /tmp/bin/glab /usr/local/bin/glab; \
    yq_file="yq_linux_${arch}"; \
    curl -fsSL -o "/tmp/${yq_file}" \
      "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${yq_file}"; \
    echo "${yq_sha}  /tmp/${yq_file}" | sha256sum -c -; \
    install -m 0755 "/tmp/${yq_file}" /usr/local/bin/yq; \
    rm -rf /tmp/gh* /tmp/glab* /tmp/yq_linux_* /tmp/bin; \
    gh --version; glab --version; yq --version

# nils-cli binaries (agent-runtime et al.) from stage 1.
COPY --from=nils /opt/nils/bin/ /usr/local/bin/
RUN agent-runtime --version; zsh-kit --version; zsh --version

# Claude Code + Codex CLI via npm lockfile pins.
COPY docker/npm-cli-pins/package.json docker/npm-cli-pins/package-lock.json /opt/npm-cli-pins/
RUN set -eux; \
    cd /opt/npm-cli-pins; \
    node -e "const fs=require('fs'); const pkg=require('./package.json'); const lock=require('./package-lock.json'); const pins={'@anthropic-ai/claude-code':process.env.CLAUDE_CODE_VERSION,'@openai/codex':process.env.CODEX_VERSION}; for (const [name, version] of Object.entries(pins)) { if (pkg.dependencies[name] !== version) throw new Error(name + ' package.json pin mismatch'); const locked = lock.packages['node_modules/' + name]; if (!locked || locked.version !== version || !/^sha512-/.test(locked.integrity || '')) throw new Error(name + ' lockfile pin/integrity mismatch'); }"; \
    npm ci --omit=dev; \
    ln -sf /opt/npm-cli-pins/node_modules/.bin/claude /usr/local/bin/claude; \
    ln -sf /opt/npm-cli-pins/node_modules/.bin/codex /usr/local/bin/codex; \
    npm cache clean --force; \
    claude --version; \
    codex --version

# Non-root runtime user. The node base ships a uid-1000 "node" user; replace it
# with "agent" so uid 1000 is predictable for optional host bind-mounts.
ARG AGENT_UID=1000
ARG AGENT_GID=1000
RUN set -eux; \
    userdel -r node 2>/dev/null || true; \
    groupadd -g "${AGENT_GID}" agent; \
    useradd -m -u "${AGENT_UID}" -g "${AGENT_GID}" -s /usr/bin/zsh agent; \
    mkdir -p /work; \
    chown agent:agent /work; \
    printf '%s\n' \
      '# Managed by zsh-kit.' \
      '# Seeded by the agent-runtime-kit Docker image.' \
      'export SHELL=/usr/bin/zsh' \
      'if [[ -z "${TERM-}" || "${TERM-}" == "dumb" ]]; then' \
      '  export TERM=xterm-256color' \
      'fi' \
      > /home/agent/.zshenv; \
    printf '%s\n' \
      '# Managed by the agent-runtime-kit Docker image.' \
      '# Operator-supplied zsh repos are installed at runtime with zsh-kit.' \
      'if command -v zoxide >/dev/null 2>&1; then' \
      '  source <(zoxide init zsh)' \
      'fi' \
      '' \
      'if [[ -o interactive && -t 0 && -t 1 && -n "${TERM-}" && "${TERM-}" != "dumb" ]] && \' \
      '    command -v starship >/dev/null 2>&1; then' \
      '  source <(starship init zsh)' \
      'fi' \
      > /home/agent/.zshrc; \
    chown agent:agent /home/agent/.zshenv /home/agent/.zshrc

# Stable env contract (mirrors the host AGENT_HOME.md / runtime-roots.yaml).
ENV AGENT_KIT_SRC=/opt/agent-runtime-kit \
    AGENT_DOCS_HOME=/opt/agent-runtime-kit \
    CODEX_HOME=/home/agent/.codex \
    XDG_STATE_HOME=/home/agent/.local/state \
    AGENT_HOME=/home/agent/.local/state/agent-runtime-kit \
    AGENT_RUNTIME_KIT_DOCKER=1 \
    SHELL=/usr/bin/zsh

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

# Bake the source so the rendered live homes (symlinks into the source tree)
# resolve without any host bind-mount.
COPY --chown=agent:agent . ${AGENT_KIT_SRC}

USER agent
WORKDIR ${AGENT_KIT_SRC}

# Render the product surfaces (build/ is gitignored, so regenerate it here) and
# activate them into the container's ~/.claude and ~/.codex. Then add the
# home-scope policy symlinks the host setup uses (AGENT_HOME.md).
RUN set -eux; \
    agent-runtime render --product codex; \
    agent-runtime render --product claude; \
    mkdir -p "${AGENT_HOME}/claude" "${AGENT_HOME}/codex" \
             "${HOME}/.claude" "${CODEX_HOME}"; \
    agent-runtime install --source-root "${AGENT_KIT_SRC}" --product claude \
      --live-home "${HOME}/.claude" --state-home "${AGENT_HOME}/claude" --apply; \
    agent-runtime install --source-root "${AGENT_KIT_SRC}" --product codex \
      --live-home "${CODEX_HOME}" --state-home "${AGENT_HOME}/codex" --apply; \
    ln -sfn "${AGENT_KIT_SRC}/AGENT_HOME.md" "${HOME}/.claude/CLAUDE.md"; \
    ln -sfn "${AGENT_KIT_SRC}/AGENT_HOME.md" "${CODEX_HOME}/AGENTS.md"

WORKDIR /home/agent
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["zsh", "-il"]
