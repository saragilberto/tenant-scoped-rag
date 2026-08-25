# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - When a tool's contract forbids leaking cross-scope data, assert the exact set of fields each entry returns, not just that the in-scope items are correct - an added aggregate/count field can leak scope existence without any existing assertion catching it.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `server,isolation` · harmful: 0
- features: rag-com-escopo-de-tenant
- evidence: tests/integration/test_server_list_sources.py (mutant M4: src/rag/server.py list_sources) (server,isolation)
- last seen: 2026-08-25T00:45:58Z

### L-002 - When hand-calculating a metric or windowed function in a test, include at least one case where the input is strictly longer than the window (k < len(retrieved)) so an off-by-one at the boundary cannot hide behind a no-op slice.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `metrics,eval` · harmful: 0
- features: rag-com-escopo-de-tenant
- evidence: tests/unit/test_metrics.py (mutant M8: src/eval/metrics.py recall_at_k) (metrics,eval)
- last seen: 2026-08-25T00:45:58Z

### L-003 - When the spec states an exact percentage or ratio for a computed property, assert that exact value directly from the deterministic parameter that produces it, not a loose plausibility band derived from an indirect proxy measurement.
- signal: `spec_precision_gap` · recurrence: 1 feature(s) · scope: `chunking` · harmful: 0
- features: rag-com-escopo-de-tenant
- evidence: RAG-04 (chunking)
- last seen: 2026-08-25T00:45:58Z

### L-004 - An AC about deployment ergonomics (single command, no manual step) still needs a file:line test citation or an explicit spec note scoping it to config-only verification - otherwise it silently reads as covered when it is not.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `server,config` · harmful: 0
- features: rag-com-escopo-de-tenant
- evidence: RAG-23 (server,config)
- last seen: 2026-08-25T00:45:58Z

### L-005 - For a CLI entrypoint's optional flags, add a test that runs main() with a non-default flag value and asserts the downstream call reflects it - a parser test proving the value parses and a domain unit test proving the function dispatches correctly do not together prove the entrypoint wires one to the other.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `cli-orchestration` · harmful: 0
- features: conexao-llm-local
- evidence: LLM-11 (cli-orchestration)
- last seen: 2026-08-25T11:29:42Z

### L-006 - A conditional that only gates a stderr warning (not an exit code or return value) is as easy to leave untested as one that gates a return value - test warning-only branches explicitly in both directions, not just the branches with an observable exit-code or output-presence effect.
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `cli-orchestration` · harmful: 0
- features: conexao-llm-local
- evidence: src/rag/context_cli.py:93 (cli-orchestration)
- last seen: 2026-08-25T11:29:42Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
