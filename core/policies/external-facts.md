# External Facts And Task Tools

## Purpose

This policy covers external, unstable, or time-sensitive claims: how to
handle them, how to cite evidence, and which purpose-built tools to reach for.
It pairs with `core/policies/cli-tools.md` (the cross-project CLI catalog),
which is optional context available on demand. Read it before relying on an
external fact; `AGENT_HOME.md` routes here. There is no finish-line validation
gate for it.

## When To Verify External Facts

- Before asserting any external, unstable, or time-sensitive claim — versions,
  prices, news, API shapes, third-party behavior — prefer authoritative sources
  over memory or assumption, and cite the evidence used.
- Local, stable, repo-internal facts do not need this; cite the file, command,
  or definition instead.

## Source Tags

Use traceable citations when source material materially affects a requirement,
feasibility, work, or external-fact claim:

- `[U#]` user input (record in English, paraphrasing non-English input)
- `[F#]` local files / code / docs
- `[W#]` web source
- `[A#]` app / API / CLI / tool result
- `[I#]` inference from cited facts

Do not present unsupported assumptions as facts. When a conclusion depends on
uncertainty, separate known facts, assumptions, inferences, and open questions.

## Tools

- The cross-project CLI catalog and recommended defaults live in
  `core/policies/cli-tools.md` (search, files, API exploration, structured
  data, and more).
- For captured/redacted web evidence, model cross-checks, and research
  synthesis, prefer the evidence and reporting skills — for example
  `web-evidence`, `model-cross-check`, `deep-research`, and `topic-radar` — over
  ad-hoc pipelines, and keep the citations they produce.
