# RAG com Escopo de Tenant Validation

**Date**: 2026-08-24
**Spec**: `.specs/features/rag-com-escopo-de-tenant/spec.md`
**Diff range**: `398b307..c22578d` (32 tasks, first commit through `docs(readme): publish the isolation design and ablation results`)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

All 32 tasks in `tasks.md` are marked `[x]` for every "Done when" line, across all 6 phases (T1–T32). No task is blocked or partial. Corresponding commits exist for every task's declared commit message, plus a small number of intervening fix commits (`0d31dbe`, `16c7e44`, `83d2eee`, `5703ee3`) that do not correspond to new tasks and do not affect scope.

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1–T7 (Phase 1) | ✅ Done | Repo hygiene, deps, DB compose, both corpora, both golden sets |
| T8–T13 (Phase 2) | ✅ Done | Extensions, tables, roles, RLS policies, indexes, `rag.db` |
| T14–T16 (Phase 3) | ✅ Done | Chunking, embedding, idempotent ingest |
| T17–T21 (Phase 4) | ✅ Done | Semantic, lexical, hybrid (RRF), recall baseline, rerank |
| T22–T27 (Phase 5) | ✅ Done | 4 MCP tools, cross-tenant suite, canary |
| T28–T32 (Phase 6) | ✅ Done | Metrics, harness, ablation, CI, README |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| -------------------------- | --------------------- | ------------------------ | ------ |
| RAG-01 ingest grava doc+chunk completos | tenant_id, origem, versão, texto íntegro; vetor 768-dim + tsvector | `tests/integration/test_ingest.py:47-70` `assert titulo == ...`, `"expires after 30 minutes" in texto_original`; `tests/integration/test_ingest.py:73-95` `assert dimensions == 768` `assert has_fts is True` | ✅ PASS |
| RAG-02 segunda ingest sem alteração | contagens idênticas | `tests/integration/test_ingest.py:105-107` `assert second.documents_written == 0` `assert second.chunks_written == 0` | ✅ PASS |
| RAG-03 doc com título → seções sem overlap | divisão por fronteira, zero overlap | `tests/unit/test_chunking.py:31-42` `assert sum(c.text.count(...)) == 1` (3x) | ✅ PASS |
| RAG-04 doc sem título → tamanho fixo, 15% overlap | overlap exatamente 15% | `tests/unit/test_chunking.py:45-56` `assert 0.05 < ratio < 0.30` | ⚠️ Spec-precision gap — test only bounds overlap in a loose 5–30% band, never asserts the exact 15% the spec states. Implementation (`src/rag/chunking.py:17` `_OVERLAP_RATIO = 0.15`) is exact; the test's tolerance is not |
| RAG-05 arquivo falha → registrado, prossegue, exit≠0 | path+causa registrados, demais processados, código de saída ≠0 | `tests/integration/test_ingest.py:150-156` `assert len(report.failed_files) == 1`; `tests/integration/test_ingest.py:180` `assert result.returncode != 0` | ✅ PASS |
| RAG-06 embedding prefixa `passage: ` | todo texto de chunk prefixado | `tests/unit/test_embedding.py:27-33` `assert stub.encoded_inputs == [["passage: reset...", "passage: import..."]]` | ✅ PASS |
| RAG-07 semantic prefixa `query: `, ordena por cosseno | prefixo exato + ordem ascendente de distância | `tests/unit/test_embedding.py:36-42` `assert stub.encoded_inputs == ["query: how do I reset my password?"]`; `tests/integration/test_semantic_search.py:30-35` `assert scores == sorted(scores)` | ✅ PASS |
| RAG-08 lexical ordena por `ts_rank_cd`, english+unaccent | ordenação por rank; acentuado=não acentuado | `tests/integration/test_lexical_search.py:21-27` `assert scores == sorted(scores, reverse=True)`; `:47-55` `assert str(accented_chunk) in unaccented_ids` and `in accented_ids` | ✅ PASS |
| RAG-09 hybrid funde por RRF k=60, por posição | score = soma de 1/(60+posição) por ranking | `tests/integration/test_hybrid_search.py:83` `assert g_candidate.score == pytest.approx(1/64 + 1/64)`; `:87` `assert a_candidate.score == pytest.approx(1/61)` | ✅ PASS |
| RAG-10 escopo com ≥top_k chunks → exatamente top_k | contagem exata | `tests/integration/test_semantic_search.py:23-27` `assert len(results) == 5`; `tests/integration/test_recall_baseline.py:95-98` margin check vs single-tenant baseline | ✅ PASS |
| RAG-11 top_k fora de 1–50 → erro, sem query no banco | rejeição antes de qualquer SELECT | `tests/integration/test_server.py:57-64` `pytest.raises(ValueError, match="top_k")`; ordering confirmed at `src/rag/server.py:91-96` (`_validate_top_k` runs before `db.scoped_connection` is opened) | ✅ PASS |
| RAG-12 query vazia/espaços → erro | rejeição | `tests/integration/test_server.py:67-69` `pytest.raises(ValueError, match="query")` | ✅ PASS |
| RAG-13 mode restrito a 3 valores | rejeição de qualquer outro valor | `tests/integration/test_server.py:72-74` `pytest.raises(ValueError, match="mode")` | ✅ PASS |
| RAG-14 RLS habilitada em toda tabela do corpus | `pg_class.relrowsecurity = true` em documents e chunks | `tests/integration/test_rls.py:55-66` `assert row[0] is True` (x2) | ✅ PASS |
| RAG-15 SET LOCAL + papel sem BYPASSRLS/dono | tenant setado; role rag_app; sem bypass; sem posse de tabela | `tests/integration/test_db.py:12-17` `assert tenant == "meridian"` `assert role == "rag_app"`; `tests/integration/test_roles.py:4-17` `assert row == (False, False)` | ✅ PASS |
| RAG-16 nenhuma tool expõe parâmetro de escopo | zero tool com `tenant`/`scope`/etc | `tests/integration/test_server.py:100-105` `assert not leaked`; `tests/isolation/test_cross_tenant.py:86-94` idem, varrendo as 4 tools exatas | ✅ PASS |
| RAG-17 env ausente/vazia/desconhecida → encerra sem anunciar tool | `SystemExit` antes de `mcp.run` | `tests/integration/test_db.py:20-38` `pytest.raises(SystemExit)` (x3 casos); `tests/integration/test_server.py:108-118` `_fail_if_called` nunca é atingido | ✅ PASS |
| RAG-18 30 perguntas sob identidade oposta → zero chunk de origem | zero leak em 3 modos x 2 direções (180 execuções) | `tests/isolation/test_cross_tenant.py:52-72` `assert not leaked` | ✅ PASS |
| RAG-19 RLS removida em ambiente dedicado → suíte falha | canário fica vermelho | `tests/isolation/test_canary.py:94-105` `pytest.raises(AssertionError, match="expected only")` após `DISABLE ROW LEVEL SECURITY` | ✅ PASS |
| RAG-20 instrução maliciosa na query → tratada como texto | escopo ativo inalterado | `tests/isolation/test_cross_tenant.py:75-83` `assert server._active_tenant == "meridian"` | ✅ PASS |
| RAG-21 handshake anuncia 4 tools com esquemas | tools presentes com `input_schema` | `tests/integration/test_server.py:48-54` `assert "search" in names`; `assert tool.input_schema.get("properties") is not None` | ✅ PASS |
| RAG-22 banco inacessível → erro específico, servidor vivo | mensagem "unreachable"; próxima chamada funciona | `tests/integration/test_server.py:130-135` `pytest.raises(ToolError, match="unreachable")`; `:140-142` chamada seguinte funciona e handshake segue vivo | ✅ PASS |
| RAG-23 iniciável com um comando, sem etapa manual extra | comando único declarado | **nenhuma citação `file:line`** — satisfeito apenas por config (`pyproject.toml:14-16` entry point `rag-server`) e por documentação (`README.md:155,160`); nenhum teste invoca o entry point real ou afirma "sem etapa manual" | ❌ GAP — not covered |
| RAG-24 get_document no escopo → texto+metadados completos | campos presentes e não vazios | `tests/integration/test_server_get_document.py:21-30` `assert result["texto"]` etc. | ✅ PASS |
| RAG-25 doc_id inexistente/outro tenant → indistinguível | resposta byte-idêntica | `tests/integration/test_server_get_document.py:43-47` `assert nonexistent == cross_tenant` | ✅ PASS |
| RAG-26 list_sources lista só escopo ativo + contagem | ids batem com escopo; contagem exata; exclui outro tenant | `tests/integration/test_server_list_sources.py:16-29` `assert {entry["doc_id"]...} == admin_ids`; `:32-40` `assert result_ids.isdisjoint(halcyon_ids)` | ✅ PASS — porém ver Sensor: mutante sobrevivente (M4) mostra que a suíte não veta um campo agregado adicional vazando contagem cross-tenant |
| RAG-27 explain_retrieval retorna score/posição/score fundido/motivo | 4 campos presentes por candidato | `tests/integration/test_server_explain_retrieval.py:20-25` `assert candidate["fused_position"] == i`, `assert candidate["cutoff_reason"]` | ✅ PASS |
| RAG-28 omite indício de candidato fora de escopo | sem contagem/id/campo revelador | `tests/integration/test_server_explain_retrieval.py:52-54` `assert "out_of_scope_count" not in candidate`; `:57-70` diff sets disjoint entre tenants | ✅ PASS |
| RAG-29 métricas determinísticas sem chamada externa | recall/precision/MRR/nDCG conferem contra cálculo manual; zero rede | `tests/unit/test_metrics.py:12-33` valores calculados à mão; `:60-71` `monkeypatch.setattr(socket, "socket", _forbidden)` | ✅ PASS — porém ver Sensor: mutante sobrevivente (M8) no off-by-one de `recall_at_k` |
| RAG-30 ablação mede 12 combinações, tabela markdown | 3 modos x 2 rerank x 2 perfis = 12 linhas | `tests/integration/test_ablation.py:49-55` `assert len(data_rows) == 12`; `assert seen == _ALL_COMBINATIONS` | ✅ PASS |
| RAG-31 golden set versionado, texto legível | arquivo YAML editável à mão | `eval/golden/meridian.yaml`, `eval/golden/halcyon.yaml`; `tests/unit/test_golden_set_integrity.py:38-46` valida contagem e referências | ✅ PASS |
| RAG-32 flag ativa → reordena antes do corte | ordem final = ordem do cross-encoder | `tests/integration/test_rerank.py:57` `assert [c.chunk_id for c in reordered] == ["best", "middle", "worst"]` | ✅ PASS |
| RAG-33 reranking desligado por padrão | `is_enabled() is False` sem env var | `tests/integration/test_rerank.py:22-25` `assert rerank.is_enabled() is False` | ✅ PASS |
| RAG-34 flag ativa + modelo ausente → falha explícita | `RuntimeError` citando o modelo | `tests/integration/test_rerank.py:69` `pytest.raises(RuntimeError, match="bge-reranker-v2-m3")` | ✅ PASS |

