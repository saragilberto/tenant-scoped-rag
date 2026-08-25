# Conexão com LLM Local Validation

**Date**: 2026-08-25
**Spec**: `.specs/features/conexao-llm-local/spec.md`
**Diff range**: `98538b7..HEAD` (9 commits: f796224, f86fef7, 5494d6c, fee782c, a2ae4fb, ec59442, 11cdc46, 4ab9d3b, 49bac2a)
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Verifier Iterations

| Round | Outcome | Gaps |
| ----- | ------- | ---- |
| 1 (`4ab9d3b`) | ❌ FAIL | 6/16 ACs (LLM-11..LLM-16) had domain-level coverage only, zero `context_cli.main()` orchestration evidence; 1 surviving mutant on the context-window-exceeds warning (`context_cli.py:93`) |
| 2 (`49bac2a`, this report) | ✅ PASS | 0 - commit `49bac2a` added 7 CLI-level integration tests closing all 6 AC gaps and the surviving mutant; all three round-1 mutations re-run and killed |

`49bac2a` is test-only (`git diff 4ab9d3b..HEAD --stat`: `tests/integration/test_context_cli.py | 130 ++++++++++++`, 1 file changed). No production code changed since round 1.

---

## Task Completion

| Task | Status  | Notes |
| ---- | ------- | ----- |
| T1-T7 | ✅ Done | Unchanged since round 1 - see prior report content, re-confirmed by full gate pass below |

All 34 `Done when` checkboxes across the 7 tasks show `[x]`.

---

## Spec-Anchored Acceptance Criteria

### P1: Contexto pronto para o chat do LLM local

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | --------------------- | ------------------------ | ------ |
| LLM-01 | top_k=5, mode=hybrid, profile=P512, `scoped_connection` | `tests/integration/test_context_cli.py:45` `test_happy_path_prints_block_and_copies_to_clipboard` (real Postgres, default flags) | ✅ PASS |
| LLM-02 | bloco com pergunta + citação por `document_id`+posição + instrução | `src/rag/context_block.py:19-21` - `tests/unit/test_context_block.py:14-51` | ✅ PASS |
| LLM-03 | mesmo conteúdo em clipboard e stdout | `tests/integration/test_context_cli.py:62-63` (compara stdout com `pbpaste`) | ✅ PASS |
| LLM-04 | tentativa de checagem de saúde, timeout 2.0 | `src/rag/context_cli.py:70`; default em `src/rag/local_llm.py:36` - attempt exercised by every integration test (mocked); literal `2.0` not independently asserted (unchanged low-risk caveat from round 1) | ✅ PASS |
| LLM-05 | aviso citando `base_url` + "start llamafile"; bloco entregue | `tests/integration/test_context_cli.py:99-116` `test_local_llm_unreachable_warns_but_still_delivers_block` | ✅ PASS |
| LLM-06 | falha com mensagem de `resolve_tenant_from_env()`, sem health check nem recuperação | `tests/integration/test_context_cli.py:67-78` (mocks raise `AssertionError` if called) | ✅ PASS |
| LLM-07 | rejeita citando `MAX_QUERY_CHARS`, sem tocar banco | `src/rag/query.py:34-39` - `tests/unit/test_query.py:8-23`; CLI: `tests/integration/test_context_cli.py:81-96` | ✅ PASS |
| LLM-08 | stdout vazio, aviso stderr | `tests/integration/test_context_cli.py:119-129` | ✅ PASS |
| LLM-09 | mensagem "unreachable" via `psycopg.OperationalError` | `tests/integration/test_context_cli.py:132-142` (`match="unreachable"`) | ✅ PASS |
| LLM-10 | comando conclui, nota stderr, stdout ok | `tests/integration/test_context_cli.py:145-160` | ✅ PASS |

