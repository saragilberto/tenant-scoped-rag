# RAG com Escopo de Tenant Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/rag-com-escopo-de-tenant/design.md`
**Status**: Draft
**Ferramentas**: todas as tasks são `MCP: NONE` · `Skill: NONE`. Nenhum MCP configurado nesta máquina serve a este projeto (os disponíveis apontam para bancos de produto da SH3, que estão explicitamente fora de escopo).

---

## Test Coverage Matrix

> Gerada do codebase, das diretrizes do projeto e da spec — confirmar antes de Execute. Diretrizes encontradas: **nenhuma** (repositório greenfield, sem testes, sem `AGENTS.md`, sem config de runner). Defaults fortes aplicados.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Lógica de domínio (chunking, embedding, métricas, RRF) | unit | Todos os ramos; 1:1 com as ACs da spec; todo edge case listado tem teste | `tests/unit/test_*.py` | `uv run pytest tests/unit -q` |
| Acesso a dados, migrações, papéis e RLS | integration | Caminhos de consulta + caminhos de erro + toda AC de escopo (RAG-14 a RAG-17) | `tests/integration/test_*.py` | `uv run pytest tests/integration -q` |
| Tools MCP (contrato do servidor) | integration | As quatro tools: caminho feliz + todo edge case listado + caminhos de erro | `tests/integration/test_server_*.py` | `uv run pytest tests/integration -q` |
| Isolamento entre tenants | integration | 100% das perguntas cruzadas do golden set; canário obrigatório | `tests/isolation/test_*.py` | `uv run pytest tests/isolation -q` |
| Conteúdo versionado (corpus, golden set) | unit | Integridade estrutural: manifesto válido, sobreposição mínima, toda referência do golden set resolve | `tests/unit/test_*_integrity.py` | `uv run pytest tests/unit -q` |
| Configuração (pyproject, compose, CI, README) | none | — (só o gate de build) | — | build gate |

**Nota sobre conteúdo:** corpus e golden set recebem teste de integridade em vez de `Tests: none`. Um golden set que referencia documento removido corromperia silenciosamente toda métrica publicada — é a classe de falha que não dá sintoma.

## Gate Check Commands

> Gerados do codebase — confirmar antes de Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tasks com testes unitários apenas | `uv run pytest tests/unit -q` |
| Full | Após tasks com testes de integração ou isolamento | `uv run pytest tests/unit tests/integration tests/isolation -q` |
| Build | Após conclusão de fase, e em tasks só de configuração | `uv run ruff check . && uv run ruff format --check . && uv run pytest -q` |

---

## Execution Plan

As fases rodam em sequência; dentro de cada fase as tasks rodam em ordem. A ordem das fases é
determinada pelo risco, não pela arquitetura: **corpus e golden set vêm antes de qualquer código de
recuperação**, porque são trabalho de escrita, valem ~30% do esforço e são onde projetos desse tipo
morrem — com toda a engenharia pronta e nenhum número para publicar.

Ordem: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

### Phase 1: Fundação e conteúdo

```
T1 → T2
T1 → T3
T4 → T5
T4 → T6
T5 → T7
```

### Phase 2: Esquema, papéis e RLS

```
T8 → T9
T9 → T10
T10 → T11
T11 → T12
T12 → T13
```

### Phase 3: Ingestão

```
T14 → T16
T15 → T16
```

### Phase 4: Recuperação

```
T17 → T19
T18 → T19
T17 → T20
T19 → T21
```

### Phase 5: Servidor MCP e prova de isolamento

```
T22 → T23
T22 → T24
T22 → T25
T22 → T26
T26 → T27
```

### Phase 6: Avaliação e publicação

```
T28 → T29
T29 → T30
T30 → T31
T30 → T32
T31 → T32
```

---

## Task Breakdown

### Phase 1: Fundação e conteúdo

#### T1: Inicializar repositório com identidade local correta

