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

### AD-006
- **Decision**: Geração assistida por LLM local entra como um comando novo (`rag-context`), externo ao servidor MCP; este repositório nunca chama o endpoint de chat completion do LLM a partir do Python — quem gera é a pessoa, pela interface web que o próprio LLM local (`llamafile`) já serve no navegador. O comando só recupera contexto escopado ao tenant e entrega esse bloco por stdout + área de transferência, com uma checagem de saúde do LLM local que só avisa, nunca bloqueia.
- **Reason**: AD-003/RAG-16 já fixam "servidor recupera, cliente gera"; a feature anterior tinha deixado a geração como ideia adiada por causa de chave de API e custo por pergunta. Um LLM local remove os dois motivos, mas reabrir a fronteira como uma tool nova de geração no servidor MCP teria enfraquecido essa decisão sem necessidade — a pessoa explicitamente preferiu continuar usando a interface de chat que o llamafile já tem.
- **Trade-off**: Nenhuma automação end-to-end (pergunta → resposta) sai deste repositório; a pessoa ainda cola o contexto manualmente no navegador. Em troca, o servidor MCP e a suíte de isolamento continuam exatamente como estão.
- **Scope**: novo comando `rag-context` (`src/rag/context_cli.py`, `local_llm.py`, `context_block.py`, `query.py`); não altera o contrato do servidor MCP.
- **Date**: 2026-08-25
- **Status**: active

## Handoff

- **Feature**: conexao-llm-local (`.specs/features/conexao-llm-local/`)
- **Phase / Task**: spec confirmada, design aprovado, tasks.md escrito e validado (`validate_tasks.py`: 0 erros, 1 aviso — `Tests: none` do T7, que a matriz já confirma como `none` para camada de config). Aguardando aprovação das tasks para iniciar Execute.
- **Completed**: duas rodadas de discussão (propósito da conexão; fronteira com o MCP; formato do chat) · context.md · spec.md (16 requisitos LLM-01..LLM-16, confirmada) · pesquisa técnica ao vivo — subimos `Qwen3.5-0.8B-Q8_0.llamafile --server` nesta máquina e confirmamos porta 8080, endpoint `/v1/models` sem auth com `meta.n_ctx=16384`, sem processo do llamafile deixado rodando · design.md (aprovado) · AD-006 · tasks.md (7 tasks em 4 fases, cabe em um único lote — sem oferta de sub-agentes)
- **In-progress** (file:line): nenhum
- **Next step**: aprovar tasks.md. Execute roda inline (7 tasks ≤ orçamento de um lote), começando por T1 (`rag/query.py`, sem dependências).
- **Blockers**: nenhum.
- **Uncommitted files**: `.specs/features/conexao-llm-local/` (context.md, spec.md, design.md, tasks.md), `.specs/STATE.md` (AD-006 + Handoff) — ainda não commitados; nenhum código de `src/` criado ainda.
- **Branch**: main

### Feature anterior: rag-com-escopo-de-tenant

- Já implementada e commitada (`git log`: `e412ed1`, `0d31dbe`, `dae4db9`, `eff0958`, `960b78a` e commits anteriores) — o Handoff antigo desta seção, que dizia "`git init` ainda não executado", estava desatualizado; reconciliado nesta sessão contra `git log`/`git status` reais. `.specs/features/rag-com-escopo-de-tenant/tasks.md` deve refletir o progresso real de execução se for consultado de novo.
