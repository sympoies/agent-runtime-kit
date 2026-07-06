# Inspecting container/stack APIs with broad jq projections prints secret env values into the transcript

## Status

- Status: promoted
- First observed: 2026-07-02
- Area: agent secret hygiene; container/orchestrator API inspection
- Severity: medium

## Signal

During the g14→sympoies takeover session (2026-07-02), the agent inspected a
restored Portainer stack record via `GET /api/stacks/{id}` and projected the
object with a jq expression that included the `Env` field. Portainer stores the
stack's environment values verbatim, so a Telegram bot token and chat id were
printed into the conversation transcript — violating the never-print-secrets
policy. The same failure shape applies to `docker inspect` (`.Config.Env`),
`docker compose config` (resolved `environment:`), Kubernetes secrets/env
dumps, and any orchestrator "show me this object" call: exploratory projections
of unknown API objects default to including env-like maps.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-02); the leak lives only
  in the local session transcript under `$HOME`.
- The safe pattern was already present in the same codebase:
  `project-add-live-repo.sh` reads `WEBHOOK_GITHUB_SECRET` from
  `docker inspect` by NAME via an awk filter and prints only its length —
  the gap is that nothing steers exploratory (non-scripted) API inspection
  toward the same discipline.

## Impact

A secret value lands in the session transcript (and potentially in retained
summaries or handoffs derived from it), forcing an out-of-band credential
rotation — in this case a Telegram bot token rotation via BotFather, which only
the user can perform.

## Current Workaround

When exploring container/stack/orchestrator API objects, never project whole
objects or `Env`/`environment` maps. Select only the needed non-secret fields,
or redact env-like maps in the projection, e.g.
`jq '{Name, Status, Env: (.Env | length)}'` or `jq '.Env |= "<redacted>"'`.
Read specific values by name and report only presence/length, mirroring the
`read_secret` pattern in `project-add-live-repo.sh`. If a value does leak,
rotate the credential and say so plainly.

## Promotion Criteria

Promote after a durable guardrail is implemented, validated, and linked from
this entry: a redaction rule for env-like fields in the relevant policy surface
(e.g. the `files-hooks-validation` or `external-facts` policy docs, or a shared
helper for secret-safe container/API inspection) that future sessions load
before poking orchestrator APIs.

## Next Action

None. Secret-safe API inspection guardrail added to core/policies/files-hooks-validation.md; it prohibits broad env-like object projections, requires redacted/narrow field selection, and routes leaked values to credential rotation rather than durable evidence.

## Archive

- Archived: 2026-07-06
- Reason: Policy guardrail added
- Durable link: `core/policies/files-hooks-validation.md`
