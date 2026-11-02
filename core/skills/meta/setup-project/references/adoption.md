# Repository Adoption

## Contract

Prereqs:

- Run inside the target repository root unless the user explicitly names
  another repository path.
- The target repository is a git work tree.
- First-time host/global runtime installation has already been handled outside
  this workflow by `scripts/setup.sh` and the released runtime install path.
- Existing project-local files are never overwritten without explicit user
  approval.

Inputs:

- Optional repository path when setting up another checkout.
- Dry-run or apply intent. Dry-run is the default.
- Required apply-time validation command for `.agents/scripts/pre-pr.sh`, passed
  as `--pre-pr-command <command>`.
- Optional `--bootstrap-command`, `--deploy-command`, and `--release-command`
  values to create retained dispatcher scripts.

Outputs:

- A repository adoption report covering `.agents/`, `.agents/scripts/`,
  `.agents/skills/`, retained dispatcher scripts, and common validation command
  candidates.
- In apply mode, `.agents/scripts/pre-pr.sh` created from an explicit validation
  command and optional retained dispatcher scripts created from explicit
  commands.
- A blocking diagnostic when an adopted repository is missing an executable
  `.agents/scripts/pre-pr.sh`.

Failure modes:

- The target path is not a git work tree.
- Apply mode is requested without `--pre-pr-command` when `pre-pr.sh` is
  missing.
- A target script already exists and replacement was not explicitly approved.
- A requested command is empty or unsupported by the generated Bash wrapper.
- The adopted repository is missing executable `pre-pr.sh`.

## Entrypoint

Resolve helper paths relative to the installed `setup-project` skill directory;
run them with the target repository as the working directory.

Use the bundled helper in dry-run mode first:

```bash
scripts/setup-project.sh \
  --repo "$repo_root" \
  --dry-run
```

Apply only after the project validation command is known:

```bash
scripts/setup-project.sh \
  --repo "$repo_root" \
  --apply \
  --pre-pr-command "bash scripts/ci/all.sh"
```

Optional retained dispatchers are explicit:

```bash
scripts/setup-project.sh \
  --repo "$repo_root" \
  --apply \
  --pre-pr-command "bash scripts/ci/all.sh" \
  --bootstrap-command "bash scripts/bootstrap.sh" \
  --deploy-command "bash scripts/deploy.sh" \
  --release-command "bash scripts/release.sh"
```

## Workflow

1. Resolve the target repository root with `git rev-parse --show-toplevel`.
2. Inspect `.agents/`, `.agents/scripts/`, `.agents/skills/`, retained
   dispatcher scripts, and common validation entrypoints.
3. Classify the repository as:
   - `unadopted` when `.agents/` is absent.
   - `partial` when `.agents/` exists but required project runtime pieces are
     incomplete.
   - `adopted` when `.agents/` exists and executable `pre-pr.sh` is present.
4. In dry-run mode, report the classification and proposed next action without
   writing files.
5. In apply mode, create `.agents/scripts/` and `.agents/skills/` as needed.
6. Create `.agents/scripts/pre-pr.sh` only from an explicit
   `--pre-pr-command`; never create a successful no-op validation gate.
7. Create optional `bootstrap`, `deploy`, and `release` scripts only from their
   explicit command flags.
8. Refuse destructive overwrite unless the user explicitly approves it.
9. Report created paths and the final adoption status.

## Boundary

This skill owns project-local runtime adoption only. It does not install host
tools, mutate global Codex or Claude runtime homes, rename the `bootstrap`
dispatcher, or create runtime-kit managed skills. Project-local skill creation
and removal use the other on-demand references in this same skill.
