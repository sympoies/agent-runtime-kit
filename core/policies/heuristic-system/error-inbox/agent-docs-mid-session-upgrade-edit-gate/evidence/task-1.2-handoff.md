# Handoff — resume agent-console#375 Sprint 1 (nils-cli daemon)

> Written 2026-07-20 by the blocked session. Task 1.1 is complete + tested on
> disk; task 1.2 is partially landed. This doc has the EXACT remaining edits so
> a fresh session resumes fast.

## Why the previous session stopped (environment, not code)

Mid-session `nils-cli` was upgraded by Homebrew **1.25.5 → 1.25.6**. The running
session's agent-docs hook bootstrap was initialized under 1.25.5, so every
`agent-docs session prepare` for the **worktree** now returns
`agent-docs-bootstrap-shape-mismatch` and the pre-edit gate blocks all worktree
edits. `sync-runtime-surfaces --apply --product claude --no-pull` was run (it
refreshed on-disk surfaces to producer_version 1.25.6) but could NOT re-align
the in-session bootstrap. **Fix = restart the Claude Code session** (ideally
`cwd` = the worktree). A fresh session bootstraps cleanly against 1.25.6.

Non-obvious workaround learned: when the pre-edit hook cues
`agent-docs ... session prepare ... --phase edit`, that exact `--phase edit`
shape shape-mismatches; running the SAME command **without `--phase`** activates
project-dev cleanly (worktree-fallback `auto` resolves it to the primary
`da183932` identity). Use the no-phase form if the gate acts up again.

Route to heuristic-inbox (L1): "agent-docs edit gate un-satisfiable in-session
after a mid-session nils-cli brew upgrade (1.25.5→1.25.6); bootstrap-shape-mismatch
on every prepare variant; only a session restart recovers." (still needs the
user's decision before any provider mutation.)

## Coordinates

- Tracker: https://github.com/serenvia/agent-console/issues/375 (L2 tracking,
  status blocked, current task 1.1→ now 1.2). Durable plan/source/state live in
  the issue comment snapshots (the local plan bundle at
  `…/worktrees/agent-console-8926ce42/next-prompt-account/docs/plans/2026-07-20-next-prompt-codex-account/`
  is only a TEMPLATE — rehydrate from the issue comments).
- Worktree: `$HOME/.local/state/agent-runtime-kit/worktrees/nils-cli-f26be630/next-prompt-codex-account`
- Branch: `feat/next-prompt-codex-account`, baseline `488de456` (== origin/main).
- Test-first evidence: `./test-first-evidence.json` (same dir as this file).
- Package: `nils-agent-session`; local checks: `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`.
- cargo is a rustup shim: use `<workspace>/.cargo/bin/cargo` (not on PATH in tool shells).

## Design summary

Add an additive **durable next-account intent** distinct from the applied
binding. `selected_account` (the applied account) NEVER changes until an apply
succeeds — the badge always names the currently-applied account. Next intent
lifecycle: `queued → applying → (success: binding flips to B + intent cleared |
failure: intent = failed, binding stays A)`. Any live/malformed next intent
fences the next prompt (`ensure_input_allowed`). Queueing a different account
cancels auto-resume. Applied by the daemon at the idle (Waiting) boundary.

## DONE (on disk, verified green before the upgrade)

### Task 1.1 — `crates/agent-session/src/codex_account.rs` (COMPLETE)
- `NEXT_SCHEMA_VERSION`, `NEXT_KEY`, `DurableNextAccount`, `DecodedNext`,
  `CodexNextAccountView`, `CodexAccountView.next: Option<CodexNextAccountView>`.
- `view_for_record` projects `next` (feature-off branch = None).
- `ensure_input_allowed` fences on any present/malformed next (`codex-account-next-pending`).
- Public fns: `queue_next_account`, `cancel_next_account`, `begin_next_apply`,
  `finish_next_apply`, `recover_next_after_restart`, `pending_next_apply`,
  `has_pending_next`; helpers `decode_next`/`store_next`/`clear_next`/`next_view`/
  `next_pending_error`/`invalid_next_error`.
- 12 new tests + existing 19 pass: `cargo test -p nils-agent-session codex_account` → **31 passed**.

### Task 1.2 partial — `crates/agent-session/src/serve.rs` (LANDED)
- `codex_account_handler`: on `begin_switch_binding` error `codex-account-session-busy`
  (turn working), falls back to `queue_next_account` and returns the queued view.
- Also: 3 test `CodexAccountView` literals got `next: None,`.

## ⚠️ SAFETY — do NOT build/PR/deploy the current on-disk state as-is
The serve routing queues a next intent, but the idle-drain (below) is NOT yet
wired, so `ensure_input_allowed` would fence the next prompt with nothing to
apply it. Either finish task 1.2 (below) OR revert the serve routing first.

## REMAINING task 1.2 edits (ready to paste)

### 1) `crates/agent-session/src/codex_app_server.rs`