**Status**: ❌ Gaps present — 32/34 ACs matched the spec-defined outcome exactly, 1 spec-precision gap (RAG-04), 1 AC with zero test evidence (RAG-23). Two of the "PASS" ACs (RAG-26, RAG-29) carry a surviving-mutant caveat from the discrimination sensor (see below) — the literal AC text is satisfied, but the test suite does not discriminate against a real regression class in that code.

---

## Discrimination Sensor

Baseline `git status --porcelain` captured before any sensor work: `?? .specs/features/conexao-llm-local/` (pre-existing untracked directory from another feature, unrelated to this one). Confirmed identical after cleanup (see below).

Scratch mechanics: a `git worktree add <scratch> HEAD` for all Python-source mutations (M2, M3, M4, M5, M6, M7, M8), synced with its own `uv sync`. For the SQL/RLS mutation (M1), a throwaway Postgres database (`rag_sensor_m1`, same server, migrated fresh, dropped afterward) — the same technique the project's own canary test (`tests/isolation/test_canary.py`) uses, since an RLS policy change cannot be expressed as a file-only mutation without applying it to a live database. The real `rag` database and the real working tree were never touched.

| # | File:line | Description | Killed? |
| - | --------- | ------------ | ------- |
| M1 | `migrations/004_rls.sql:12-13,20-21` | Inverted RLS `SELECT` predicate `tenant_id = current_setting(...)` → `tenant_id != current_setting(...)` on `documents` and `chunks`, applied to a disposable scratch database | ✅ Killed — `tests/integration/test_rls.py::test_rag_app_scoped_select_excludes_other_tenant` fails: meridian scope now returns halcyon's chunk instead of its own |
| M2 | `src/rag/db.py:37` | Removed the `SET LOCAL app.tenant_id` call inside `scoped_connection` | ✅ Killed — `tests/integration/test_db.py::test_scoped_connection_applies_tenant_scope_and_uses_rag_app_role` fails with `psycopg.errors.UndefinedObject: unrecognized configuration parameter "app.tenant_id"` |
| M3 | `src/rag/server.py:124-125` (`get_document`) | Added an unscoped admin-connection existence check so a cross-tenant `doc_id` returns `{"found": False, "reason": "belongs_to_another_tenant"}` instead of the plain not-found response | ✅ Killed — `tests/integration/test_server_get_document.py::test_cross_tenant_doc_id_is_not_found` and `::test_nonexistent_and_cross_tenant_responses_are_byte_identical` both fail |
| M4 | `src/rag/server.py:150` (`list_sources`) | Added a `total_all_tenants` field to every entry, populated via an unscoped admin connection counting `documents` across all tenants | ❌ **Survived** — `tests/integration/test_server_list_sources.py` (all 3 tests) still pass. The suite checks doc-id set membership and per-doc chunk counts, but never asserts the *absence* of extra/aggregate fields the way `test_server_explain_retrieval.py:52-54` does for `explain_retrieval`. → fix task created |
| M5 | `src/rag/server.py:73` (`_validate_mode`) | Inverted the validation condition (`if mode in _SEARCH_MODULES: raise ...`) | ✅ Killed — `tests/integration/test_server.py::test_rejects_invalid_mode` and `::test_db_unavailable_returns_error_and_server_stays_alive` fail |
| M6 | `src/rag/chunking.py:45` (`has_structure`) | Inverted the heading-detection condition (`is None` instead of `is not None`) | ✅ Killed — all 6 tests in `tests/unit/test_chunking.py` fail (`IndexError` on the now-empty heading list) |
| M7 | `src/rag/embedding.py:39` (`embed_query`) | Removed the `query: ` prefix | ✅ Killed — `tests/unit/test_embedding.py::test_embed_query_prefixes_text_with_query` fails |
| M8 | `src/eval/metrics.py:21` (`recall_at_k`) | Off-by-one: `retrieved[:k]` → `retrieved[:k+1]` | ❌ **Survived** — `tests/unit/test_metrics.py` all 10 tests still pass. Every hand-calculated case uses `k == len(retrieved)` (e.g. `retrieved=["a","b","c"]`, `k=3`), so slicing one element past `k` is a no-op and the mutation is invisible. → fix task created |