### P2: Escolher modo, top_k e perfil de chunk

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | --------------------- | ------------------------ | ------ |
| LLM-11 | `--mode` explícito → `run_search` recebe esse modo | `tests/integration/test_context_cli.py:163-176` `test_explicit_mode_top_k_and_profile_reach_run_search` - runs `context_cli.main()` with `--mode lexical`, captures `run_search`'s args via a fake, asserts `calls == [("lexical", 3, ChunkProfile.P1024)]` | ✅ PASS - gap closed |
| LLM-12 | `--top-k N` → `run_search` recebe `top_k=N` | same test, `top_k=3` reaches `run_search` in the tuple above | ✅ PASS - gap closed (verifies plumbing to `run_search`; N-chunks-returned behavior itself is domain-level, covered in `test_query.py`) |
| LLM-13 | `--top-k` fora de 1-50 → mesma mensagem de `query.validate_top_k` | `tests/integration/test_context_cli.py:272-278` `test_rejects_top_k_outside_range_before_touching_database` - `top_k=51`, `pytest.raises(SystemExit, match="top_k")`, `db.scoped_connection` set to fail-if-called. Message from `src/rag/query.py:44` (`"top_k must be between 1 and 50"`) matches | ✅ PASS - gap closed |
| LLM-14 | `--profile P1024` → usado na recuperação | same test as LLM-11/12, `calls == [(..., ChunkProfile.P1024)]` | ✅ PASS - gap closed |

### P3: Abrir o chat do llamafile automaticamente

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --------- | --------------------- | ------------------------ | ------ |
| LLM-15 | `open_browser(base_url)` chamado após `copy_to_clipboard` | `tests/integration/test_context_cli.py:179-204` `test_open_flag_opens_browser_after_copying_to_clipboard` - order list asserts `["copy", "open"]`, `opened == ["http://127.0.0.1:8080"]` | ✅ PASS - gap closed |
| LLM-16 | falha ao abrir → aviso, continua sem abortar | `tests/integration/test_context_cli.py:207-224` `test_open_flag_warns_but_continues_when_browser_fails` - `open_browser` returns `False`, asserts no `SystemExit`, stdout has the block, stderr has "could not open the browser" | ✅ PASS - gap closed |

**Status**: ✅ All 16/16 ACs covered end-to-end with orchestration-layer (`context_cli.main()`) evidence.

---