**a. `ControlCommand` enum — add after the `BindAccount { … }` variant (~line 1698):**
```rust
    /// Drain and apply a queued next-account intent if the turn is idle. Used by
    /// the periodic idle-boundary drive; a no-op when nothing is drainable.
    ApplyNext {
        response: oneshot::Sender<Result<(), String>>,
    },
```

**b. `impl ControlHandle` — add after the `bind_account` method (~line 1774):**
```rust
    pub(crate) async fn apply_next(&self) -> Result<(), String> {
        let (response, receive) = oneshot::channel();
        tokio::time::timeout(CONTROL_SUBMIT_TOTAL_TIMEOUT, async {
            self.sender
                .send(ControlCommand::ApplyNext { response })
                .await
                .map_err(|_| "codex control connection unavailable".to_string())?;
            receive
                .await
                .map_err(|_| "codex control connection closed".to_string())?
        })
        .await
        .map_err(|_| "Codex next-account apply timed out".to_string())?
    }
```

**c. Replace `apply_account_binding` (currently ~1782-1861) with the extracted
login helper + refactored binding apply + the next-apply helper:**
```rust
/// Resolve credentials and drive the app-server external-auth login for
/// `account`. Mutates only the live app-server; never touches durable binding
/// or next-intent state. Returns a fail-closed reason code on failure.
async fn drive_external_auth_login(
    websocket: &mut tokio_tungstenite::WebSocketStream<UnixStream>,
    request_id: &mut u64,
    account: &str,
) -> Result<(), &'static str> {
    let resolve_account = account.to_string();
    let credentials = tokio::task::spawn_blocking(move || {
        crate::codex_account::resolve_account(&resolve_account, false)
    })
    .await
    .map_err(|_| "broker_failed")?
    .map_err(|_| "broker_failed")?;

    *request_id = request_id.saturating_add(1);
    if send_json(
        websocket,
        external_auth_login_request(
            *request_id,
            &credentials.access_token,
            &credentials.chatgpt_account_id,
            credentials.chatgpt_plan_type.as_deref(),
        ),
    )
    .await
    .is_err()
    {
        return Err("apply_failed");
    }
    let result =
        receive_response_with_timeout(websocket, *request_id, None, None, CONTROL_RESPONSE_TIMEOUT)
            .await;
    if !result
        .as_ref()
        .is_ok_and(|result| result.get("type").and_then(Value::as_str) == Some("chatgptAuthTokens"))
    {
        return Err("apply_failed");
    }
    Ok(())
}

async fn apply_account_binding(
    websocket: &mut tokio_tungstenite::WebSocketStream<UnixStream>,
    context: &CliContext,
    record: &SessionRecord,
    request_id: &mut u64,
    account: &str,
    revision: u64,
) -> Result<crate::codex_account::CodexAccountView, String> {
    let launch_id = record
        .runtime
        .as_ref()
        .map(|runtime| runtime.launch_id.clone())
        .ok_or_else(|| "Codex runtime identity is missing".to_string())?;
    match drive_external_auth_login(websocket, request_id, account).await {
        Ok(()) => {
            finish_account_binding(context, record, &launch_id, account, revision, Ok(())).await
        }
        Err(reason) => {
            let _ =
                finish_account_binding(context, record, &launch_id, account, revision, Err(reason))
                    .await;
            Err(format!("Codex external-auth login failed: {reason}"))
        }
    }
}

/// At the idle boundary, apply a queued next-account intent before the next
/// prompt: transition it to `applying`, drive the app-server login, and record
/// success (which flips the applied binding and clears the intent) or failure
/// (which marks the intent failed and keeps the prompt fenced). Returns the
/// account now applied to the live runtime, if it changed.
async fn apply_pending_next_account(
    websocket: &mut tokio_tungstenite::WebSocketStream<UnixStream>,
    context: &CliContext,
    record: &SessionRecord,
    request_id: &mut u64,
) -> Option<String> {
    let launch_id = record
        .runtime
        .as_ref()
        .map(|runtime| runtime.launch_id.clone())?;
    // Only drain while the turn is authoritatively idle.
    let idle_context = context.clone();
    let idle_id = record.id.clone();
    let idle_launch = launch_id.clone();
    let idle = tokio::task::spawn_blocking(move || {
        let current = crate::load_session_record(&idle_context, &idle_id).ok()?;
        if current
            .runtime
            .as_ref()
            .is_none_or(|runtime| runtime.launch_id != idle_launch)
        {
            return None;
        }
        crate::activity::state_for_view(&idle_context, &current).map(|state| state.phase)
    })
    .await
    .ok()
    .flatten();
    if idle != Some(crate::activity::TurnPhase::Waiting) {
        return None;
    }

    let begin_context = context.clone();
    let begin_id = record.id.clone();
    let begin_launch = launch_id.clone();
    let queued = tokio::task::spawn_blocking(move || {
        crate::codex_account::begin_next_apply(&begin_context, &begin_id, &begin_launch)
    })
    .await
    .ok()?;
    let (account, revision) = match queued {
        Ok(Some(pair)) => pair,
        Ok(None) => return None,
        Err(_) => return None, // malformed intent stays fenced for explicit repair
    };

    let outcome = drive_external_auth_login(websocket, request_id, &account).await;
    let succeeded = outcome.is_ok();
    let finish_context = context.clone();
    let finish_id = record.id.clone();
    let finish_launch = launch_id.clone();
    let finish_account = account.clone();
    let finished = tokio::task::spawn_blocking(move || {
        crate::codex_account::finish_next_apply(
            &finish_context,
            &finish_id,
            &finish_launch,
            &finish_account,
            revision,
            outcome,
        )
    })
    .await;
    match finished {
        Ok(Ok(_)) if succeeded => Some(account),
        _ => None,
    }
}
```