Real worktree `git status --porcelain` re-checked after `git worktree remove --force` and scratch-database drop: identical to the pre-sensor baseline (`?? .specs/features/conexao-llm-local/` only). Sensor run is valid.

**Sensor depth**: P0/critical-path tier — 5 mutations targeting the isolation core (RLS policy, `scoped_connection`, `get_document`, `list_sources`, `search` validation) as required, plus 3 lightweight mutations for chunking/embedding/metrics.
**Result (iteration 1)**: 6/8 killed, 2 survived — ❌ did not discriminate (superseded by iteration 2 below, both survivors now killed)

---

## Interactive UAT Results

Not performed. This is a backend-only, MCP-server feature (no UI); per `validate.md` §3, automated checks are sufficient and interactive UAT is reserved for user-facing features.

---

## Code Quality

Spot-checked across 4 tasks spanning 3 different phases: T13 (`src/rag/db.py`, Phase 2), T16 (`src/rag/ingest.py`, Phase 3), T19 (`src/rag/retrieval/hybrid.py`, Phase 4), T30 (`src/eval/ablation.py`, Phase 6).

| Principle | Status |
| --------- | ------ |
| No features beyond what was asked | ✅ Each module does exactly its task's stated job; no speculative flags, no unused config surface |
| No abstractions for single-use code | ✅ `db.py` deliberately exports only 2 functions and has a test enforcing it (`test_module_exports_no_other_connection_constructor`) |
| No unnecessary "flexibility" added | ✅ `hybrid.py`, `ablation.py` hardcode the spec's fixed constants (`_RRF_K = 60`, the 12-cell matrix) rather than generalizing |
| Only touched files required for task | ✅ Each commit's diff matches its task's `Where:` field |
| Didn't "improve" unrelated code | ✅ No drive-by refactors observed outside task scope |
| Matches existing patterns/style | ✅ Consistent module docstring convention explaining "why", consistent `__all__` exports, consistent error-handling shape (`RuntimeError`/`ValueError`/`ToolError`) across modules |
| Would senior engineer approve? | ✅ |
| Tests map to acceptance criteria and are non-shallow (spot-check one story) | ✅ P1 "Isolamento garantido pelo banco" story spot-checked: `test_rls.py`, `test_db.py`, `test_cross_tenant.py`, `test_canary.py` all assert precise outcomes (role names, GUC values, exact leak sets), not just "no exception" |
| Spec-anchored outcome check (asserted values match spec) | ⚠️ 32/34 exact; see RAG-04 spec-precision gap and RAG-23 gap above |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ Matches the Test Coverage Matrix in `tasks.md`: unit tests for domain logic, integration tests for DB/RLS/tools, isolation tests for cross-tenant, integrity tests for corpus/golden set |
| Every test maps to a spec requirement — no unclaimed tests | ✅ Every test file's docstring cites the RAG-IDs it covers, and inspection confirms the tests match those IDs |
| Documented guidelines followed | none - strong defaults applied (Test Coverage Matrix itself states "Diretrizes encontradas: nenhuma") |

