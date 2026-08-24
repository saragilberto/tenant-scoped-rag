# STATE

## Decisions

### AD-001
- **Decision**: Este repositório é o laboratório público (`tenant-scoped-rag`), com corpus inventado; o serviço interno `sh3-conhecimento` é outro repositório, privado, e aplica depois o que aqui for provado.
- **Reason**: As partes arriscadas (filtro dentro do índice ANN, prova de isolamento, escolha de modo de busca) chegam medidas ao serviço interno em vez de descobertas em produção — e nenhum dado da SH3 cruza para o público. Resolve de vez o risco de vazar a conta de trabalho no histórico do git.
- **Trade-off**: Duas bases de código a manter; o que for aprendido aqui precisa ser portado à mão para o serviço interno, que provavelmente não será em Python.
- **Scope**: todo o repositório; fronteira com `suporte-sh3-hub` e `sh3-mcp-server`.
- **Date**: 2026-08-20
- **Status**: active

### AD-002
- **Decision**: O isolamento entre tenants é imposto por RLS no PostgreSQL, ancorada em `current_setting('app.tenant_id')` aplicada via `SET LOCAL`, com papel de banco sem `BYPASSRLS` e que não é dono das tabelas.
- **Reason**: Move a afirmação do README de "meus WHEREs estão corretos" para "o banco recusa". É a única versão da tese que sobrevive a uma leitura hostil do código.
- **Trade-off**: Predicado de RLS não é *leakproof* e não desce para dentro da varredura do índice HNSW — o que cria o risco de retornar menos que `top_k` e obriga a mitigação com `hnsw.iterative_scan` mais teste de recall (RAG-10).
- **Scope**: esquema do banco, camada de conexão, suíte de isolamento.
- **Date**: 2026-08-20
- **Status**: active

### AD-003
- **Decision**: A identidade do tenant entra por variável de ambiente da instância do servidor MCP; nenhuma tool aceita parâmetro de escopo.
- **Reason**: O cliente não tem como forjar o que nunca envia. Um `tenant_id` como argumento de tool é justamente o valor que um atacante controla, e tornaria a prova de isolamento encenação.
- **Trade-off**: Um processo de servidor por tenant. Não serve o caso de N usuários com visibilidades diferentes numa mesma sessão — que é o caso do `sh3-conhecimento` e exigirá trocar a origem da GUC lá.
- **Scope**: inicialização do servidor, contrato das quatro tools.
- **Date**: 2026-08-20
- **Status**: active

### AD-004
- **Decision**: A avaliação é inteiramente determinística (recall@k, precision@k, MRR, nDCG@10) sobre golden set escrito à mão; RAGAS e qualquer métrica com LLM-juiz ficam fora.
- **Reason**: `faithfulness` não se aplica a servidor que não gera resposta, e métrica com LLM-juiz exige chave de API — contradizendo o argumento de que qualquer pessoa clona e reproduz os números publicados.
- **Trade-off**: Perde-se a menção a RAGAS, que era um dos itens da aula de origem; a qualidade da geração não é medida em lugar nenhum.
- **Scope**: harness de avaliação, tabela de ablação, README.
- **Date**: 2026-08-20
- **Status**: active

### AD-005
- **Decision**: A busca léxica usa `ts_rank_cd` sobre `tsvector`, e a fusão híbrida usa Reciprocal Rank Fusion com k=60.
- **Reason**: PostgreSQL não implementa BM25 — o ranking nativo é tf-idf com normalização por tamanho, sem saturação de termo. E RRF combina posições, não notas, dispensando normalizar cosseno contra `ts_rank_cd`, que vivem em escalas incompatíveis.
- **Trade-off**: O ranking léxico é mais fraco que BM25 de verdade; extensão externa (`pg_search`/ParadeDB) resolveria ao custo de mais uma dependência de infraestrutura.
- **Scope**: camada de busca, README.
- **Date**: 2026-08-20
- **Status**: active

## Handoff

- **Feature**: rag-com-escopo-de-tenant (`.specs/features/rag-com-escopo-de-tenant/`)
- **Phase / Task**: Tasks escrito e validado (`validate_tasks.py`: 0 erros, 4 avisos — todos de camada de configuração que a matriz declara `none`). Spec confirmada, design aprovado. Aguardando aprovação das tasks e da matriz de cobertura para iniciar Execute.
- **Completed**: discussão das áreas cinzentas · context.md · spec.md (34 requisitos, confirmada) · AD-001 a AD-005 · pesquisa técnica (pgvector 0.8.1; SDK MCP v2 — `FastMCP` renomeada para `MCPServer`) · design.md (aprovado) · tasks.md (32 tasks em 6 fases)
- **In-progress** (file:line): nenhum
- **Next step**: aprovar tasks + matriz de cobertura. Execute começa por T1 (identidade local do git antes do primeiro commit) e T4/T5 (corpus) — 32 tasks empacotam em ~5 lotes, então cabe a oferta de sub-agentes por lote.
- **Blockers**: nenhum. Instalar `uv` no início da execução (ausente; Python do sistema é 3.9.6 e o SDK MCP v2 exige ≥ 3.10). Docker rodando.
- **Uncommitted files**: todos — `git init` ainda não executado (é a T1).
- **Branch**: n/a