**What**: `git init`, `.gitignore` para Python, e o teste que falha se a identidade do repositório apontar para a conta de trabalho.
**Where**: `tests/unit/test_repo_hygiene.py`
**Depends on**: None
**Requirement**: risco registrado em `design.md` §Risks

**Done when**:

- [x] Repositório inicializado com `git config user.email` **local** apontando para o `noreply` pessoal
- [x] Teste falha quando o `user.email` do repositório contém `sh3` ou difere do endereço pessoal
- [x] `.gitignore` cobre `.venv/`, `__pycache__/`, `.env` e cache de modelos
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 2 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `chore(repo): initialize repository with local git identity guard`

---

#### T2: Declarar o projeto e as dependências

**What**: `pyproject.toml` com Python 3.12, dependências fixadas (`mcp` v2, `psycopg[binary]`, `pgvector`, `sentence-transformers`, `pytest`, `ruff`) e os entry points de CLI.
**Where**: `pyproject.toml`
**Depends on**: T1
**Requirement**: RAG-23

**Done when**:

- [x] `uv sync` resolve sem conflito
- [x] Entry points `ingest`, `rag-server` e `rag-eval` declarados
- [x] `ruff` configurado para lint e format
- [x] Gate check passa: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`

**Tests**: none
**Gate**: build
**Commit**: `build(deps): declare project, pinned dependencies and entry points`

---

#### T3: Subir PostgreSQL 17 com pgvector 0.8.1

**What**: `docker-compose.yaml` com a imagem `pgvector/pgvector:pg17`, dois bancos — o principal e o de linha de base de tenant único exigido pelo RAG-10 — e volume nomeado.
**Where**: `docker-compose.yaml`
**Depends on**: T1
**Requirement**: RAG-10

**Done when**:

- [x] `docker compose up -d` sobe e `SELECT extversion FROM pg_extension WHERE extname='vector'` devolve `0.8.1` — ⚠️ spec-precision gap: a imagem `pgvector/pgvector:pg17` é tag flutuante; em 2026-08-24 resolveu `0.8.6` (verificado manualmente), não `0.8.1`. O requisito real de design é `≥ 0.8` (exigido por `hnsw.iterative_scan`, RAG-10) e `0.8.6` satisfaz; `0.8.1` era apenas "corrente em mai/2026"
- [x] Os dois bancos existem e são alcançáveis
- [x] Gate check passa: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`

**Tests**: none
**Gate**: build
**Commit**: `build(db): add PostgreSQL 17 with pgvector 0.8.1 via compose`

---

#### T4: Escrever o corpus do tenant `meridian`

**What**: base de suporte fictícia de um CRM — artigos em markdown com front-matter — e o teste de integridade estrutural que os valida.
**Where**: `tests/unit/test_corpus_integrity.py`
**Depends on**: None
**Requirement**: RAG-01

**Done when**:

- [x] Ao menos 20 artigos em `corpus/meridian/`, cobrindo os 8 assuntos de sobreposição (erro de login, importação de CSV, 2FA, limites de API, exportação de fatura, webhooks, SSO, retenção de logs)
- [x] Ao menos 5 artigos sem títulos internos, para exercitar o chunking por tamanho fixo (RAG-04)
- [x] Teste falha se algum artigo tiver front-matter incompleto ou visibilidade fora do vocabulário `empresa|departamentos|equipes|restrito`
- [x] Teste falha se algum artigo contiver padrão de dado real (CPF, e-mail, telefone)
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(corpus): add meridian knowledge base with structural integrity tests`

---

#### T5: Escrever o corpus do tenant `halcyon` e provar a sobreposição

**What**: base fictícia de uma plataforma de faturamento cobrindo os mesmos oito assuntos com conteúdo diferente, e as asserções de sobreposição — sem elas o teste de isolamento é vacuoso.
**Where**: `tests/unit/test_corpus_integrity.py`
**Depends on**: T4
**Requirement**: RAG-01

**Done when**:

- [x] Ao menos 20 artigos em `corpus/halcyon/`, cobrindo os mesmos 8 assuntos com solução e vocabulário distintos
- [x] Teste falha se algum dos 8 assuntos não tiver artigo nos **dois** tenants
- [x] Teste falha se houver trecho de 12+ palavras idêntico entre os dois corpora — a sobreposição é de assunto, nunca de texto
- [x] As asserções de front-matter e de ausência de dado real de T4 valem também para este corpus
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 7 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(corpus): add halcyon knowledge base with deliberate topical overlap`