## Discrimination Sensor

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ------------ | ------- |
| 1 | `src/rag/context_cli.py:85` | Flipped `if not candidates:` → `if candidates:` (zero-chunks guard) | ✅ Killed (7 tests failed - more than round 1's 4, since new tests also exercise this path) |
| 2 | `src/rag/context_cli.py:93` | Flipped `estimated > status.context_window` → `estimated < status.context_window` | ✅ Killed this round (`test_warns_when_block_exceeds_local_llm_context_window` and `test_no_warning_when_block_fits_local_llm_context_window` both fail) - **round 1's surviving mutant is now fixed** |
| 3 | `src/rag/local_llm.py:31` | Flipped `scheme not in ("http", "https")` → `scheme in ("http", "https")` | ✅ Killed (14 tests failed, incl. the new `test_rejects_invalid_local_llm_base_url_before_health_check`) |

**Sensor depth**: lightweight (3 mutations, re-run of all 3 round-1 mutations)
**Result**: 3/3 killed - ✅ PASS

Sensor mechanics: git worktree at `<scratchpad>/sensor-scratch2` (HEAD `49bac2a`), one mutation at a time, reverted between each, worktree removed with `git worktree remove --force` after. `git status --porcelain` on the real tree was identical before and after sensor work (only the pre-existing round-1 artifacts: `.specs/LESSONS.md`, `.specs/lessons.json`, `.specs/features/conexao-llm-local/spec.md` modified, `validation.md` untracked - none of these are sensor output).

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code | ✅ - 130 lines, all 7 new tests map 1:1 to a named gap (Fix 1/2/3/4 from round 1) |
| Surgical changes | ✅ - only `tests/integration/test_context_cli.py` touched; no production code changed |
| No scope creep | ✅ - diff is test-only, matches the round-1 fix-task brief exactly |
| Matches patterns | ✅ - reuses `_set_argv`, `unreachable_local_llm` fixture where the scenario doesn't need a specific `context_window`, `Candidate`/`ChunkProfile` imports already used elsewhere in the file |
| Spec-anchored outcome check (asserted values match spec) | ✅ - all 6 previously-gapped ACs now assert the spec-defined outcome (call args, ordering, stderr message, exit code) |
| Per-layer Coverage Expectation met (domain 1:1 ACs; routes happy+edge+error) | ✅ - orchestration layer (`context_cli.main()`) now has happy + edge + error coverage for every flag |
| Every test maps to a spec requirement - no unclaimed tests | ✅ - each new test name and body traces directly to LLM-11/12/13/14/15/16 or the context-window warning (design.md-derived, not a numbered AC, but explicitly named in round 1's Fix 3) |
| Documented guidelines followed | none found (no `AGENTS.md`/`CONTRIBUTING.md`) - strong defaults applied, consistent with round 1 |

**Minor nit (non-blocking)**: the file's module docstring (`tests/integration/test_context_cli.py:1`) still reads `"...(LLM-01..LLM-10, LLM-12/13)."` and was not updated to reflect the now-covered LLM-11/14/15/16 and the context-window-warning tests. Cosmetic documentation staleness, not a coverage or correctness issue - not raised as a gap.

---

## Edge Cases

- [x] `LOCAL_LLM_BASE_URL` inválido: now covered at CLI level too - `tests/integration/test_context_cli.py:281-289` `test_rejects_invalid_local_llm_base_url_before_health_check` (`check_health` and `scoped_connection` both fail-if-called, confirming rejection happens before either)
- [x] Pergunta só com espaços em branco tratada como vazia: unchanged, `tests/unit/test_query.py:12-14`, `tests/integration/test_context_cli.py:81-87`
- [x] Dois chunks do mesmo `document_id` sem deduplicar: unchanged, `tests/unit/test_context_block.py:37-47`

---

## Gate Check

- **Gate command**: `uv run ruff check . && uv run ruff format --check . && uv run pytest tests/unit tests/integration -q`
- **Result**: `ruff check` - all checks passed; `ruff format --check` - 109 files already formatted; `pytest tests/unit tests/integration` - 171 passed, 0 failed, 0 skipped
- **Additional gate**: `uv run pytest tests/isolation -q` - 10 passed, 0 failed; `tests/isolation/` not in the changed-files list (confirmed via `git diff 4ab9d3b..HEAD --stat`)
- **Test count before this round** (`4ab9d3b`): 164 (`tests/unit tests/integration`)
- **Test count after this round** (`49bac2a`): 171
- **Delta**: +7 new tests, 0 deleted, 0 weakened
- **Skipped tests**: none
- **Failures**: none

---

## Fix Plans

None - all 4 fix items from round 1 are closed. See AC table and sensor table above for evidence.

---

## Requirement Traceability Update

| Requirement | Previous Status (round 1) | New Status |
| ----------- | -------------------------- | ----------- |
| LLM-01 to LLM-10 | ✅ Verified | ✅ Verified (unchanged) |
| LLM-11 | ❌ Needs Fix | ✅ Verified |
| LLM-12 | ❌ Needs Fix | ✅ Verified |
| LLM-13 | ❌ Needs Fix | ✅ Verified |
| LLM-14 | ❌ Needs Fix | ✅ Verified |
| LLM-15 | ❌ Needs Fix | ✅ Verified |
| LLM-16 | ❌ Needs Fix | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 16/16 ACs matched spec outcome end-to-end (up from 10/16 in round 1)
**Sensor**: 3/3 mutations killed (up from 2/3 in round 1 - the context-window-warning mutant is now killed)
**Gate**: 171 + 10 (isolation) = 181 passed, 0 failed

**What works**: All three round-1 gaps are closed by commit `49bac2a`. The 6 previously-untested flag-plumbing ACs (`--mode`, `--top-k`, `--profile`, `--open`) now have `context_cli.main()`-level evidence, following exactly the fix tasks round 1 specified: capture `run_search`'s call arguments for the P2 flags, and an ordered-call list for `--open`. The context-window-exceeds warning branch, previously a surviving mutant, now has both a triggering and a non-triggering test and kills the mutation on re-run. The invalid-`LOCAL_LLM_BASE_URL` edge case is now covered at CLI level too.

**Issues found**: none blocking. One cosmetic nit: the test file's module docstring wasn't updated to list the newly-covered requirement IDs.

**Next steps**: None required for this feature. Round 1's L-005/L-006 lessons (recorded against the underlying "domain-tested but orchestration-untested" gap pattern) already cover the general lesson from this fix cycle - not duplicated here, per instruction.
