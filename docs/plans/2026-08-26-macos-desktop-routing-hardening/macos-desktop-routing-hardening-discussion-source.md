# Implementation Source: Harden macOS desktop surface selection and rerunnable flows

## Status

- Status: ready for L2 plan-tracking execution
- Date: 2026-08-26
- Plan owner: `sympoies/agent-runtime-kit`
- Implementation repository: `sympoies/agent-runtime-kit` only
- Backend: unchanged. Peekaboo stays pinned at `v4.2.2` behind `macos-agent`
  adapter v3; the nils-cli floor stays `>= 1.27.3`
- Open questions carried into execution: none

## Goal

Make `computer-use.macos-desktop` choose the *cheapest surface that can prove
the outcome* instead of defaulting to GUI driving, refuse degenerate
accessibility targets before they produce false success, and express a
repeatable desktop flow as a reviewable tracked asset rather than transcript
prose.

The skill keeps its existing mechanics contract. Nothing here changes the
adapter, the backend pin, the tool profiles, the journal, or the replay
ceiling. Every change lands in repo-owned source, policy, reference, and test
surfaces.

## Inputs And Evidence

- [U1] The maintainer asked whether a more mature alternative to Peekaboo
  exists for fully autonomous macOS operation, automated testing, and
  autonomous app/browser use.
- [U2] After review the maintainer chose to keep Peekaboo, treat `cua-driver`
  as an optional future second backend, and execute items 1-4 of the
  recommended sequence now. The `lume` macOS VM fixture (item 5) is explicitly
  deferred as a separate environment decision.
- [W1] `openclaw/Peekaboo` is actively maintained: `v4.0.0` (2026-08-10) was a
  ground-up command-surface cleanup and `v4.2.2` (2026-08-20) is the current
  latest release, confirmed through the GitHub releases API. The repository
  pin is therefore current, not behind.
- [W2] macOSWorld (arXiv 2506.04135, "macOSWorld: A Multilingual Interactive
  Benchmark for GUI Agents", 202 tasks over 30 applications) reports
  proprietary computer-use agents above a 30% success rate and open-source
  lightweight research models below 5%. GUI driving is therefore a
  low-yield primitive and must not be the first choice when a deterministic
  surface exists.
- [W3] Public discussion of macOS accessibility automation consistently
  reports that Chromium-family, Qt, OpenGL/Canvas, and similar applications
  expose degenerate or empty accessibility trees, and that a credible tool
  either handles that explicitly or silently fails for some users.
- [F1] `core/skills/computer-use/macos-desktop/SKILL.md.tera` routes only
  local-versus-SSH, evidence mode, runtime, and journal root. It contains no
  rule preferring a deterministic surface and never mentions `browser-test`.
- [F2] `core/policies/browser-test-routing.md` already routes rendered-page,
  Playwright, HTTP, and native-desktop claims, and already sends browser
  chrome and cross-application claims *to* the desktop route. The reverse
  direction does not exist.
- [F3] `docs/source/macos-agent-capability-matrix.md` marks `Browser DOM/CDP`
  as `disabled` with the contract text "Use a separately governed browser
  route" but never names that route.
- [F4] The matrix classifies capabilities but has no row for application
  classes whose accessibility tree is unusable, so an agent has no published
  basis to stop.
- [F5] Peekaboo v4 removed the `.peekaboo.json` runner and the skill correctly
  replaced it with individually reviewed chained `exec` calls. The consequence
  is that a repeatable flow now exists only as transcript prose; there is no
  tracked, reviewable fixture a rerun or CI can consume.
- [F6] `## Acceptance Standard` item 4 requires that "the same fixture can run
  independently without a blind mutation retry" but samples exactly one run,
  so a flaky flow can pass acceptance.
- [F7] `scripts/ci/all.sh` is the canonical gate and already covers render,
  golden, drift, smoke, and hooks. `tests/runtime-smoke/cases/computer-use/run.sh`
  holds the source-and-rendered contract probe where new assertions belong.

## Decisions

1. **Keep Peekaboo.** [W1] The backend is current and shipping faster than any
   alternative. No pin change, no backend abstraction work in this plan.
2. **Deterministic surfaces outrank GUI driving.** [W2] Add a published
   selection ladder. The ladder names surfaces that run *outside* the adapter;
   it does not widen the adapter, and the adapter `shell` hard-deny is
   unchanged.
3. **AX degeneracy is a published boundary, not an improvisation.** [W3][F4]
   Diagnose it from a fresh observation, then either take the already-governed
   bounded coordinate fallback or stop with a blocker. Publish the negative
   application classes in the matrix.
4. **Browser routing becomes reciprocal.** [F2][F3] The desktop skill names
   `browser-test` for DOM-level claims and the matrix names the route. The
   handoff states who owns session state, artifact directories, and evidence
   links.
5. **A repeatable flow becomes a tracked fixture.** [F5] Define a declarative
   fixture whose runner is exactly the chained `exec` calls the skill already
   documents. No adapter change, and `journal replay-plan` is *not* repurposed
   as the CI mechanism because its `never` classification and SSH
   `eligible=false` rows are deliberate safety ceilings.
6. **Acceptance samples stability.** [F6] Require repeated independent runs and
   a recorded postcondition success rate before a flow is called
   unattended-safe.
7. **Upstream freshness is audited, not assumed.** [W1] Add a drift check that
   compares the pinned backend against the declared upstream so a new Peekaboo
   release surfaces as a reviewable diff.

## Non-Goals

- Replacing Peekaboo, adding `cua-driver`, or abstracting the backend.
- Adopting `lume` / `cua-sandbox` macOS VMs as a test fixture. [U2]
- Changing the nils-cli pin, adapter contract, tool profiles, journal schema,
  replay classification, or any hard-denied capability.
- Granting the adapter shell access. Deterministic surfaces named by the
  ladder are caller-side, outside the adapter boundary.
- Claiming DOM, CDP, or rendered-browser capability for this skill.

## Acceptance Criteria

- The rendered skill for Codex, Claude, and Hermes publishes the surface
  selection ladder, the AX-degeneracy gate, the reciprocal browser handoff, the
  flow-fixture reference, and the stability threshold.
- The capability matrix publishes the negative application classes, names the
  browser route, and records the backend freshness audit.
- A tracked example fixture exists and its documented runner is the chained
  `exec` shape already in the skill.
- `bash scripts/ci/all.sh` passes once against the final change.
- Meaningful red was captured in the computer-use smoke probe before the
  production `.tera` edit.

## Privacy And Safety

Provider-visible records use generic runtime roles. Host aliases, users,
private paths, credentials, and raw desktop artifacts stay in private
`agent-out` evidence. No change here relaxes TCC handling, approval boundaries,
sensitive-value suppression, or replay refusal.