---

#### T6: Escrever o golden set de `meridian`

**What**: 30 perguntas anotadas com os documentos relevantes, e o teste que garante que toda referência resolve.
**Where**: `tests/unit/test_golden_set_integrity.py`
**Depends on**: T4
**Requirement**: RAG-31

**Done when**:

- [x] 30 perguntas em `eval/golden/meridian.yaml`, cada uma com ao menos um documento relevante anotado
- [x] Ao menos 10 perguntas incidem sobre os assuntos de sobreposição — são as que mais pressionam o isolamento
- [x] Teste falha se alguma pergunta referenciar documento inexistente
- [x] Teste falha se o conjunto não tiver exatamente 30 perguntas
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(eval): add meridian golden set with reference integrity tests`

---

#### T7: Escrever o golden set de `halcyon`

**What**: as 30 perguntas do segundo tenant, e a asserção que impede referência cruzada entre tenants.
**Where**: `tests/unit/test_golden_set_integrity.py`
**Depends on**: T5
**Requirement**: RAG-31

**Done when**:

- [x] 30 perguntas em `eval/golden/halcyon.yaml`, com ao menos 10 sobre os assuntos de sobreposição
- [x] Teste falha se alguma pergunta referenciar documento do **outro** tenant — anotação errada inverteria o resultado da suíte de isolamento
- [x] As asserções de T6 valem para os dois conjuntos
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(eval): add halcyon golden set and cross-tenant reference guard`

---

### Phase 2: Esquema, papéis e RLS

#### T8: Migração de extensões e `immutable_unaccent`

**What**: cria `vector` e `unaccent`, e a função `immutable_unaccent` que torna a coluna gerada possível.
**Where**: `migrations/001_extensions.sql`
**Depends on**: T3
**Requirement**: RAG-08

**Done when**:

- [x] Teste confirma que `immutable_unaccent('orçamento')` devolve `orcamento` e que a função é `IMMUTABLE`
- [x] Migração é idempotente (`IF NOT EXISTS`)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 2 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): add vector/unaccent extensions and immutable unaccent wrapper`

---

#### T9: Migração das tabelas

**What**: `tenants`, `documents` e `chunks` conforme o modelo do design, com `tenant_id` desnormalizado em `chunks` e a coluna `fts` gerada.
**Where**: `migrations/002_tables.sql`
**Depends on**: T8
**Requirement**: RAG-01

**Done when**:

- [x] As três tabelas existem com as colunas e restrições do design
- [x] `chunks.fts` é populada automaticamente ao inserir, com acentos normalizados
- [x] `UNIQUE (tenant_id, source_path, content_hash)` presente em `documents`
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): add tenants, documents and chunks tables`

---

#### T10: Migração dos três papéis

**What**: cria `rag_owner`, `rag_ingest` e `rag_app` com os grants mínimos de cada um.
**Where**: `migrations/003_roles.sql`
**Depends on**: T9
**Requirement**: RAG-15

**Done when**:

- [x] Teste afirma que `rag_app` **não** é dono de `documents` nem de `chunks`
- [x] Teste afirma que `rag_app` não tem `BYPASSRLS` nem `SUPERUSER`
- [x] Teste afirma que `rag_app` não tem `INSERT`, `UPDATE` nem `DELETE` em nenhuma tabela do corpus
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): add owner, ingest and app roles with least privilege`

---

#### T11: Migração das políticas RLS

**What**: habilita RLS em `documents` e `chunks`, com política de leitura por `app.tenant_id` e política de escrita com `WITH CHECK`.
**Where**: `migrations/004_rls.sql`
**Depends on**: T10
**Requirement**: RAG-14

**Done when**:

- [x] RLS habilitada nas duas tabelas, verificada em `pg_class.relrowsecurity`
- [x] Como `rag_app` com `app.tenant_id='meridian'`, `SELECT count(*) FROM chunks` não enxerga linha de `halcyon`
- [x] Como `rag_ingest`, inserir chunk com `tenant_id` diferente do GUC é **rejeitado pelo banco**
- [x] Com `app.tenant_id` não definido, a leitura devolve zero linhas em vez de todas
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): enforce tenant isolation with row level security policies`

