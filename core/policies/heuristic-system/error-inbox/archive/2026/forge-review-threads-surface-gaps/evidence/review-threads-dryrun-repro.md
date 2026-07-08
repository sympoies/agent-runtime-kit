# forge-cli pr review-threads list --dry-run is not dry (v1.9.1)

## list --dry-run makes a LIVE gh call (against a non-existent PR)

$ forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json pr review-threads list 9999999
{"schema_version":"cli.forge-cli.error.v1","ok":false,"error":{"code":"backend_error",
 "message":"gh exited with status 1","details":{"detail":"GraphQL: Could not resolve to a
 PullRequest with the number of 9999999. (repository.pullRequest)"}}}

## contrast: checks --dry-run plans OFFLINE (no call)

$ forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json pr checks 9999999
{"schema_version":"cli.forge-cli.pr.checks.v1","ok":true,"data":{"provider":"github",
 "plan":["gh","pr","checks","9999999", "..."]}}

## resolve/reply --dry-run also plan OFFLINE (correct)

$ forge-cli ... --dry-run pr review-threads resolve 9999999 --thread PRRT_x
{"schema_version":"cli.forge-cli.pr.review-threads.resolve.v1","ok":true,
 "data":{"provider":"github","plan":["gh","api","graphql", "..."]}}

Upstream: sympoies/nils-cli#887 (dry-run), sympoies/nils-cli#888 (umbrella).
