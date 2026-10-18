# Codex One-shot Consumer Acceptance

This is the consumer acceptance layer for [#129](https://github.com/sympoies/agent-runtime-kit/issues/129),
using the released `codex-cli` executable. Tests are the deliverable under
[#289](https://github.com/sympoies/agent-runtime-kit/issues/289); there is no
production behavior fix or artificial red-first record. No hook exemption,
registration change, runtime activation, merge, or release is part of this suite.

`run.py --layer boundary` runs in the canonical gate with the admitted nils-cli
surface. Only child peers are substituted: Codex captures argv/home/environment,
Git delegates fixture reads and staging to real Git but refuses raw commits and
captures pushes, and semantic-commit returns real staged diff bytes and captures
structured commit arguments without creating a commit. This proves the released
wrapper's routing and failure boundaries, not native commit/signing behavior.
Every case has its own temporary HOME, XDG roots, Git config and workspace.
There are no credentials or API/model calls. The auth marker is synthetic.

`run.py --layer product` also requires real Codex and the **exact validated
release** in `docs/source/nils-cli-pin.yaml`. It adds real no-API prompt-input
controls and doctor. Product smoke invokes this layer instead of a native
`codex exec` that might accidentally contact an available local model server.
The current product binary's version is recorded with the acceptance output.

## Control Matrix

A passing executable suite does **not** close #129. JSON records test success
separately from per-row acceptance, with `acceptance_complete: false` until the
scheduled tester supplies the outstanding observations. `partial` is not a pass.
All rows below are defined even when their live observations remain pending.

| Row | Executable control and observable assertion | Remaining acceptance |
| --- | --- | --- |
| A1 | Two default prompt children get different 0700 homes, exact isolated flags/features, workspace cwd, ordinary shell/signing environment, stripped control variables, no dangerous flag, and cleanup. Literal shell metacharacters remain one prompt argv entry. | None at the wrapper boundary. |
| A2 | Real inherited `debug prompt-input` contains both home/project instruction sentinels; the isolated shape contains neither. A1 separately binds that shape to wrapper argv. | No model claim is inferred from this no-API probe. |
| A3 | The child home contains no hook/config surfaces; the explicit inherited control retains them. Doctor leak injection fails closed. | A trusted home hook and a trusted project hook must each execute in inherited mode and remain silent in isolated mode, observed by marker files. |
| A4 | Planted plugins, skills, agents, memory, goals and hook/config surfaces are absent from the isolated home and present in the inherited control; all integration feature disables are checked. | Real positive discovery controls for plugins, skills, MCP, memories, goals and subagents, then isolated suppression. Entry absence alone does not prove discovery. |
| A5 | Synthetic auth is a symlink to the selected source, the only initial child entry; no marker contents reach logs; replacement is warned about without propagation; cleanup covers success and child failure. Missing auth leaves the home empty. | Scheduled authenticated file-backed bridge smoke; credential-store-only platforms need separate acceptance. |
| A6 | Prompt selects workspace-write; advice/knowledge select read-only. Fixture prompt templates exercise those actual wrapper commands. | Native command events must show workspace write success for prompt, denied outside write, and denied workspace writes for advice/knowledge. |
| A7 | Missing flag/feature and unavailable secure temporary storage fail before any child execution, without inherited fallback. | Fault-injected auth-symlink creation denial must produce `isolated-auth-bridge-unavailable` before a request. This cannot be claimed from successful symlink creation. |
| A8 | Runtime flag beats environment; environment beats default; invalid selectors fail; inherited keeps its dangerous-mode gate, real home and legacy argv; resume resolves real fixture history, exact native argv and exit status, and rejects a runtime selector. | None at the wrapper boundary. |
| A9 | Only real staged bytes reach structured generation; unstaged/untracked sentinels stay out. Shell tools are disabled, semantic-commit receives structured fields and expected HEAD. Invalid fields/messages and real HEAD/index drift refuse commit. | Native semantic-commit/signing protections are not replaced or exercised by the peer fixture. |
| A10 | Removing semantic-commit fails before model, raw commit or push. | None at the wrapper boundary. |
| A11 | Push occurs only after explicit `--push` and a successful semantic owner; failed owner prevents push, failed push reports local commit preservation, and prompt text cannot request push. | Git publication is captured, never performed; no remote is configured. |
| A12 | Doctor JSON schema/readiness/method are checked, instruction and hook-surface leak injections fail, and no model child runs. Product mode uses real no-API doctor too. | `child-home-hook-surface` is explicitly not an observed lifecycle result. |
| A13 | Hook source, policy, manifest and Codex registration are scanned for command-specific exemptions. The implementation diff must keep those controls unchanged. | Outer managed-session hooks remain authoritative during all tester commands. |
| A14 | Product mode refuses a CLI other than the validated pin and runs all boundary checks plus real no-API controls. Linux pinned launcher verifies the release archive against the committed digest; a wrong pin fails product smoke instead of becoming a capability skip. Authenticated output guards reject repository-local/symlink destinations and enforce private modes. | Scheduled authenticated doctor/knowledge receipt, then issue-owner disposition of all partial rows. No automatic issue retirement. |

The matrix JSON is deliberately conservative on failures: failed rows are named;
other rows become unverified rather than being reported as successful acceptance.

## Reproduction

Run from the repository root. Allocate output outside the repository:

```bash
acceptance_out="$(agent-out project --topic codex-agent-acceptance --mkdir)"
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 \
  bash tests/runtime-smoke/codex-agent/pinned.sh \
  python3 tests/runtime-smoke/codex-agent/run.py --layer product \
  --matrix-out "$acceptance_out/matrix.json"
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 \
  bash tests/runtime-smoke/codex-agent/pinned.sh \
  bash tests/runtime-smoke/run.sh --mode product --product codex --probe-only \
  --artifacts-dir "$acceptance_out/product"
```

`pinned.sh` resolves tag and architecture-specific SHA256 from the manifest and
uses the existing released-package launcher. It neither changes the installed
CLI nor moves the version pin. On other platforms, install the released platform
package at the same validated tag and invoke `run.py` directly. The boundary
layer accepts the repository compatibility floor and newer supported hosts; only
product acceptance enforces exact pin equality. For a clean committed tree, the
repository finish line remains `bash scripts/ci/all.sh`; it already includes
`tests/hooks/run.sh` and the boundary suite. Run Linux validation in the same
memory-limited systemd scope.

## Scheduled Tester Handoff

The dispatcher schedules authenticated acceptance. Do not use a shared desktop,
browser, or device from this harness. The resident tester uses an existing
approved Codex login; no key provisioning or runtime sync is required. Configure
`RUNTIME_SMOKE_SOURCE_CODEX_HOME` privately when the login home differs from the
ordinary `CODEX_HOME`. Never publish that value or raw product logs.

After the deterministic/product probes above pass, run the authenticated smoke
against the same pinned package:

```bash
export RUNTIME_SMOKE_ARTIFACTS_DIR="$(agent-out project --topic codex-agent-live --mkdir)"
export RUNTIME_SMOKE_CODEX_AUTHENTICATED=1
systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 \
  bash tests/runtime-smoke/codex-agent/pinned.sh \
  bash tests/runtime-smoke/codex-agent/authenticated.sh
```

`authenticated.sh` refuses an unapproved live invocation, reruns the no-API
product checks, borrows only an auth symlink into a temporary sentinel home,
then runs `codex-cli agent doctor --format json` and
`codex-cli agent knowledge 'Reply with the active runtime mode only: isolated.'`
in a temporary workspace. It requires ready doctor JSON, an exact `isolated`
response, and no instruction sentinel or `agent-hook` text in product output.
It enforces a 0700 external artifact directory and umask 077 before writing raw output, refuses a symlink destination, and removes the borrowed home afterward. A model saying `isolated` or absent
text is a smoke signal, not proof of hook suppression or sandbox enforcement.
The script leaves A3/A4/A6/A7 acceptance pending explicitly.

For those remaining rows the tester must record these **separate** controls:

1. In a disposable home/workspace, register one home and one project lifecycle
   hook through the product's ordinary supported trust/configuration flow.
   Each hook writes its own marker outside the workspace. Use inert sentinel
   hooks only; do not link the maintainer's real hook tree or change kit hooks.
   Run `codex-cli agent prompt --runtime inherited --ephemeral 'Reply ok.'`
   with the inherited path's existing `CODEX_ALLOW_DANGEROUS_ENABLED=true`
   opt-in. Both markers must exist. Clear only these disposable markers, run
   default `agent prompt 'Reply ok.'`, and require both markers absent. If the
   trusted inherited control does not fire, report blocked, not isolated pass.
2. Seed distinct inert plugin/skill/MCP/memory/goal/subagent sentinels in that
   disposable home using supported product formats. Record each one's
   discovery in an inherited native input/tool inventory; then require absence
   in isolated input/tool inventory. A missing inherited positive control is
   incomplete acceptance. Never register a real external service or run a
   discovered subagent merely to test this surface.
3. Ask default `agent prompt` to write a unique file inside its fixture
   workspace and attempt a second write to a sibling fixture directory outside
   the workspace. Record native tool commands and exit codes, plus filesystem
   effects: only the first write succeeds. For `agent advice` and
   `agent knowledge`, request a workspace write and require a native denied
   attempt and no file. Refusal without an observed tool attempt is incomplete.
   Do not target a real file, auth home, or shared resource.
4. On an isolated platform/fault-injection fixture where symlink creation is
   denied, supply a synthetic file-backed auth source and run default prompt.
   Require `isolated-auth-bridge-unavailable`, no child model request and no
   inherited fallback. If that platform is unavailable, retain A7 as partial;
   do not relax symlink safety or copy credentials to obtain a pass.

Return a private receipt with PR/head, exact wrapper and product versions,
platform, commands and exit codes, each positive/negative sentinel result,
observed sandbox tool exits/effects, auth bridge result, and remaining partial
rows. Public evidence includes only versions, booleans/counts, generic case IDs,
statuses and the receipt outcome. No auth data, paths, account/device names,
hook bodies, raw prompts, model transcripts or private topology are published.