---

#### T12: Migração dos índices

**What**: índices HNSW **parciais por perfil de chunk**, GIN sobre `fts`, índice de apoio em `(tenant_id, profile)`, e `hnsw.iterative_scan = strict_order` no banco.
**Where**: `migrations/005_indexes.sql`
**Depends on**: T11
**Requirement**: RAG-10

**Done when**:

- [x] `EXPLAIN` de busca vetorial com `profile='P512'` usa o índice parcial correspondente
- [x] `EXPLAIN` de busca léxica usa o índice GIN
- [x] `SHOW hnsw.iterative_scan` devolve `strict_order` numa conexão nova
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): add per-profile partial HNSW indexes and enable iterative scan`

---

#### T13: `rag.db` — porta única de acesso ao banco

**What**: fábrica de conexão que aplica `SET LOCAL app.tenant_id`, resolve o tenant da variável de ambiente e encerra o processo se ela faltar.
**Where**: `src/rag/db.py`
**Depends on**: T12
**Requirement**: RAG-15, RAG-17

**Done when**:

- [x] `scoped_connection` aplica `SET LOCAL` dentro da transação e conecta como `rag_app`
- [x] `resolve_tenant_from_env` encerra com mensagem explícita quando a variável está ausente, vazia ou desconhecida (RAG-17)
- [x] Teste afirma que o módulo não exporta nenhum outro construtor de conexão — não há caminho para consultar fora do escopo
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(db): add scoped connection factory as the single database door`

---

### Phase 3: Ingestão

#### T14: `rag.chunking` — divisão sensível à estrutura

**What**: divisão por fronteira de seção quando há títulos markdown; tamanho fixo com 15% de overlap quando não há.
**Where**: `src/rag/chunking.py`
**Depends on**: T2
**Requirement**: RAG-03, RAG-04

**Done when**:

- [x] Documento com títulos gera chunks nas fronteiras de seção, sem overlap (RAG-03)
- [x] Documento sem títulos gera chunks de tamanho fixo com 15% de overlap (RAG-04)
- [x] Documento sem títulos maior que um chunk não perde texto nas fronteiras (edge case da spec)
- [x] Os dois perfis (512 e 1024) produzem contagens diferentes sobre o mesmo documento
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 6 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(chunking): split by document structure with fixed-size fallback`

---

#### T15: `rag.embedding` — modelo local com os prefixos do e5

**What**: `embed_passages` e `embed_query` como funções separadas, cada uma com o prefixo obrigatório.
**Where**: `src/rag/embedding.py`
**Depends on**: T2
**Requirement**: RAG-06, RAG-07

**Done when**:

- [x] `embed_passages` prefixa `passage: ` em todo texto antes de gerar vetor (RAG-06)
- [x] `embed_query` prefixa `query: ` (RAG-07)
- [x] Vetores têm 768 dimensões
- [x] Revisão do modelo fixada; ausência de rede na primeira execução falha com mensagem explícita
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(embedding): add e5 encoder with mandatory query/passage prefixes`

---

#### T16: `rag.ingest` — comando de carga idempotente

**What**: CLI que lê o corpus, divide, embeda e grava, sem duplicar em execução repetida.
**Where**: `src/rag/ingest.py`
**Depends on**: T14, T15, T13
**Requirement**: RAG-01, RAG-02, RAG-05

**Done when**:

