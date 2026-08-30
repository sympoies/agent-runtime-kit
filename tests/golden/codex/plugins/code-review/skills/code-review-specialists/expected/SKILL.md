---
name: code-review-specialists
description: >
  Review a code change through an internally selected context and quick,
  focused, or specialist depth, then return evidence-grounded findings.
---

# Code Review

Use this as the generic read-only code-review outcome. The workflow selects the
review context and the smallest depth that satisfies the request and risk, then
returns findings before any summary.

## Contract

Prereqs:

- Run inside the target git repository with `git` available on `PATH`.
- `review-specialists >=1.27.27` is installed from the released nils-cli package and
  available on `PATH`.
- Know the base ref for the diff under review, or explicitly choose one before
  running scope detection.
- Keep this workflow read-only: it does not auto-fix code, merge, close PRs/MRs,
  open/close issues, or post live provider comments.
- Dispatch the managed read-only `reviewer-<lens>` subagents for the selected
  lenses whenever the active host exposes subagent dispatch. In Codex sessions,
  Codex must dispatch the selected reviewers only when the tool schema exposes
  a custom-agent selector. The current `multi_agent_v1.spawn_agent` selector,
  `agent_type`, must be the canonical custom-agent identity from
  `manifests/agents.yaml`; `task_name` is only a workflow label and must not
  stand in for the reviewer identity. If the selector is absent or rejects the
  requested identity, do not spawn a generic child: report the host capability
  limitation and use the matching inline fallback. The parent agent owns lens
  selection, dispatch, validation, and merge.
- Leave provider review decisions to the owning PR or dispatch parent. Create a
  `review-evidence` CLI record only when findings need retained evidence.

Inputs:

- Diff base ref, optional review target summary, and optional validation
  evidence to inspect.
- Optional requested focus or forced specialist flags: `--testing`, `--security`,
  `--performance`, `--data-migration`, `--api-contract`, `--maintainability`,
  `--red-team`, or `--all-specialists`.
- Optional specialist JSONL finding files for deterministic validation, merge,
  rendering, and bundle synthesis.
- Optional confidence display threshold for merged findings.

Outputs:

- A context decision (`ad-hoc`, `follow-up`, or `pre-merge`) and a depth
  decision (`quick`, `focused`, or `specialist`) grounded in request, scope,
  outer lifecycle, and delivery context.
- Scope JSON from `review-specialists scope` describing changed files, diff
  size, stack signals, test framework signals, and suggested specialists.
- Read-only specialist findings with concrete file or evidence anchors.
- A final specialist review report using
  `references/SPECIALIST_REVIEW_REPORT_TEMPLATE.md`.
- Optional `review-evidence` records when retained workflow evidence is needed.
- No source edits, PR/MR comments, merge decisions, or close decisions from this
  workflow.

Failure modes:

- Base ref is missing or does not resolve in the target repository.
- Specialist output is malformed JSONL, lacks required fields, uses unsupported
  severity values, or omits evidence anchors.
- Findings lack enough confidence or evidence to support a concrete issue; mark
  them as residual risk instead of presenting them as verified findings.
- Caller tries to use this read-only workflow as a substitute for provider write
  authority owned by the PR or dispatch parent,
  retained evidence, browser-operation checks, CI repair automation, or
  implementation work.

## Entrypoint

Use the released CLI directly:

```bash
review-specialists scope --base "$BASE_REF" --format json
review-specialists validate --input findings.jsonl --format json
review-specialists merge --input findings.jsonl --summary-out specialist-review.md --format json
review-specialists render --profile report --input merged-findings.json --out specialist-review.md
review-specialists bundle --input findings.jsonl --out-dir "$REVIEW_OUT" --profile provider-review --format json
```

## Mode Selection

The caller requests the review outcome; the workflow selects context and depth.

- Pre-merge is a delivery context, not a review depth. Every delivered PR still
  receives a review before merge; the workflow selects quick or full depth
  inside that context.
- **Follow-up** — previous findings or review threads are supplied. Treat this
  as closed-set closure review: classify them as resolved, unresolved,
  accepted, or residual risk without starting another discovery generation.
