# Delivery Specialist Review Gate

Use this shared gate from end-to-end delivery workflows before final PR or MR
merge. The gate gives provider delivery skills one consistent review contract
without making low-level close skills mandatory review orchestrators.

## Ownership

- `deliver-pr` owns this mandatory gate for end-to-end delivery.
- `deliver-pr` also owns explicit provider close or merge requests when the
  selected lifecycle path requires them.
- `deliver-plan-tracking-issue` relies on this delivery gate for each PR, then adds
  issue-visible evidence, runtime-finding disposition, lifecycle completion, and
  closeout requirements.
- `deliver-dispatch-plan` uses `code-review-specialists` in pre-merge or
  specialist mode before the parent decision for dispatch PRs.
- `code-review-specialists` remains read-only. It supplies scope detection,
  specialist findings, and reports; it does not fix code, post PR or MR
  comments, mark draft reviewables ready, merge, close issues, or clean
  branches.

## Mandatory Gate

For every end-to-end delivery PR or MR:

1. Resolve reviewable metadata and diff base:
   - GitHub PR: use `forge-cli --provider github pr view <pr>` or the
     equivalent `gh pr view` JSON fields to resolve the PR number, URL, base
     branch, head branch, draft state, check state, and closing issue links.
   - GitLab MR: use `forge-cli --provider gitlab pr view <mr>` or the
     equivalent `glab mr view` output to resolve the MR number, URL, target
     branch, source branch, draft state, and pipeline state.
   - Use the PR base branch or MR target branch as the `code-review-specialists`
     diff base.
2. Run deterministic scope detection with forced minimum lenses:

   ```bash
   review-specialists scope --base "$BASE_REF" --testing --maintainability --format json
   ```

3. Run the selected specialist lenses. The forced minimum means a small diff is
   still reviewed; do not skip only because `diff_lines < 50`.
4. Add risk lenses when the scope warrants them:
   - `--security` for auth, permission, credential-handling, dependency,
     supply-chain, or backend changes over 100 diff lines.
   - `--api-contract` for route, controller, API schema, OpenAPI, GraphQL,
     event, protocol, CLI, or other external contract changes.
   - `--data-migration` for schema, migration, data transform, fixture
     migration, or persistence changes.
   - `--performance` for runtime hot paths, build/runtime loops, query behavior,
     concurrency, rendering, or deployment-time execution.
   - `--red-team` when `diff_lines > 200`, a previous specialist pass found a
     critical issue, or the reviewable changes safety/security-sensitive
     behavior.
5. For doc-only, generated-only, formatting-only, or mechanical metadata
   reviewables, the review may be a short testing/maintainability pass that
   records "no concrete findings" plus why broader lenses were not selected.
6. For delivery gates with provider write access, the owning parent posts a
   compact specialist review comment through `forge-cli pr review` after each
   selected lens returns — on GitHub a native `COMMENT` review event via
   `--submit-review`, plus `--thread-file` when the lens surfaces actionable
   findings that require owner changes. Use `--decision comments-only`, the
   same semantic `--lens`, and the provider-guarded command from
   `REVIEW_OUTCOME_POSTING_CONTRACT.md`. The
   reviewer subagent remains read-only and does not post directly. Specialist
   comments report findings only; the parent records final dispositions later.

## CLI Command-Block Contract Check

When a diff touches
`core/skills/{dispatch,pr}/deliver-*/SKILL.md.tera` and changes a
command block containing a `forge-cli`, `gh`, or `glab` invocation:

1. Force the `api-contract` lens even when the reviewable is otherwise small or
   documentation-only.
2. Resolve the repository's pinned nils-cli surface from
   `docs/source/nils-cli-pin.yaml`. Run the check through
   `scripts/dev/with-nils-version.sh release:<pinned-tag>` when the ambient host
   differs, and record the exact version. The pinned nils-cli surface is the
   consumer contract; an ahead-of-pin host is not substitute evidence.
3. Check every invocation in the edited command block, not only the changed
   line:
   - For `forge-cli`, repeat the exact invocation with
     `--dry-run --format json`, require `ok=true`, and inspect every
     plan-bearing field in the command envelope for the intended subcommand,
     flags, and provider argv. This includes `data.plan`,
     `data.plan_steps[].plan`, and applicable auxiliary fields such as
     `guard_plan`, `issue_plan`, `thread_plan`, `submit_plan`, or `target_plan`.
   - Raw `gh` / `glab` read commands may run only against a safe target; verify
     their exact flags and output shape. Never execute raw provider mutations
     for review evidence. Prefer the matching `forge-cli` dry-run, or a
     provider-native documented dry-run when no forge surface exists.
4. Compare the backend plan or read output with the downstream JSON fields,
   `jq` expressions, and consumer assumptions in the skill body. For example, a
   comments consumer requires a comments-aware fetch such as
   `forge-cli issue view --with-comments`; a plain issue view must not be
   treated as comments evidence.
5. Capture the pinned version, exact commands, `ok` result, backend plans or
   read-output shape, and downstream field comparison in the `api-contract`
   specialist report or provider review comment. Missing command-contract
   evidence blocks a passing review outcome.

## Findings And Repair Loop

- Treat evidence-backed concrete findings as blocking before merge.
- Repair concrete findings on the same delivery branch when they are inside the
  accepted delivery scope.
- After repairs, rerun focused validation, provider checks or pipelines, and the
  affected specialist lenses. Post the focused follow-up specialist review
  comment with the same semantic lens before continuing to the next gate step.
  Resolve the original GitHub review threads after the fix is verified; follow-up
  pass comments normally omit `--thread-file`.
- Repeat review and repair until no concrete unresolved findings remain, or
  stop with an exact blocker and unblock action.
- Do not treat user-authorized review fixes as a successful stopping point; they
  are part of the delivery repair loop.
- Weakly evidenced concerns, accepted tradeoffs, cleanup notes, and residual
  risks must be reported by the owning delivery workflow. Issue-backed delivery
  must also record their issue-visible disposition before closeout.
- The owning delivery workflow must post the final or blocked outcome through
  `forge-cli pr review`, following
  `references/DELIVERY_REVIEW_OUTCOME_COMMENT.md`, before final merge/close.