- [x] Primeira execução grava documentos e chunks com metadados completos e texto original preservado (RAG-01)
- [x] Segunda execução sem alteração deixa as contagens idênticas (RAG-02)
- [x] Arquivo com falha é registrado, a ingestão prossegue e o código de saída é ≠ 0 (RAG-05)
- [x] Teste confirma que a ingestão conecta como `rag_ingest` e é impedida pelo banco de gravar em outro tenant
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 7 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(ingest): add idempotent corpus ingestion command`

---

### Phase 4: Recuperação

#### T17: Busca semântica

**What**: recuperação por distância de cosseno sobre o índice HNSW parcial do perfil ativo.
**Where**: `src/rag/retrieval/semantic.py`
**Depends on**: T16
**Requirement**: RAG-07, RAG-10

**Done when**:

- [x] Consulta é prefixada com `query: ` e ordenada por `<=>` (RAG-07)
- [x] Com escopo ativo e havendo ao menos `top_k` chunks no escopo, devolve exatamente `top_k` (RAG-10)
- [x] Consulta sem correspondência devolve lista vazia, nunca o chunk menos ruim (edge case da spec)
- [x] `Candidate` preserva score e posição, para alimentar `explain_retrieval`
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(retrieval): add scoped semantic search over partial HNSW index`

---

#### T18: Busca léxica

**What**: recuperação por `ts_rank_cd` sobre a coluna `fts`, com dicionário `english` e `unaccent`.
**Where**: `src/rag/retrieval/lexical.py`
**Depends on**: T16
**Requirement**: RAG-08

**Done when**:

- [x] Ordenação por `ts_rank_cd`, usando o índice GIN
- [x] Termo acentuado encontra o documento não acentuado e vice-versa
- [x] Escopo respeitado: consulta de um tenant não alcança chunk do outro
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(retrieval): add scoped lexical search with ts_rank_cd`

---

#### T19: Busca híbrida por RRF

**What**: fusão dos dois rankings por Reciprocal Rank Fusion com k=60, combinando posições.
**Where**: `src/rag/retrieval/hybrid.py`
**Depends on**: T17, T18
**Requirement**: RAG-09

**Done when**:

- [x] Fusão usa posições, não os scores brutos das duas escalas (RAG-09)
- [x] Documento fora do top-3 de ambos os rankings isolados pode aparecer no top-3 fundido
- [x] Escopo respeitado nos dois rankings de origem
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 5 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(retrieval): fuse semantic and lexical rankings with RRF`

---

#### T20: Teste de recall contra a base de tenant único

**What**: o teste que fecha o RAG-10 — compara a recall da busca escopada contra a mesma busca num banco carregado com um tenant só.
**Where**: `tests/integration/test_recall_baseline.py`
**Depends on**: T17
**Requirement**: RAG-10

**Done when**:

- [x] A recall@5 da busca escopada não é inferior à da base de tenant único além da margem declarada no teste
- [x] A falha reporta o número medido, não apenas "falhou"
- [x] Nenhum papel com `BYPASSRLS` é usado — a comparação é entre bancos
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `test(retrieval): measure scoped recall against single-tenant baseline`

---

#### T21: Reranking sob flag

**What**: reordenação opcional com `bge-reranker-v2-m3`, desligada por padrão.
**Where**: `src/rag/retrieval/rerank.py`
**Depends on**: T19
**Requirement**: RAG-32, RAG-33, RAG-34

**Done when**:

