# Runtime-kit path identity checks reject the macOS /var alias

## Status

- Status: promoted
- First observed: 2026-07-14
- Resolved: 2026-08-28
- Area: runtime-kit trusted executable and Hermes cleanup path identity on macOS
- Severity: medium
- Durable link: `https://github.com/sympoies/agent-runtime-kit/pull/67`
- Durable link: `https://github.com/sympoies/agent-runtime-kit/issues/66`

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

None. The original action — "canonicalize the macOS temporary root consistently
before trusted-executable and no-follow cleanup identity checks, then add /var
versus /private/var regression cases for both owners" — is complete; see
Resolution.

Lifecycle link: `https://github.com/sympoies/agent-runtime-kit/pull/67`

## Resolution

Promoted 2026-08-28. Every promotion criterion is now satisfied, verified
first-hand on the reporting host.

- **Both spellings resolve before identity validation.** The trusted-executable
  owner no longer compares `realpath(candidate)` against the whole lexical path.
  `hook_common.resolves_within_its_directory` anchors the check at the
  already-resolved directory, so a symlinked *ancestor* — the `/var` to
  `/private/var` alias this entry reported — no longer decides trust, while a
  symlinked *leaf* still does. The helper is shared, so
  `block-unsafe-default-delivery` and `session-coordination-guard` cannot drift
  apart again. Separately, `--docs-home` is now canonicalized by all four hooks
  that build it, where previously only `pre-edit-intent-gate` did; that was the
  second half of the same alias mismatch and it also split the preflight cache
  key.
- **Both owners still reject root replacement and symlink attacks.**
  Trusted-executable: `test_a_symlink_out_of_the_per_user_root_is_still_rejected`
  proves a link planted inside a trusted bin that points out of it stays
  untrusted, with and without a symlinked ancestor above it, and
  `test_delivery_still_rejects_an_unrelated_directory` is unchanged. Cleanup:
  the no-follow root-swap rejection at
  `tests/runtime-smoke/cases/meta/run.sh:1699` still asserts
  `review-needed Hermes cleanup root changed after discovery`.
- **macOS and Linux suites pass.** On the reporting macOS host:
  `bash tests/hooks/run.sh` is 423/423 (18 were failing, 6 of them this entry's
  class); `bash tests/runtime-smoke/run.sh --mode convergence --product hermes`
  is 3/3, including `convergence.hermes.lifecycle`, the case this entry opened
  on; `bash scripts/ci/all.sh` is positions 1-17 OK. On Linux, provider CI is
  green on both the minimum and validated lanes.

The entry's Next Action asked to "canonicalize the macOS temporary root
consistently before trusted-executable and no-follow cleanup identity checks,
then add /var versus /private/var regression cases for both owners". The
trusted-executable half and the regression cases landed in
`sympoies/agent-runtime-kit#67`. The Hermes cleanup half was already passing
independently by the time this was re-checked, so no cleanup change was needed;
its failure is not reproducible on the reporting host today.

One caveat recorded rather than left implicit: the anchored check does admit one
case the whole-path comparison refused — a trusted bin directory that is itself
a symlink. `is_managed_cli_home_bin` resolved both sides and admitted such a
directory anyway, and anyone able to replace `~/.local/nils-cli/bin` with a link
can replace the binaries inside it, so the refusal bought nothing. `/usr/bin` is
unaffected: `realpath` cannot redirect it.

Related: the 12 remaining macOS hook failures fixed in the same PR were a
different root cause (bash 3.2 mis-parsing a heredoc body inside `$( … )`,
`sympoies/agent-runtime-kit#65`) and are not part of this entry.

## Archive

- Archived: 2026-08-28
- Reason: Completed entry archived out of the active error inbox.
