# Conexão com LLM Local Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute
flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source
of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier,
discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/conexao-llm-local/design.md`
**Status**: Draft

---

## Test Coverage Matrix

> Generated from codebase sampling (`tests/unit/`, `tests/integration/`, `.github/workflows/ci.yml`)
> and the strong default (no `AGENTS.md`/`CONTRIBUTING.md`/`docs/` found in this repo) — confirm
> before Execute.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------- | --------------------- | ------------------ | ------------ |
| `rag/query.py` — validação pura (`validate_query`, `validate_top_k`, `validate_mode`) | unit | Todo ramo: vazio, só espaço, no limite, acima do limite, `top_k` abaixo/acima/nas bordas 1 e 50, modo desconhecido — 1:1 com LLM-06, LLM-07, LLM-12, LLM-13 | `tests/unit/test_query.py` | `uv run pytest tests/unit -q` |
| `rag/local_llm.py` — `resolve_base_url`, `check_health`, `open_browser` | unit | Todo ramo: URL padrão, URL custom válida, URL inválida (não http/https), saudável com `meta.n_ctx`, saudável sem `meta.n_ctx`, inacessível, timeout, navegador abre ok, navegador falha | `tests/unit/test_local_llm.py` | `uv run pytest tests/unit -q` |
| `rag/context_block.py` — `build_block`, `estimate_tokens`, `copy_to_clipboard` | unit | Bloco com 1 candidato e com vários (citação por `document_id`+posição), `estimate_tokens` monotônico, clipboard presente/ausente/falhando (mock de `subprocess`/`shutil.which`) | `tests/unit/test_context_block.py` | `uv run pytest tests/unit -q` |
| `rag/context_cli.py` — `build_parser` | unit | Defaults de `--mode`/`--top-k`/`--profile`/`--open`; rejeição de valor de `--mode`/`--profile` fora do conjunto fechado | `tests/unit/test_context_cli_parser.py` | `uv run pytest tests/unit -q` |
| `rag/context_cli.py` — `main` (fluxo ponta a ponta) | integration | Caminho feliz contra Postgres real (mesma base do `tests/integration`); `RAG_TENANT_ID` ausente/desconhecido; pergunta vazia; zero chunks; banco inacessível (via monkeypatch, como `tests/integration/test_server.py` já faz para outros casos) — happy path + todo edge case listado no spec | `tests/integration/test_context_cli.py` | `uv run pytest tests/integration -q` |
| `rag/server.py` — regressão da extração para `rag/query.py` | integration | Suíte existente permanece verde sem edição — nenhuma tool, assinatura ou mensagem de erro muda | `tests/integration/test_server*.py` (existentes, não editados) + `tests/isolation/*` (existentes, gate extra por tocar arquivo crítico de isolamento) | `uv run pytest tests/integration -q && uv run pytest tests/isolation -q` |
| `pyproject.toml` — script `rag-context` | none | build gate only | - | `uv run ruff check . && uv run ruff format --check .` |

**Coverage Expectation aplicado**: domínio/lógica de negócio (`query.py`, `local_llm.py`,
`context_block.py`) cobre todo ramo, 1:1 com os critérios de aceite do spec; a camada de
orquestração/CLI (`context_cli.py`) tem parser testado por unit e fluxo completo por integration;
config (`pyproject.toml`) só passa pelo build gate.

## Gate Check Commands

> Gerado a partir de `.github/workflows/ci.yml` e `pyproject.toml` — confirmar antes de Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks só com unit tests | `uv run pytest tests/unit -q` |
| Full | Após tasks com integration tests | `uv run pytest tests/unit -q && uv run pytest tests/integration -q` |
| Build | Fim de fase, ou tasks só de configuração | `uv run ruff check . && uv run ruff format --check . && uv run pytest tests/unit tests/integration -q` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks
within a phase execute in order.

### Phase 1: Extrair validação e dispatch de busca para `rag/query.py`

```
T1 → T2
```

### Phase 2: Ponte com o LLM local

```
T3
```

### Phase 3: Bloco de contexto e entrega

```
T4
```

### Phase 4: Comando `rag-context`

```
T5 → T6 → T7
```

---

## Task Breakdown

### T1: Criar `rag/query.py` com validação e dispatch de busca

**What**: Novo módulo com `MAX_QUERY_CHARS`, `MIN_TOP_K`, `MAX_TOP_K`, `SEARCH_MODULES`,
`validate_query`, `validate_top_k`, `validate_mode` e `run_search` — os mesmos valores e a mesma
lógica hoje privados em `server.py`, movidos sem alteração de comportamento. `server.py` ainda não é
tocado nesta task.
**Where**: `src/rag/query.py`
**Depends on**: None
**Reuses**: `rag.retrieval.semantic/lexical/hybrid`, `rag.chunking.ChunkProfile`, `rag.retrieval.Candidate` — os mesmos que `server.py` já importa
**Requirement**: LLM-01, LLM-06, LLM-07, LLM-12, LLM-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `validate_query`, `validate_top_k`, `validate_mode` e os valores de `MAX_QUERY_CHARS`/`MIN_TOP_K`/`MAX_TOP_K` são idênticos aos que hoje vivem em `server.py` (mesmos limites, mesmas mensagens de erro)
- [x] `run_search(conn, query, mode, top_k, profile)` despacha para `SEARCH_MODULES[mode].search(...)`
- [x] Gate check passes: `uv run pytest tests/unit -q`
- [x] Test count: cobre todo ramo listado na Test Coverage Matrix para este módulo (sem exclusão silenciosa)

**Tests**: unit
**Gate**: quick

**Commit**: `feat(query): extract search validation and mode dispatch into rag.query`

---

### T2: Migrar `server.py` para usar `rag/query.py`

**What**: Remover de `server.py` as definições privadas equivalentes ao que `rag/query.py` agora
provê; `server.search` e `server.explain_retrieval` passam a chamar `query.validate_*` e
`query.run_search`. Nenhuma tool, assinatura ou mensagem de erro observável muda.
**Where**: `src/rag/server.py`
**Depends on**: T1
**Reuses**: `rag.query` (T1)
**Requirement**: N/A — regressão de comportamento existente (RAG-11/12/13/16), não um requisito novo desta feature

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `server.py` não define mais `_validate_query`/`_validate_top_k`/`_validate_mode`/`_SEARCH_MODULES`/`_MAX_QUERY_CHARS`/`_MIN_TOP_K`/`_MAX_TOP_K` — importa de `rag.query`
- [x] Nenhum teste existente em `tests/integration/test_server*.py` ou `tests/isolation/*` foi editado
- [x] Gate check passes: `uv run pytest tests/integration -q && uv run pytest tests/isolation -q`
- [x] Test count: mesma contagem de testes que passava antes desta task (nenhuma remoção, nenhuma falha)

**Tests**: integration
**Gate**: full

**Commit**: `refactor(server): use rag.query for validation and mode dispatch`

---

### T3: Criar `rag/local_llm.py`

**What**: Novo módulo com `resolve_base_url()`, `HealthStatus`, `check_health(base_url, timeout)` e
`open_browser(base_url)`, usando só `urllib.request` e `webbrowser` da stdlib. Nunca chama endpoint
de chat completion.
**Where**: `src/rag/local_llm.py`
**Depends on**: None
**Reuses**: nada externo (stdlib apenas)
**Requirement**: LLM-04, LLM-05, LLM-15, LLM-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `resolve_base_url()` lê `LOCAL_LLM_BASE_URL`, aplica o default `http://127.0.0.1:8080`, e levanta `ValueError` para valor que não é `http(s)`
- [x] `check_health` nunca propaga exceção — timeout, erro de conexão e resposta malformada viram `HealthStatus(reachable=False, ...)`
- [x] `check_health` extrai `context_window` de `meta.n_ctx` quando presente na resposta de `GET {base_url}/v1/models`
- [x] `open_browser` retorna `False` em vez de propagar quando `webbrowser.open` falha
- [x] Gate check passes: `uv run pytest tests/unit -q`
- [x] Test count: cobre todo ramo listado na Test Coverage Matrix para este módulo

**Tests**: unit
**Gate**: quick

**Commit**: `feat(local-llm): add health check and browser bridge for the local LLM`

---

### T4: Criar `rag/context_block.py`

**What**: Novo módulo com `build_block(question, candidates)`, `estimate_tokens(text)` e
`copy_to_clipboard(text)`.
**Where**: `src/rag/context_block.py`
**Depends on**: None
**Reuses**: `rag.retrieval.Candidate`
**Requirement**: LLM-02, LLM-03, LLM-08, LLM-10

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `build_block` inclui a pergunta, cada chunk citado por `document_id` e posição, e a instrução de responder só com base no conteúdo apresentado
- [x] `copy_to_clipboard` retorna `False` sem levantar exceção quando `pbcopy` está ausente (`shutil.which` retorna `None`) ou quando `subprocess.run` falha
- [x] `estimate_tokens` é determinístico e cresce com o tamanho do texto
- [x] Gate check passes: `uv run pytest tests/unit -q`
- [x] Test count: cobre todo ramo listado na Test Coverage Matrix para este módulo

**Tests**: unit
**Gate**: quick

**Commit**: `feat(context-block): add context block builder and clipboard delivery`

---

### T5: Criar o parser de argumentos de `rag-context`

**What**: `build_parser()` em um novo `context_cli.py`: argumento posicional `question`, `--mode
{semantic,lexical,hybrid}` (default `hybrid`), `--top-k` (default `5`), `--profile {P512,P1024}`
(default `P512`), `--open` (flag booleana). Sem `main()` ainda.
**Where**: `src/rag/context_cli.py`
**Depends on**: None
**Reuses**: `rag.chunking.ChunkProfile` (para os valores válidos de `--profile`)
**Requirement**: LLM-11, LLM-14, LLM-15

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `build_parser().parse_args(["pergunta"])` produz `mode="hybrid"`, `top_k=5`, `profile="P512"`, `open=False`
- [x] Um `--mode` ou `--profile` fora do conjunto fechado é rejeitado pelo próprio `argparse` (erro antes de qualquer lógica de negócio)
- [x] Gate check passes: `uv run pytest tests/unit -q`
- [x] Test count: cobre todo ramo listado na Test Coverage Matrix para este módulo

**Tests**: unit
**Gate**: quick

**Commit**: `feat(context-cli): add argument parser for rag-context`

---

### T6: Implementar `main()` de `rag-context`

**What**: Orquestra o fluxo completo descrito em `design.md`: resolve tenant → valida pergunta/top_k/mode → checagem de saúde do LLM local (aviso, nunca bloqueio) → recuperação escopada → monta o bloco → avisa se o bloco estimado excede `context_window` → imprime em stdout → copia para a área de transferência → abre o navegador se `--open`. Diagnóstico em stderr, bloco de contexto só em stdout.
**Where**: `src/rag/context_cli.py`
**Depends on**: T1, T3, T4, T5
**Reuses**: `rag.db.resolve_tenant_from_env`, `rag.db.scoped_connection`, `rag.query` (T1), `rag.local_llm` (T3), `rag.context_block` (T4), `build_parser` (T5)
**Requirement**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, LLM-08, LLM-09, LLM-10, LLM-11, LLM-12, LLM-13, LLM-15, LLM-16

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Caminho feliz contra o Postgres do repositório (tenant `meridian`, corpus já ingerido pela suíte de integração) produz um bloco em stdout e o mesmo conteúdo na área de transferência quando `pbcopy` está disponível
- [x] `RAG_TENANT_ID` ausente/desconhecido falha com a mesma mensagem de `resolve_tenant_from_env`, sem tentar a checagem de saúde nem a recuperação (LLM-06)
- [x] Pergunta vazia ou acima do limite é rejeitada antes de qualquer chamada ao banco (LLM-07)
- [x] LLM local inacessível (nenhuma instância rodando, como no ambiente de CI) produz um aviso em stderr e ainda assim entrega o bloco (LLM-05)
- [x] Zero chunks retornados não copia nem imprime um bloco vazio (LLM-08)
- [x] Banco inacessível (via monkeypatch de `scoped_connection`) produz mensagem clara em stderr (LLM-09)
- [x] `pbcopy` ausente (esperado no runner de CI, Linux) não falha o comando — stdout continua correto (LLM-10)
- [x] Gate check passes: `uv run pytest tests/unit -q && uv run pytest tests/integration -q`
- [x] Test count: cobre todo caso listado na Test Coverage Matrix para `context_cli.py — main`, sem exclusão silenciosa

**Tests**: integration
**Gate**: full

**Commit**: `feat(context-cli): wire retrieval, health check and delivery into rag-context main`

---

### T7: Registrar o script `rag-context`

**What**: Adicionar `rag-context = "rag.context_cli:main"` a `[project.scripts]` em `pyproject.toml`.
**Where**: `pyproject.toml`
**Depends on**: T6
**Reuses**: N/A
**Requirement**: N/A — empacotamento, não um critério de aceite

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `uv sync` seguido de `uv run rag-context --help` executa e mostra `--mode`/`--top-k`/`--profile`/`--open`
- [ ] Gate check passes: `uv run ruff check . && uv run ruff format --check .`

**Tests**: none
**Gate**: build

**Commit**: `chore(context-cli): register rag-context console script`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3 → Phase 4

Phase 1:  T1 ------→ T2
Phase 2:  T3
Phase 3:  T4
Phase 4:  T5 ------→ T6 ------→ T7

T6 also depends directly on earlier phases (not just T5):
  T1 ----------------→ T6
  T3 ----------------→ T6
  T4 ----------------→ T6
```

Execution is strictly sequential - there is no intra-phase parallelism. 7 tasks total fits a single
task-budgeted batch (≤ ~8 tasks) - Execute runs inline, no sub-agent offer needed.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Criar `rag/query.py` | 1 arquivo novo | ✅ Granular |
| T2: Migrar `server.py` para `rag/query.py` | 1 arquivo modificado | ✅ Granular |
| T3: Criar `rag/local_llm.py` | 1 arquivo novo | ✅ Granular |
| T4: Criar `rag/context_block.py` | 1 arquivo novo | ✅ Granular |
| T5: Parser de `rag-context` | 1 arquivo novo (só o parser) | ✅ Granular |
| T6: `main()` de `rag-context` | 1 arquivo modificado (mesmo de T5) | ✅ Granular |
| T7: Registrar script | 1 arquivo modificado | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ----------------------- | -------------- | ------ |
| T1 | None | Nenhuma seta de entrada | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | None | Nenhuma seta de entrada (Fase 2 isolada) | ✅ Match |
| T4 | None | Nenhuma seta de entrada (Fase 3 isolada) | ✅ Match |
| T5 | None | Nenhuma seta de entrada (Fase 4 começa em T5) | ✅ Match |
| T6 | T1, T3, T4, T5 | T5 → T6 dentro da Fase 4; T1/T3/T4 são fases anteriores, já concluídas quando a Fase 4 começa | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | ----------------------------- | ---------------- | ---------- | ------ |
| T1: Criar `rag/query.py` | `rag/query.py` (validação pura) | unit | unit | ✅ OK |
| T2: Migrar `server.py` | `rag/server.py` (regressão) | integration | integration | ✅ OK |
| T3: Criar `rag/local_llm.py` | `rag/local_llm.py` | unit | unit | ✅ OK |
| T4: Criar `rag/context_block.py` | `rag/context_block.py` | unit | unit | ✅ OK |
| T5: Parser de `rag-context` | `rag/context_cli.py` — `build_parser` | unit | unit | ✅ OK |
| T6: `main()` de `rag-context` | `rag/context_cli.py` — `main` | integration | integration | ✅ OK |
| T7: Registrar script | `pyproject.toml` | none | none | ✅ OK |

---

## Task Verification Standards

Every task above follows `Done when` + `Tests` + `Gate`. Cada `Done when` é binário (passa/falha) e
referencia o comando de gate correspondente em **Gate Check Commands**. A contagem de testes exigida
por task vem da Test Coverage Matrix, não de um número fixo — o gate é "cobre todo ramo listado",
verificável lendo os testes escritos contra a lista de ramos de cada módulo.