- [x] Com a flag ativa, reordena antes do corte em `top_k` (RAG-32)
- [x] Desligado por padrão (RAG-33)
- [x] Flag ativa e modelo ausente falha com mensagem explícita, nunca devolve a ordem não reordenada (RAG-34)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(retrieval): add optional cross-encoder reranking behind a flag`

---

### Phase 5: Servidor MCP e prova de isolamento

#### T22: Servidor MCP com a tool `search`

**What**: `MCPServer` por stdio, bootstrap com resolução de tenant, e a primeira tool.
**Where**: `src/rag/server.py`
**Depends on**: T19
**Requirement**: RAG-11, RAG-12, RAG-13, RAG-16, RAG-17, RAG-21, RAG-22, RAG-23

**Done when**:

- [x] Handshake stdio anuncia as tools com seus esquemas (RAG-21)
- [x] `top_k` fora de 1–50, `query` vazia e `mode` inválido são rejeitados antes de qualquer consulta (RAG-11 a RAG-13)
- [x] Consulta acima de 2.000 caracteres é rejeitada antes de gerar embedding (edge case da spec)
- [x] Nenhum parâmetro de escopo existe na assinatura (RAG-16)
- [x] Banco inacessível devolve erro e o processo permanece vivo (RAG-22)
- [x] Variável de tenant ausente encerra antes de anunciar tool alguma (RAG-17)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 9 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(server): add MCP stdio server with scoped search tool`

---

#### T23: Tool `get_document`

**What**: devolve o documento original completo, com resposta indistinguível entre inexistente e fora de escopo.
**Where**: `src/rag/server.py`
**Depends on**: T22
**Requirement**: RAG-24, RAG-25

**Done when**:

- [x] Documento do escopo devolve texto original íntegro e metadados (RAG-24)
- [x] `doc_id` inexistente e `doc_id` do outro tenant produzem resposta **byte a byte idêntica** (RAG-25)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(server): add get_document tool with indistinguishable not-found`

---

#### T24: Tool `list_sources`

**What**: lista os documentos do escopo ativo com a contagem de chunks de cada um.
**Where**: `src/rag/server.py`
**Depends on**: T22
**Requirement**: RAG-26

**Done when**:

- [x] Lista somente documentos do escopo ativo (RAG-26)
- [x] Base vazia devolve lista vazia sem revelar que o outro tenant tem conteúdo (edge case da spec)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(server): add list_sources tool scoped to the active tenant`

---

#### T25: Tool `explain_retrieval`

**What**: devolve scores, posições em cada ranking e motivo do corte — sem nenhum indício do que ficou fora por escopo.
**Where**: `src/rag/server.py`
**Depends on**: T22
**Requirement**: RAG-27, RAG-28

**Done when**:

- [x] Cada candidato traz score por ranking, posição por ranking, score fundido e motivo do corte (RAG-27)
- [x] Nenhuma contagem, identificador ou campo revela candidato fora do escopo (RAG-28)
- [x] Teste executa a mesma pergunta sobre assunto compartilhado nos dois tenants e compara as respostas: nada em uma denuncia a existência da outra
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(server): add explain_retrieval tool without out-of-scope leakage`

---

#### T26: Suíte de isolamento cruzada

**What**: toda pergunta do golden set de um tenant executada sob a identidade do outro, em todos os modos de busca.
**Where**: `tests/isolation/test_cross_tenant.py`
**Depends on**: T22
**Requirement**: RAG-16, RAG-18, RAG-20

**Done when**:

- [x] As 60 perguntas rodam contra a identidade oposta nos três modos, e nenhum chunk do tenant de origem aparece (RAG-18)
- [x] Teste que injeta instrução maliciosa na `query` tentando alterar escopo — tratada como texto de busca (RAG-20)
- [x] Teste que varre a assinatura das quatro tools e falha se qualquer parâmetro de escopo for introduzido (RAG-16)
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 8 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `test(isolation): assert zero cross-tenant leakage across all modes`

---

#### T27: Teste-canário

**What**: em banco descartável, remove a política RLS e exige que a suíte de isolamento **falhe** — provando que ela detecta vazamento.
**Where**: `tests/isolation/test_canary.py`
**Depends on**: T26
**Requirement**: RAG-19

**Done when**:

- [x] Com a política removida, a suíte de isolamento fica vermelha (RAG-19)
- [x] A política é restaurada ao fim, e o banco principal nunca é tocado
- [x] O canário falha se a suíte de isolamento passar sem a política — verde é o estado de erro aqui
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 2 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `test(isolation): add canary proving the suite detects leakage`

---

### Phase 6: Avaliação e publicação

#### T28: Métricas determinísticas

**What**: `recall@k`, `precision@k`, `MRR` e `nDCG@k` como funções puras sobre listas de identificadores.
**Where**: `src/eval/metrics.py`
**Depends on**: T6, T7
**Requirement**: RAG-29

**Done when**:

- [x] As quatro métricas conferem contra casos calculados à mão no próprio teste
- [x] Lista de resultados vazia e lista de relevantes vazia têm comportamento definido e testado
- [x] Nenhuma chamada de rede em nenhum caminho
- [x] Gate check passa: `uv run pytest tests/unit -q`
- [x] Test count: 10 testes passam (sem deleções silenciosas)

**Tests**: unit
**Gate**: quick
**Commit**: `feat(eval): add deterministic retrieval metrics`

---

#### T29: Harness de avaliação

**What**: executa o golden set contra uma configuração e devolve o resultado agregado.
**Where**: `src/eval/harness.py`
**Depends on**: T28
**Requirement**: RAG-29, RAG-31

**Done when**:

- [x] Executa as 60 perguntas escopadas, cada uma sob a identidade correta (RAG-29)
- [x] Duas execuções sobre a mesma base produzem números idênticos
- [x] Nenhuma chamada a serviço externo em nenhum caminho de execução
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 4 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(eval): add deterministic evaluation harness over the golden set`

