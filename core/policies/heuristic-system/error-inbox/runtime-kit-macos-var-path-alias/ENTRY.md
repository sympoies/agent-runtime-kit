# Runtime-kit path identity checks reject the macOS /var alias

## Status

- Status: open
- First observed: 2026-07-14
- Area: runtime-kit trusted executable and Hermes cleanup path identity on macOS
- Severity: medium

## Signal

On macOS, `bash scripts/ci/all.sh` reached the executable convergence
acceptance and failed only `convergence.hermes.lifecycle`. The portable source
was resolved under `/private/var/...`, while the isolated live home retained
the equivalent `/var/...` spelling. Hermes cleanup's no-follow root identity
check treated those aliases as different objects and returned
`review-needed Hermes cleanup root changed: [Errno 20] Not a directory: 'var'`.
An immediate Hermes-only rerun reproduced the same failure. The separately
required hook suite then failed its temporary-runtime cases for the same root
cause: trusted `agent-docs` executable resolution rejected equivalent temporary
paths before the fixture command could run.

## Evidence

- Raw record: not captured (manual diagnosis, 2026-07-14)
- Validation reached runtime-smoke position 8 after positions 1-7 passed.
- `bash tests/hooks/run.sh` ran 163 tests; path-independent cases passed while
  67 trusted-executable/preflight cases failed and two fixture logs were never
  created because path identity rejected the command first.
- The retained local artifact contains the full and Hermes-only run logs; raw
  temporary paths remain outside this curated entry.
- Reproduction: run `bash tests/runtime-smoke/run.sh --mode convergence
  --product hermes` from a clean macOS checkout whose temporary directory is
  visible through the `/var` to `/private/var` alias.

## Impact

Unrelated docs or records PRs cannot satisfy either declared local validation
command on affected Macs even when their content is valid. The same false
rejection can also hide genuine trusted-executable or Hermes convergence
regressions behind a host path-normalization failure.

## Current Workaround

Run the remaining scoped validations, retain the exact Hermes failure evidence,
and use Linux provider CI as the clean-path convergence authority. Do not relax
the no-follow or ownership checks; this waiver is only for the proven macOS path
alias mismatch.

## Promotion Criteria

Promote after both path spellings resolve to one canonical root before identity
validation, trusted executable and cleanup checks still reject real root
replacement and symlink attacks, and macOS plus Linux hook/convergence suites
pass.

## Next Action

Canonicalize the macOS temporary root consistently before trusted-executable and no-follow cleanup identity checks, then add /var versus /private/var regression cases for both owners.
