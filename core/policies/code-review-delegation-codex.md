# Codex Code Review Delegation

Codex sessions must use managed subagent reviewers for code-review requests
only when the active host exposes a custom-agent selector. On the current
Codex dispatch surface, set `agent_type` to the canonical custom-agent identity
from `manifests/agents.yaml`.

- Prefer `reviewer-quick` for small routine diffs and focused
  `reviewer-<lens>` agents for broad or risky diffs.
- Treat `task_name` as a workflow label only. It does not select a reviewer
  profile, and underscore-form task labels are not reviewer identities.
- The parent agent owns base-ref selection, lens selection, synthesis,
  validation, follow-up code, and PR action.
- Reviewer subagents inspect read-only and report findings.
- If `agent_type` is absent from the tool schema or rejects the canonical
  reviewer name, do not spawn a generic child. Report the host capability
  limitation, run the same review through the inline fallback, and state that
  fallback in the result.
