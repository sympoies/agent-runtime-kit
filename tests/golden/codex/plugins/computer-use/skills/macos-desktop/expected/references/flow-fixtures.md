# Declarative Flow Fixtures

## Why This Exists

Peekaboo v4 removed the `.peekaboo.json` runner, and this skill replaced it
with individually reviewed chained `exec` calls. That is the right mechanics
boundary, but it leaves a repeatable flow living only in a transcript. A flow
that a person will rerun, hand to someone else, or gate a change on needs a
tracked, reviewable definition.

A flow fixture is that definition. It adds no mechanics: the runner is exactly
the chained `exec` calls the skill already publishes, in one homogeneous
journal directory, checking each postcondition before continuing.

`journal replay-plan` is not the rerun mechanism. Its `never` classification
and ineligible SSH rows are deliberate safety ceilings on replaying recorded
input, not a limitation to work around. A fixture re-derives every step from a
fresh observation instead of replaying a recorded one.

## Shape

Store a fixture next to the work it proves, in the repository that owns the
flow. One fixture describes one outcome against one application.

```yaml
fixture: calculator-clear-to-zero
target_app: Calculator
intent: Prove the clear control returns the display to zero
runtime: app
evidence_mode: minimal
transport: local

setup:
  - intent: Launch the disposable fixture target
    argv: [app, launch, Calculator]
    expected: Calculator is frontmost

steps:
  - intent: Observe the current control set
    argv: [see, --app, Calculator, --json]
    observe: true
  - intent: Enter a known non-zero value
    argv: [click, --app, Calculator, --on, "$digit_three_id", --json]
    expected: Calculator display reads 3
  - intent: Clear the accumulated value
    argv: [click, --app, Calculator, --on, "$clear_button_id", --json]
    expected: Calculator display reads 0

reset:
  - intent: Return the fixture to its disposable baseline
    argv: [app, quit, --app, Calculator]
    expected: Calculator is not running

stop_when:
  - A step reports a failure class other than a clean postcondition miss
  - The accessibility tree for the declared target is degenerate
  - Any action would leave the declared target application
```

Field rules:

- `fixture`, `target_app`, and `intent` identify the outcome. Keep them
  specific enough that a reviewer can tell what is being proved.
- `runtime`, `evidence_mode`, and `transport` pin one homogeneous journal
  tuple. Changing any of them requires a new sibling run directory, so a
  fixture never mixes them.
- `observe: true` marks a read-only step.
  Every mutating step declares an observable postcondition in `expected`;
  a mutating step without one is an invalid fixture, not a shortcut.
- Element ids in `argv` are placeholders resolved from the immediately
  preceding `see` result. Never freeze a literal element id into a fixture —
  ids are snapshot-scoped and a stale id is a wrong-target defect.
- `setup` and `reset` keep each run independent. A fixture that only passes as
  the second run in a session is not independent.
- `stop_when` is explicit so a run halts instead of improvising.

## Running One

Allocate one homogeneous child directory, then issue each step as its own
reviewed `exec` call. This is the same shape as `## Multi-step Flows` in the
skill; the fixture only decides the order and the postconditions.

```bash
flow_out="$session_root/local-flow-minimal-app"
mkdir -p "$flow_out"

macos-agent exec \
  --out-dir "$flow_out" \
  --intent "Observe the current control set" \
  --runtime app \
  -- see --app Calculator --json

macos-agent exec \
  --out-dir "$flow_out" \
  --intent "Clear the accumulated value" \
  --expected "Calculator display reads 0" \
  --runtime app \
  -- click --app Calculator --on "$clear_button_id" --json
```

Check each result and its postcondition before issuing the next step. Exit zero
confirms adapter execution, not user-visible success. After a partial failure,
inspect the journal and resume only from a newly observed state.

Do not expand a fixture into a shell loop, a command bundle, or a generated
script that sends unreviewed steps. The reviewability of each step is the point.

## Stability

A single green run does not make a flow trustworthy. Run the fixture at least
three times independently, each with its own `setup` and `reset`, and read the
observed postcondition success rate back from the journals.

- Full success across the independent runs: the flow converges and may be
  called unattended-safe.
- Anything lower: report the observed rate and the failing step, and treat the
  flow as not unattended-safe.

Repeated independent runs are not a blind mutation retry. Retrying a failed
non-idempotent action inside one run remains forbidden; rerunning a fixture
from a clean reset is how stability is measured.

Over SSH the journal is a usable source for that rate from `macos-agent`
1.27.12 onward. Each SSH `exec` merges its transferred journal into `--out-dir`
and the chained steps accumulate under one `run_id`, so `steps.jsonl` reads back
directly the same way a local-transport journal does. Against an older adapter
each SSH `exec` replaced the journal and retained only the last step; there,
record the per-run postcondition outcome as the fixture runs and report the rate
from that record, naming the source.

## Privacy

Fixtures are tracked source. Keep host aliases, user names, absolute home
paths, window titles, and any real credential out of them. Use a disposable
fixture target and a synthetic value for any sensitive-input step, and let the
adapter's `sensitive` evidence mode suppress the value in the journal.