- **Pre-merge** — the review is a delivery gate. Select quick depth only for an
  eligible L0/L1 routine diff; use the full profile for L2/L3 delivery or any
  risk trigger. Preserve comment-before-fix ordering and return a decision to
  the delivery owner.
- **Focused** — the user explicitly asks for one or more lenses. Force only
  those lenses unless scope reveals a mandatory safety lens.
- **Quick** — the diff is small or ordinary, with no migration, security,
  public API, or other specialist trigger. Dispatch `reviewer-quick` when the
  active host exposes the custom-agent selector; otherwise inspect the complete
  diff through the explicit inline fallback. Report concrete findings or a
  clean result. Include residual risk only when it is concrete and
  decision-relevant.
- **Specialist** — the diff is broad, risky, cross-cutting, or exceeds normal
  reviewer confidence. Use scope detection and the specialist workflow below.
- **Quick pre-merge** — quick depth may terminate the delivery review when scope
  is bounded, validation and checks pass, no suggested or forced risk-specialist
  trigger or unresolved review state exists, and the outer work is L0 or L1. A `pass` verdict is
  terminal review evidence for the current head; `findings` blocks merge and
  enters repair/follow-up. A verdict of `escalate` routes to the full pre-merge
  profile without changing the work tier.

All modes are read-only. When reviewer subagents are available and a mode uses
one or more lenses, the workflow must dispatch the selected reviewers. The
parent owns base selection, synthesis, and any authorized provider action.

## Workflow

1. Establish the review target and base ref. For a PR/MR, use the actual
   PR/MR base or merge-base rather than a moving `origin/main` guess. Inspect
   previous findings and delivery context before selecting a mode.
2. Select the context and review depth using the precedence above. A caller may
   prefer quick review, but scope, risk, outer lifecycle, or reviewer confidence
   can force the full pre-merge profile.
3. For **quick** mode, dispatch the canonical `reviewer-quick` custom agent
   when selector-capable dispatch is available. Otherwise state that the
   selector is unavailable and inspect the complete diff, changed tests, and
   validation evidence through the inline fallback. Report findings first with
   file anchors; if clean, state that explicitly. Include residual test or
   validation risk only when it is concrete and decision-relevant. In quick
   pre-merge context, return `pass`, `findings`, or
   `escalate` to the delivery owner; stop without manufacturing specialist work.
4. For **follow-up** mode, re-check every supplied finding, its repair hunks,
   and their direct regression surface. Classify each as `resolved`,
   `unresolved`, `accepted`, or `residual-risk`. Admit a new finding only when
   concrete evidence shows that the repair introduced a material correctness,
   security, data, migration, or public-contract regression in a reachable
   supported scenario. Otherwise do not broaden scope, add lenses, or restart
   full-diff discovery.
5. Run deterministic scope detection for the initial pre-merge discovery and
   for **focused** or **specialist** ad-hoc review. A follow-up to a completed
   pre-merge discovery reuses only the affected lenses and does not rerun
   general scope selection:

   ```bash
   review-specialists scope --base "$BASE_REF" --format json
   ```

6. Select specialists:
   - In focused mode, use the requested lenses.
   - In the full pre-merge profile, always include `testing` and
     `maintainability`.
   - In specialist mode, use the scope suggestions and rules below.
   - Always consider `testing` and `maintainability` for larger diffs.
   - Consider `security` for auth changes or backend changes over 100 diff
     lines.
   - Consider `performance` for backend or frontend runtime changes.
   - Consider `data-migration` for migration, schema, or data transform changes.
   - Consider `api-contract` for route, controller, API schema, OpenAPI,
     GraphQL, or protocol changes.
7. Resolve the matching managed reviewer through the manifest inventory:
   `reviewer-quick`, `reviewer-testing`, `reviewer-maintainability`,
   `reviewer-security`, `reviewer-performance`, `reviewer-data-migration`,
   `reviewer-api-contract`, and `reviewer-red-team`. These are installed at
   `~/.codex/agents/reviewer-<lens>.toml` and
   `~/.claude/agents/reviewer-<lens>.md`.
