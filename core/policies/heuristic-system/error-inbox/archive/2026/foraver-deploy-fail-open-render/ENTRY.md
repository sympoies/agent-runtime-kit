# Foraver deploy continues after secret render failure

## Status

- Status: promoted
- First observed: 2026-07-12
- Area: infra-deploy
- Severity: high

## Signal

The foraver infra target used separate shell commands for render and startup:
`$(MAKE) render; $(MAKE) up`. A failed secret render therefore did not stop
`make deploy STACK=foraver`; Compose could continue with an existing rendered
`.env`.

## Evidence

- Raw record: `<workspace>/.local/state/agent-runtime-kit/out/projects/graysurf__foraver/20260713-040723-production-deploy/skill-usage.record.json`
- Original run: `meta:deploy` ended `worked_around` after the render submake
  failed but the documented infra fallback completed production deployment.
- Durable infra fix: [sympoies-infra PR #72](https://github.com/graysurf/sympoies-infra/pull/72)
  changed the target to `render && up` and added an isolated fail-closed
  regression.
- Governed crawler target: [sympoies-infra PR #73](https://github.com/graysurf/sympoies-infra/pull/73)
  added crawler-only recreation plus watchdog validation.
- App entrypoint: [foraver PR #80](https://github.com/graysurf/foraver/pull/80)
  added `.agents/scripts/deploy.sh` with clean-revision, rendered-env,
  ordering, and fail-closed contract coverage.
- Post-fix production validation ran the app-owned deploy entrypoint
  successfully, recreated the crawler, passed web/public smoke and watchdog
  readiness, confirmed database connectivity, and observed a fresh crawler
  heartbeat.

## Impact

A render or secret-store failure could be masked while deployment continued
with stale or incorrect credentials. The command could exit successfully even
though its prerequisite state was not regenerated, giving operators a false
deployment result.

## Current Workaround

Before the fix, run render as a separate fail-fast prerequisite and verify the
expected rendered env exists before invoking Compose. The supported path is now
the foraver-owned `.agents/scripts/deploy.sh`, which delegates to the
infra-owned fail-closed targets.

## Promotion Criteria

Promote when the infra deploy target cannot run `up` after render fails, an
isolated regression proves that ordering, and the governed app deploy path
passes post-fix production smoke and readiness validation.

## Next Action

None. The fail-closed infra fix and governed app deploy path are implemented, validated, and linked above.

## Archive

- Archived: 2026-07-12
- Reason: Durable fail-closed deploy path merged and passed post-fix production validation.
- Durable link: `https://github.com/graysurf/foraver/pull/80`
