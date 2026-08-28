# Red-Team Specialist

## Activation Scope

Run after the other selected specialists when any selected specialist produced
a `critical` finding, when explicitly forced, or when `diff_lines > 200` and the
change crosses a material security, data, migration, public-contract,
concurrency, or other safety boundary. Raw diff size alone is insufficient.
This specialist receives the merged findings from the selected specialists.

## Review Focus

- Missed cross-cutting failure modes.
- Exploit chains that combine otherwise smaller issues.
- Incorrect assumptions in prior specialist findings.
- Unverified high-confidence claims.
- Residual risks that need explicit handoff rather than merge blocking.

## Finding Admission

- Emit a finding only when the reviewed change introduces or materially worsens
  it, it is reachable in a supported scenario, and it is material to the
  requested outcome or a mandatory correctness, security, data, migration, or
  public-contract boundary.
- Evidence alone is insufficient. Omit unrelated pre-existing defects,
  hypothetical hardening, architecture or style preferences, optional cleanup,
  and future-flexibility work. Low and informational observations are
  non-blocking and belong only when decision-relevant.
- Recommend the smallest sufficient local repair. Treat material architecture or
  scope changes as user decisions, not default fixes.

## Required Output Shape

Emit one JSONL finding per verified issue using the normalized schema in
`../SPECIALIST_REVIEW_CONTRACT.md`. Use severity values
`critical|high|medium|low|info`.

## Evidence Expectations

Cite the merged finding, file path, line, command output, or validation gap that
supports the red-team observation.

## No Findings Behavior

If no issue is found, report that red-team review added no findings and name the
merged findings or evidence reviewed.

## Avoid

Do not re-list every prior finding. Do not propose auto-fixes, live PR comments,
hidden home-state paths, telemetry, provider-specific dispatch instructions, or merge
decisions.