---

## Edge Cases

- [x] Consulta sem correspondência → lista vazia, nunca erro nem chunk menos ruim: `tests/integration/test_semantic_search.py:38-45`
- [x] Corpus de um tenant vazio → lista vazia sem revelar outro tenant: `tests/integration/test_server_list_sources.py:43-54`
- [x] Consulta > 2000 caracteres → erro de validação antes do embedding: `tests/integration/test_server.py:77-79`
- [x] Documento sem título maior que um chunk → múltiplos chunks contíguos sem perder texto: `tests/unit/test_chunking.py:59-69`
- [x] Modelo de embedding indisponível → falha explícita: `tests/unit/test_embedding.py:58-65`; rerank equivalente em `tests/integration/test_rerank.py:61-70`

---

## Gate Check

- **Gate command**: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- **Result**: 125 passed, 0 failed, 0 skipped. `ruff check` and `ruff format --check` both clean.
- **Test count before feature**: 0 (greenfield repository)
- **Test count after feature**: 125
- **Delta**: +125 new tests
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

### Fix 1: `list_sources` has no negative assertion against leaking extra/aggregate fields

- **Root cause**: `tests/integration/test_server_list_sources.py` only asserts doc-id set membership and per-doc chunk counts. Unlike `test_server_explain_retrieval.py` (which explicitly asserts `"out_of_scope_count" not in candidate` and `"total_candidates" not in candidate`), no test in this file asserts the shape of each entry is exactly `{doc_id, titulo, chunk_count}` with nothing else — so a future change that adds a cross-tenant aggregate (e.g. a "helpful" `total_all_tenants` count) would ship silently.
- **Fix task**: Add `assert set(entry) == {"doc_id", "titulo", "chunk_count"}` (or equivalent) to `test_list_sources_returns_only_active_tenant_documents_with_correct_chunk_counts` in `tests/integration/test_server_list_sources.py`.
- **Priority**: Major (isolation-adjacent test gap, though the current implementation has no leak — this is a discrimination-sensor finding, not a live vulnerability)

