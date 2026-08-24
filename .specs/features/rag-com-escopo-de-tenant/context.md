# RAG com Escopo de Tenant — Context

**Gathered:** 2026-08-20
**Spec:** `.specs/features/rag-com-escopo-de-tenant/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Um servidor MCP em Python que expõe quatro tools de **recuperação** — `search`, `get_document`,
`list_sources`, `explain_retrieval` — sobre um corpus sintético de dois tenants em PostgreSQL +
pgvector, onde nenhuma consulta de um tenant alcança chunk do outro, com suíte de isolamento em CI
e tabela de ablação no README.

Geração de resposta fica no cliente MCP. O servidor não chama LLM nenhuma.

---

## Implementation Decisions

### Recorte e ordem no programa maior

O projeto é o **laboratório público**. Ele existe para provar, com corpus inventado, as decisões
que depois serão aplicadas no `sh3-conhecimento` (serviço interno da SH3, repositório privado).

Três peças distintas, que estavam sendo tratadas como uma:

1. **Módulo Conhecimento do Hub** — a wiki: autoria e armazenamento. Três specs escritas em
   06/08/2026 (`conhecimento-editor`, `conhecimento-artigos`, `conhecimento-importacao`), todas
   "aguardando confirmação"; módulo scaffoldado e vazio; o protótipo do editor — declarado gate de
   viabilidade — continua pendente.
2. **`sh3-conhecimento`** — o serviço de busca vetorial que lê aquela base. Já decidido como
   serviço separado (`suporte-sh3-hub/docs/modulo-conhecimento.md` §14), por proteção de dados.
3. **`sh3-mcp-server`** — acesso de leitura aos bancos dos produtos, Laravel + `laravel/mcp`.

Este repositório não é nenhuma das três. É o ensaio técnico das partes arriscadas das peças 2 e 3,
com dado inventado e em público.

### Identidade e enforcement

- Cada instância do servidor MCP nasce amarrada a **um** tenant por variável de ambiente. O cliente
  não passa `tenant_id` em lugar nenhum e não tem como forjá-lo.
- A conexão aplica `SET LOCAL app.tenant_id` e políticas **RLS** filtram toda tabela do corpus.
  A barreira final é o PostgreSQL, não o código Python.
- Escolhido em vez de role por tenant (não escala para N usuários com visibilidades diferentes) e
  em vez de `WHERE` na aplicação (a garantia viraria "meus WHEREs estão corretos", que é exatamente
  a afirmação fraca que o projeto existe para superar).
- **Por que carrega para o destino:** trocando a GUC de `tenant_id` por identidade de usuário e o
  predicado por `sistema × visibilidade`, o mesmo desenho vira a autorização do `sh3-conhecimento`.
  O vocabulário `empresa | departamentos | equipes | restrito` já está fixado em
  `modulo-conhecimento.md:274` e não deve divergir.

### Corpus

- Duas bases de suporte de produtos SaaS fictícios. Legível em inglês sem contexto prévio, e o
  formato (artigo com categoria, versão, visibilidade) já ensaia o do `sh3-conhecimento`.
- Sobreposição temática deliberada: as duas bases têm artigo sobre erro de login, importação de
  CSV, autenticação em dois fatores, limites de API. Assunto igual, conteúdo e procedimento
  diferentes — sem isso o teste de isolamento não prova nada, porque a busca de um nunca chegaria
  perto do outro por acaso.
- **Nenhum dado da SH3, de cliente ou de produto real.** Corpus inventado, versionado no repositório.

### Superfície de vazamento do `explain_retrieval`

- A tool mostra candidatos, score, posição em cada ranking e motivo do corte — **somente** entre
  chunks visíveis a quem perguntou.
- Nada na resposta indica que existe algo fora do escopo. Sem contagem de "N descartados por
  escopo": isso vazaria cardinalidade do outro tenant e permitiria inferir assunto sem ler chunk.
- A visão completa que o estudo de ablação precisa vem do harness de avaliação offline, que conecta
  com credencial própria — nunca através da tool.

### Avaliação

- Golden set de 30 perguntas por tenant, escritas à mão, com os chunks relevantes anotados.
- Cada pergunta de um tenant também roda contra a identidade do outro, com resultado esperado
  vazio — a suíte de isolamento reaproveita o golden set em vez de exigir perguntas novas.
- Métricas determinísticas (recall@k, precision@k, MRR, nDCG@10), sem LLM-juiz. RAGAS fica fora:
  exige chave de API e `faithfulness` não se aplica a servidor que não gera resposta.
- Manchete do README: recall@5 na tabela de ablação + zero vazamento em N consultas cruzadas.

### Agent's Discretion

- Transporte **stdio** (assumido, não questionado): é o que Claude Desktop e Claude Code consomem
  sem infraestrutura.
- PostgreSQL sobe por **Docker Compose** no próprio repositório — não há Postgres local nesta máquina.
- Nomes dos dois tenants fictícios, estrutura de diretórios, nomes de módulos e organização dos
  testes ficam a meu critério, dentro das decisões acima.

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área cinzenta foi declinada — as quatro levantadas foram decididas. As decisões técnicas
não levadas à discussão (mitigação de filtragem ANN, estratégia de chunking, constante do RRF,
prefixos do modelo de embedding) estão registradas na tabela de premissas da spec com default e
justificativa, para poderem ser contestadas item a item.

---

## Specific References

- Artefato de origem: "RAG com escopo de tenant", 20/08/2026 — a tese, a stack e as fases vêm dele.
- Correções aplicadas sobre o artefato após revisão técnica:
  1. PostgreSQL **não tem BM25**; a busca léxica é `ts_rank_cd` sobre `tsvector`.
  2. `faithfulness` do RAGAS não se aplica a servidor retrieval-only, e RAGAS exige chave de API —
     contradizendo o argumento "clone e rode".
  3. Identidade tinha ficado indefinida: sem dizer por onde entra, a prova de isolamento seria encenação.
  4. Filtragem sobre índice HNSW ocorre **após** a varredura do índice — risco de retornar menos que
     `top_k` ou degradar para seq scan. Não estava no documento.
  5. Suíte de isolamento verde não prova nada sem um teste-canário que a faça falhar de propósito.
  6. `multilingual-e5-base` exige os prefixos `query:` / `passage:`.
- Base de origem do programa maior: `suporte-sh3-hub/docs/modulo-conhecimento.md` (§14, D5, e o
  vocabulário de visibilidade da §8).

---

## Deferred Ideas

- **Conector para a tabela `conhecimento_artigos` do Hub** — pertence ao `sh3-conhecimento`.
- **Eixo `sistema × visibilidade` em vez de `tenant_id`** — a generalização do predicado RLS. O
  desenho aqui deve permitir, mas implementar é do serviço interno.
- **Tela de busca no painel de suporte** — o primeiro corte é só MCP; a tela só se justifica depois
  de a qualidade estar medida pela tabela de ablação.
- **Camada de geração com resposta em linguagem natural** — traz chave de API, custo por pergunta e
  o problema de resposta errada com aparência de certeza. Decisão separada.
- **Registrar a AD que separa o `sh3-conhecimento` do Hub** — `modulo-conhecimento.md` a chama de
  "AD-016", mas esse número já é o de `/autarquias` no `STATE.md` do Hub. Precisa de número próprio
  quando for aprovada. Não é deste repositório, mas se perde se não ficar anotado.