**d. `run_control` MAIN loop (the second `loop { tokio::select! { … } }`, the one
whose `command = commands.recv()` arm holds the `Usage`/`Prompt`/`Continue`/
`BindAccount` match ~2100-2273; NOT the small `binding_is_present &&
external_auth_account.is_none()` bootstrap loop ~1978).**

- Declare an interval just before that `loop {`:
```rust
    let mut next_apply_interval = tokio::time::interval(Duration::from_secs(1));
    next_apply_interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
```
- Add an `ApplyNext` arm to the `command = commands.recv()` match (after `BindAccount`):
```rust
                    ControlCommand::ApplyNext { response } => {
                        if let Some(applied) = apply_pending_next_account(
                            &mut websocket, &context, &record, &mut request_id,
                        )
                        .await
                        {
                            external_auth_account = Some(applied);
                        }
                        let _ = response.send(Ok(()));
                    }
```
- Add a third `tokio::select!` arm (alongside `command = …` and `message = …`):
```rust
            _ = next_apply_interval.tick() => {
                if let Some(applied) = apply_pending_next_account(
                    &mut websocket, &context, &record, &mut request_id,
                )
                .await
                {
                    external_auth_account = Some(applied);
                }
            }
```
(The interval is the robust idle-drain; input is fenced until it applies, so ≤1s
latency is fine. `apply_pending_next_account` self-gates on Waiting + drainable.)

### 2) `crates/agent-session/src/lib.rs` — resume path (~3998)
After `codex_account::mark_runtime_pending(&mut record)?;` add:
```rust
    codex_account::recover_next_after_restart(&mut record)?;
```
(so an interrupted `applying` intent is re-queued for the fresh runtime; the
`configure_runtime` + `write_session_record` right after persist it).

### 3) OPTIONAL prompt-immediacy trigger (`serve.rs`)
The control-loop interval already drains within ~1s. If you want zero-latency
apply, have the periodic Codex pass (`process_codex_auto_resume_id` /
`process_codex_auto_resume_ids`, ~4604-4692) call `control.handle.apply_next()`
for a target whose record `has_pending_next`. Not required for correctness.

## Tests to add for task 1.2
- **serve route test** (model on `codex_account_switch_serializes_full_id_and_prefix_as_one_transaction`
  ~13615, but ingest ONLY `turn_started` so phase = Working): PUT `/sessions/{id}/account`
  → 200, `body.data.codex_account.next.state == "queued"`,
  `selected_account` unchanged, no `BindAccount` reaches the control plane.
- **app-server drain test** (model on the bind/switch WebSocket test ~7230-7310):
  fake app-server; bind A; `codex_account::queue_next_account(..,"B")`; ingest
  `turn_completed` so phase = Waiting; `handle.apply_next().await`; assert the fake
  server receives the `external_auth_login` for B and the persisted view shows
  `selected_account == "B"`, `next == None`.

## After task 1.2 is green
1. `NILS_CLI_TEST_RUNNER=nextest bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` (from worktree, `<workspace>/.cargo/bin/cargo`).
2. Rehydrate #375 run-state: no `run-state.json` exists — reconstruct the plan
   bundle from the issue #375 comment snapshots (plan/source/execution-state),
   then `plan-issue tracking run init` (bundle + execution-state file). ledger-update
   1.1/1.2/1.3, `tracking checkpoint --live --post state,session,validation`.
3. Deliver via `pr:deliver-pr` / the plan-tracking skill: `forge-cli pr deliver --no-merge`
   with `--test-first-evidence` (this dir), review gate (testing + maintainability +
   security — concurrency/creds surface), merge (watch required checks test/test_macos/coverage).
4. Task 1.3: release + deploy the daemon via `private-release-nils-cli` (honor its
   two-stage consent) + deploy to sympoies runtime; verify existing sessions survive restart.
5. Close #375: user wants Sprint 2 (agent-console UI, tasks 2.1-2.3) handled
   SEPARATELY — descope it from #375 (spin out a fresh follow-up tracker) so
   `tracking close-ready` passes, then `record close` + read-back audit +
   `plan-archive discover`/dry-run migrate.
6. Terminal cleanup per git-delivery policy (worktree remove only after provider
   merge truth confirmed).

## Notes
- `deliver-pr`/`semantic-commit` from a foreign cwd need literal `--repo`; forge-cli
  `pr ready/merge` need cwd = a clean worktree (agent-out/ makes main dirty).
- nils-cli `main` is unprotected but required checks are test/test_macos/coverage —
  watch with `gh pr checks --watch`.