8. Dispatch the selected read-only reviewer subagents one per lens, handing each
   the base ref and scope; each inspects read-only and returns JSONL findings for
   its lens. In Codex, set `agent_type` to the canonical custom-agent identity
   exactly as rendered from the manifest. `task_name` is only a workflow label;
   an underscore-form task label never selects the profile. If the active tool
   schema lacks `agent_type`, or the canonical identity is rejected, do not
   spawn a generic child. State the limitation and run the same lenses through
   the inline fallback by reading `references/specialists/`. You stay the
   parent: you own base-ref selection, lens selection, dispatch, fallback
   justification, and the validation/merge steps below.
9. Collect each subagent's JSONL findings (or the inline equivalent) following
   `references/SPECIALIST_REVIEW_CONTRACT.md`. Treat malformed JSONL, missing
   required fields, unsupported severities, or absent evidence anchors as a
   workflow failure or residual risk for that lens — never promote it to a
   verified finding. Mark unverifiable claims as residual risk, not findings.
10. Validate and merge findings:

   ```bash
   review-specialists validate --input findings.jsonl --validate-paths --format json
   review-specialists merge --input findings.jsonl --summary-out specialist-review.md --format json
   ```

11. Run red-team only after the selected specialists when a selected specialist
   produced a `critical` finding, the reviewer forced it, or `diff_lines > 200`
   and the change crosses a material security, data, migration, public-contract,
   concurrency, or other safety boundary. Raw diff size alone is insufficient.
   Dispatch `reviewer-red-team` with `agent_type = "reviewer-red-team"`
   when selector-capable subagent dispatch is available. If the selector is
   unavailable or blocked, state the fallback reason and run the same red-team
   lens through the inline fallback from `references/specialists/red-team.md`.
   Hand it the
   merged first-wave findings so it can probe cross-cutting failure modes. Pass
   the red-team JSONL through `review-specialists validate`, then append it to
   the first-wave JSONL and run `review-specialists merge` again over the
   combined input so duplicate
   fingerprints, confirming specialists, and confidence ordering are resolved in
   the final report.
12. Use the report template for the final synthesis. For either pre-merge
   profile, apply
   `references/DELIVERY_SPECIALIST_REVIEW_GATE.md` and
   `references/REVIEW_OUTCOME_POSTING_CONTRACT.md`; the delivery owner, not a
   reviewer, posts provider comments and makes the merge decision. For every
   mode, the recommended next step may route to the dispatch parent's
   independent-review phase, a normal implementation workflow, or a retained
   `review-evidence` CLI record, but this workflow does not execute that decision.

## Boundary

`code-review-specialists` owns mode selection, read-only diff inspection, scope
detection, specialist selection, reviewer-subagent dispatch, follow-up
classification, validation and merge of returned findings, and the final
report.
Each `reviewer-<lens>` subagent owns only its read-only lens.
This workflow does not fix code, post PR or MR review comments, mark a draft
reviewable ready, merge, close issues, or execute the recommended next step —
those belong to the owning PR / MR or dispatch parent and the evidence control plane.

## References

- Reviewer subagent sources:
  `core/agents/code-review/reviewer-<lens>/AGENT.md.tera`
- Specialist review contract:
  `references/SPECIALIST_REVIEW_CONTRACT.md`
- Report template:
  `references/SPECIALIST_REVIEW_REPORT_TEMPLATE.md`
- Specialist prompts:
  `references/specialists/`
- Delivery specialist review gate:
  `references/DELIVERY_SPECIALIST_REVIEW_GATE.md`
- Delivery review outcome comment:
  `references/DELIVERY_REVIEW_OUTCOME_COMMENT.md`
- Specialist review comment:
  `references/SPECIALIST_REVIEW_COMMENT.md`
- Review outcome posting contract:
  `references/REVIEW_OUTCOME_POSTING_CONTRACT.md`
- Delivery review outcome schema:
  `references/DELIVERY_REVIEW_OUTCOME_SCHEMA.md`
- Evidence routing policy:
  `core/policies/evidence-control-plane.md`