### Fix 2: `recall_at_k`'s k-window boundary is untested

- **Root cause**: Every hand-calculated case in `tests/unit/test_metrics.py` uses `k == len(retrieved)` (e.g. 3 retrieved items, `k=3`), so an off-by-one in the slice bound (`retrieved[:k]` vs `retrieved[:k+1]`) is invisible to the test suite.
- **Fix task**: Add a case to `tests/unit/test_metrics.py` with `len(retrieved) > k` and a relevant document sitting exactly at index `k` (just past the cutoff), asserting it is *not* counted.
- **Priority**: Minor (metrics are internal to the ablation study; wrong recall numbers would eventually surface in the published README table, but the current implementation is correct — only the test's discriminating power is weak)

### Fix 3: RAG-23 has no test evidence

- **Root cause**: "Iniciável com um único comando... sem etapa manual além de subir o banco e executar a ingestão" is satisfied only by `pyproject.toml`'s `rag-server` entry point and by README documentation — no test invokes the entry point or asserts the absence of additional manual steps.
- **Fix task**: Either (a) add a subprocess-level smoke test that runs `uv run rag-server` against a running DB with `RAG_TENANT_ID` set and confirms it starts and answers the MCP handshake (mirroring the CI workflow's own manual verification), or (b) explicitly document in `tasks.md`/`spec.md` that RAG-23 is intentionally verified by config + manual UAT rather than automated test (matching how the Test Coverage Matrix already scopes "Configuração" as `Tests: none`), so the gap is a documented decision rather than a silent one.
- **Priority**: Minor (this is a "clone and run" ergonomics claim already made credible by the CI workflow's own use of the entry point paths and by the README's copy-pasted client config; the gap is in verification-of-record, not in the underlying behavior)

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| ----------- | ---------------- | ----------- |
| RAG-01 | In Tasks | ✅ Verified |
| RAG-02 | In Tasks | ✅ Verified |
| RAG-03 | In Tasks | ✅ Verified |
| RAG-04 | In Tasks | ⚠️ Verified (spec-precision gap) |
| RAG-05 | In Tasks | ✅ Verified |
| RAG-06 | In Tasks | ✅ Verified |
| RAG-07 | In Tasks | ✅ Verified |
| RAG-08 | In Tasks | ✅ Verified |
| RAG-09 | In Tasks | ✅ Verified |
| RAG-10 | In Tasks | ✅ Verified |
| RAG-11 | In Tasks | ✅ Verified |
| RAG-12 | In Tasks | ✅ Verified |
| RAG-13 | In Tasks | ✅ Verified |
| RAG-14 | In Tasks | ✅ Verified |
| RAG-15 | In Tasks | ✅ Verified |
| RAG-16 | In Tasks | ✅ Verified |
| RAG-17 | In Tasks | ✅ Verified |
| RAG-18 | In Tasks | ✅ Verified |
| RAG-19 | In Tasks | ✅ Verified |
| RAG-20 | In Tasks | ✅ Verified |
| RAG-21 | In Tasks | ✅ Verified |
| RAG-22 | In Tasks | ✅ Verified |
| RAG-23 | In Tasks | ✅ Verified (was ❌ Needs Fix in iteration 1; closed in iteration 2 — see below) |
| RAG-24 | In Tasks | ✅ Verified |
| RAG-25 | In Tasks | ✅ Verified |
| RAG-26 | In Tasks | ✅ Verified (was ⚠️ surviving mutant M4 in iteration 1; killed in iteration 2 — see below) |
| RAG-27 | In Tasks | ✅ Verified |
| RAG-28 | In Tasks | ✅ Verified |
| RAG-29 | In Tasks | ✅ Verified (was ⚠️ surviving mutant M8 in iteration 1; killed in iteration 2 — see below) |
| RAG-30 | In Tasks | ✅ Verified |
| RAG-31 | In Tasks | ✅ Verified |
| RAG-32 | Done (T21) | ✅ Verified |
| RAG-33 | Done (T21) | ✅ Verified |
| RAG-34 | Done (T21) | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 32/34 ACs matched spec outcome, 1 spec-precision gap flagged (RAG-04), 1 AC not covered (RAG-23)
**Sensor**: 6/8 mutations killed
**Gate**: 125 passed, 0 failed

**What works**: The tenant-isolation core is genuinely solid — RLS enforcement, `scoped_connection`, `get_document`'s indistinguishable not-found, and `search`'s validation ordering all killed their targeted mutations immediately and with precise failure messages. The 180-query cross-tenant suite and the RLS-removal canary are exactly the kind of proof-by-test the spec's Problem Statement demands, and they hold up under fault injection. Chunking, embedding, and the retrieval math (exact RRF score computation) are all tested to the precision the spec asks for.

**Issues found**:
1. `list_sources` lacks a negative assertion against extra/leaking fields (surviving mutant M4) — add a shape assertion, see Fix 1.
2. `recall_at_k`'s off-by-one at the k boundary is untested (surviving mutant M8) — add a k < len(retrieved) case, see Fix 2.
3. RAG-23 ("single command, no manual step") has zero test evidence — add a smoke test or explicitly document it as a config-verified requirement, see Fix 3.

**Next steps**: Route the 3 fix items above to an implementer, then re-dispatch the Verifier (fix→re-verify loop, max 3 iterations per `validate.md`).

---

## Re-verification (iteration 2)

**Date**: 2026-08-25
**Diff range since iteration 1**: `c22578d..8fc8454` (`4537232` docs(spec) recording the iteration-1 findings, `8fc8454` test: close verifier gaps)
**Verifier**: independent sub-agent (fresh dispatch, author ≠ verifier)
**Scope**: the 3 gaps ranked in iteration 1 (M4 surviving mutant, M8 surviving mutant, RAG-23 no evidence), plus a full-gate regression sanity check. The other 6 mutations (M1–M3, M5–M7) and the 32 clean ACs from iteration 1 were not re-audited, per orchestrator instruction — nothing in that territory was touched by the fix commit.

### Gap 1 — `list_sources` extra-field leak (mutant M4)

- **Fix applied**: `tests/integration/test_server_list_sources.py:26` — `assert set(entry) == {"doc_id", "titulo", "chunk_count"}`, added inside `test_list_sources_returns_only_active_tenant_documents_with_correct_chunk_counts`.
- **Read and confirmed**: the assertion runs once per returned entry, immediately after the doc-id-set membership check, and pins the exact key set — the same pattern already used for `explain_retrieval` (`test_server_explain_retrieval.py:52-54`). It genuinely tests what it claims: any additional key on the dict (aggregate, count, or otherwise) fails the test.
- **Mutation re-run**: recreated the *exact* M4 mutation from iteration 1 (`src/rag/server.py` `list_sources` — added a `total_all_tenants` field populated via an unscoped `postgres` admin connection counting `documents` across all tenants, bypassing RLS) in a scratch git worktree (`git worktree add`, never `git stash`). Ran `uv run pytest tests/integration/test_server_list_sources.py -q` against the scratch: **1 failed, 2 passed** — `test_list_sources_returns_only_active_tenant_documents_with_correct_chunk_counts` fails with `AssertionError: assert {'chunk_count', 'doc_id', 'titulo', 'total_all_tenants'} == {'chunk_count', 'doc_id', 'titulo'}`.
- **Result**: ✅ Mutant M4 now **killed**.

### Gap 2 — `recall_at_k` off-by-one at the k cutoff (mutant M8)

- **Fix applied**: `tests/unit/test_metrics.py:36-39` — new test `test_recall_at_k_excludes_relevant_doc_just_past_the_cutoff`, with `retrieved = ["a", "b", "c", "d"]`, `relevant = ["d"]`, `k = 3`, asserting `recall_at_k(...) == 0.0`.
- **Read and confirmed**: `"d"` sits at index 3, i.e. exactly one position past the `k=3` cutoff (`retrieved[:3]` excludes it). This is precisely the boundary the iteration-1 report identified as untested — every prior hand-calculated case used `k == len(retrieved)`, making an off-by-one invisible. The new case has `len(retrieved) > k` with the relevant doc sitting exactly at the boundary index, as prescribed by Fix 2.
- **Mutation re-run**: recreated the *exact* M8 mutation from iteration 1 (`src/eval/metrics.py:21` — `retrieved[:k]` → `retrieved[: k + 1]`) in the same scratch worktree. Ran `uv run pytest tests/unit/test_metrics.py -q` against the scratch: **1 failed, 10 passed** — the new test fails with `AssertionError: assert 1.0 == 0.0` (mutant now includes index 3, counting `"d"` as recalled).
- **Result**: ✅ Mutant M8 now **killed**.

### Gap 3 — RAG-23 no test evidence

- **Fix applied**: `tests/integration/test_server_smoke.py` (new file), `test_rag_server_entry_point_starts_and_announces_tools_with_no_manual_step`.
- **Read and confirmed real-subprocess invocation** (not a direct call to `main()`): the test builds `StdioServerParameters(command="uv", args=["run", "--directory", str(REPO_ROOT), "rag-server"], env={"RAG_TENANT_ID": "meridian"})` and drives it through `mcp.client.stdio.stdio_client`, which spawns `uv` as a real OS subprocess, then completes a genuine MCP `ClientSession.initialize()` handshake and `list_tools()` round-trip over that subprocess's stdio pipes (`tests/integration/test_server_smoke.py:14-27`). The `command="uv", args=["run", ...]` shape is a real external-process invocation of the declared `rag-server` script entry point (`pyproject.toml` `[project.scripts]`), not an in-process function call — there is no import of `rag.server.main` anywhere in this file.
- **Assertion targets the spec-defined outcome**: `assert names == {"search", "get_document", "list_sources", "explain_retrieval"}` (`test_server_smoke.py:32`) confirms all 4 tools are announced after a real cold start, which is the concrete, checkable half of RAG-23's "iniciável com um único comando, sem etapa manual extra" (the single command is `uv run rag-server`, exactly what's documented in `README.md` and declared in `pyproject.toml`).
- **Executed independently**: `uv run pytest tests/integration/test_server_smoke.py -v` → **1 passed** (see Gate Check below for the full-suite context; the smoke test spawns a real process against the already-running Postgres and completes in the normal test run, no special setup needed).
- **Result**: ✅ RAG-23 now has direct, real-subprocess test evidence.

### Sensor re-tally

| # | Description | Iteration 1 | Iteration 2 |
| - | ------------ | ------------ | ------------ |
| M1–M3, M5–M7 | (unchanged; not re-run this iteration) | ✅ Killed | not re-run (out of scope, untouched by fix) |
| M4 | `list_sources` unscoped aggregate leak | ❌ Survived | ✅ **Killed** (re-run in scratch worktree, see Gap 1) |
| M8 | `recall_at_k` off-by-one | ❌ Survived | ✅ **Killed** (re-run in scratch worktree, see Gap 2) |

**Sensor mechanics**: `git worktree add <scratch> HEAD` at commit `8fc8454`, `uv sync` inside it. Baseline `git status --porcelain` on the real tree before sensor work: `M .specs/STATE.md` (unrelated feature, another session) + `?? .specs/features/conexao-llm-local/` (unrelated feature, untracked). Both mutations were injected and reverted/discarded entirely inside the scratch worktree; the scratch was removed with `git worktree remove --force` afterward. Real tree `git status --porcelain` re-checked after cleanup: identical to the pre-sensor baseline (`M .specs/STATE.md`, `?? .specs/features/conexao-llm-local/`) — no `git stash` was used at any point, and the real tree was never mutated. Sensor run is valid.

**Full sensor tally (cumulative)**: 8/8 mutations killed (6 from iteration 1 unchanged + 2 re-killed this iteration).
**Result**: 8/8 killed - ✅ PASS

### Gate Check (iteration 2)

- **Gate command**: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`
- **Result**: `ruff check` — all checks passed. `ruff format --check` — 99 files already formatted. `pytest -q` — **127 passed, 0 failed, 0 skipped** in 54.92s.
- **Test count reconciliation**: 125 (iteration 1) → 127 (iteration 2). Delta of +2 matches exactly: +1 new case in `tests/unit/test_metrics.py` (`test_recall_at_k_excludes_relevant_doc_just_past_the_cutoff`) + 1 new file `tests/integration/test_server_smoke.py` with 1 test. No test was removed, skipped, or weakened. `tests/integration/test_server_list_sources.py` gained an assertion inside an existing test, not a new test function, so it contributes 0 to the count delta — consistent with the file's `git show --stat` (`+1` line only).
- **Failures**: none. **Skipped**: none.

### Requirement Traceability (iteration 2 update)

| Requirement | Iteration 1 Status | Iteration 2 Status |
| ----------- | ------------------- | -------------------- |
| RAG-23 | ❌ Needs Fix | ✅ Verified — real-subprocess smoke test, `tests/integration/test_server_smoke.py:30-32` |
| RAG-26 | ⚠️ Verified (surviving mutant M4) | ✅ Verified — mutant M4 killed, `tests/integration/test_server_list_sources.py:26` |
| RAG-29 | ⚠️ Verified (surviving mutant M8) | ✅ Verified — mutant M8 killed, `tests/unit/test_metrics.py:36-39` |

`spec.md`'s Requirement Traceability table updated to match (RAG-23, RAG-26, RAG-29 rows now read `✅ Verified`, no caveat).

RAG-04's ⚠️ Spec-precision gap (loose 5–30% overlap bound instead of the spec's exact 15%) is unchanged and out of scope for this iteration — it was never one of the 3 ranked gaps routed to the fix→re-verify cycle, and the fix commit did not touch `tests/unit/test_chunking.py`. It remains flagged as a caveat, not a blocking gap: the spec-anchored check rule for this class is "flag it, don't silently pass it" — not "fail the whole feature over it" — and it does not represent a discriminating-power failure (the implementation constant is exact; only the test's tolerance band is loose).

### Code Quality (fix-commit spot-check)

| Principle | Status |
| --------- | ------ |
| No features beyond what was asked | ✅ Each fix is exactly the assertion/test prescribed by iteration 1's Fix 1/Fix 2/Fix 3 — no extra behavior added |
| Only touched files required for task | ✅ `8fc8454` touches exactly the 3 files named in the fix plan; `4537232` touches only spec/validation/lessons docs |
| Read-only over implementation | ✅ Confirmed no change to any `src/` file in either commit (`git show --stat` above lists test files and docs only) |
| Matches existing patterns/style | ✅ The `list_sources` fix mirrors the exact pattern already used in `test_server_explain_retrieval.py`; the smoke test follows the existing `asyncio.run(go())` + `assert names == {...}` shape used elsewhere in the integration suite |
| Tests target the spec-defined outcome, not just "an assertion exists" | ✅ All 3 fixes assert the precise value/shape the spec and iteration-1 fix plan called for |

### Summary (iteration 2)

**Overall**: ✅ Ready

**Spec-anchored check**: 33/34 ACs matched spec outcome exactly; 1 spec-precision gap remains flagged (RAG-04, unchanged, out of scope this iteration); 0 ACs uncovered.
**Sensor**: 8/8 mutations killed (2 re-verified this iteration: M4, M8).
**Gate**: 127 passed, 0 failed, 0 skipped.

**What works**: All 3 gaps ranked in iteration 1 are closed with genuine, independently-reproduced evidence — both previously-surviving mutants (M4, M8) now die against the updated tests when the identical fault is re-injected in a scratch worktree, and RAG-23 now has a real-subprocess MCP handshake test rather than zero evidence. No regression: the full gate is green and the test-count delta (+2) reconciles exactly against the 2 new test cases added.

**Issues found**: none blocking. RAG-04's spec-precision gap (loose overlap-ratio bound) remains as a pre-existing, non-blocking caveat, unchanged from iteration 1 and outside this iteration's scope.

**Next steps**: None required for this feature. If RAG-04's spec-precision gap is ever prioritized, tighten `tests/unit/test_chunking.py`'s overlap-ratio assertion to the spec's exact 15% (`abs(ratio - 0.15) < tolerance`) instead of the current 5–30% band.
