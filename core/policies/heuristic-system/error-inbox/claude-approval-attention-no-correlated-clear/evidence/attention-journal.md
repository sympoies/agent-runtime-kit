agent-session activity journal excerpt: attention event kinds and timestamps only.
No prompt, answer, command, or transcript text is included; attention ids are truncated.
provider=claude

-- Before the ingress fix. Two client questions each raised an uncorrelated
-- permission_prompt approval that nothing ever cleared. The 15:47 pair shows the
-- duplicate directly: the exact clarification cleared on answer, while the approval
-- raised six seconds later for the same interaction stayed pending.
2026-07-25T15:43:50Z  attention_requested  attention_kind=approval       attention_id=86e514c89c2c...
2026-07-25T15:47:51Z  attention_requested  attention_kind=clarification  attention_id=fe8482f7afcf...
2026-07-25T15:47:57Z  attention_requested  attention_kind=approval       attention_id=6a690f9db836...
2026-07-25T15:48:27Z  attention_cleared    attention_kind=-              attention_id=fe8482f7afcf...

-- After the ingress fix. One exact clarification, cleared on answer, with no
-- duplicate approval for the same interaction.
2026-07-25T16:04:48Z  attention_requested  attention_kind=clarification  attention_id=871580bc64af...
2026-07-25T16:05:05Z  attention_cleared    attention_kind=-              attention_id=871580bc64af...

-- Remaining gap tracked by this entry: a genuine permission approval still has no
-- correlated clear, so it latches until turn completion, a new turn, or a new runtime.