---

#### T30: Estudo de ablação

**What**: matriz de 12 execuções — 3 modos × com/sem rerank × 2 perfis de chunk — com saída em tabela markdown.
**Where**: `src/eval/ablation.py`
**Depends on**: T29
**Requirement**: RAG-30

**Done when**:

- [x] As 12 combinações são executadas e emitidas como tabela markdown (RAG-30)
- [x] A tabela declara explicitamente qualquer configuração que não pôde ser medida, em vez de omiti-la
- [x] Execução repetida reproduz a mesma tabela
- [x] Gate check passa: `uv run pytest tests/unit tests/integration tests/isolation -q`
- [x] Test count: 3 testes passam (sem deleções silenciosas)

**Tests**: integration
**Gate**: full
**Commit**: `feat(eval): add ablation study across modes, rerank and chunk profiles`

---

#### T31: Pipeline de CI

**What**: workflow do GitHub Actions com PostgreSQL como service container e a suíte de isolamento como gate obrigatório.
**Where**: `.github/workflows/ci.yml`
**Depends on**: T30
**Requirement**: RAG-18, RAG-19

**Done when**:

- [x] Workflow sobe `pgvector/pgvector:pg17`, roda migrações, ingere o corpus e executa as três suítes
- [x] Falha da suíte de isolamento reprova o workflow
- [x] Cache do modelo configurado, com revisão fixada, para a CI não ficar vermelha por rede
- [x] Gate check passa: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`

**Tests**: none
**Gate**: build
**Commit**: `ci: run migrations, ingestion and the isolation suite on every push`

---

#### T32: README em inglês

**What**: o entregável público — o problema, o desenho do isolamento, a tabela de ablação e a configuração pronta de cliente MCP.
**Where**: `README.md`
**Depends on**: T30, T31
**Requirement**: RAG-23, RAG-30

**Done when**:

- [x] Abre pelo problema e pelo desenho do isolamento, não pela lista de dependências
- [x] Publica a manchete: `recall@5` por configuração + zero vazamento em 180 consultas cruzadas reais (spec-precision gap: `spec.md` estimava 360 = 60 perguntas × 3 modos × 2 perfis de chunk; a suíte de isolamento implementada em T26 escopa `search()` sempre no perfil fixo `P512` do servidor MCP, então o número real medido é 60 × 3 = 180 — o README publica o número que a suíte de fato executa, não a estimativa original)
- [x] Traz a configuração de Claude Desktop e Claude Code para os dois tenants, colável
- [x] Diz explicitamente que a busca léxica é `ts_rank_cd` e **não** BM25, e por quê
- [x] Gate check passa: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q`

**Tests**: none
**Gate**: build
**Commit**: `docs(readme): publish the isolation design and ablation results`
