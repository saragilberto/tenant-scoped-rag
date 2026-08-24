# RAG com Escopo de Tenant Specification

**Status:** confirmada em 2026-08-20 (sign-off em bloco das premissas apresentadas)
**Data:** 2026-08-20
**Origem:** artefato "RAG com escopo de tenant" (20/08/2026), revisado — ver `context.md` §Specific References
**Escopo avaliado:** Complex (domínio novo, decisão de segurança no centro)

## Problem Statement

Existem milhares de repositórios chamados `rag-example`: ingestão, embedding, top-k, resposta. Nenhum
deles prova nada, porque qualquer pessoa com um fim de semana faz igual. O que ninguém constrói é
recuperação em que a permissão de quem pergunta faz parte da consulta, e não de um filtro aplicado
depois — e é exatamente essa a parte que o `sh3-conhecimento` vai precisar quando existir, sobre dado
real de cliente. Este repositório é o laboratório dessa decisão: dois tenants na mesma base vetorial,
nenhuma consulta de um alcançando chunk do outro, provado por teste em CI e não por afirmação no README.

## Goals

- [ ] Zero chunk de um tenant retornado a uma consulta feita sob a identidade do outro, em 100% das
      360 consultas cruzadas geradas pelo golden set (60 perguntas × 3 modos × 2 perfis de chunk) — com o isolamento garantido pelo PostgreSQL (RLS)
      e não pelo código da aplicação
- [ ] Um teste-canário que, ao remover a política RLS, faz a suíte de isolamento falhar — provando que
      a suíte consegue detectar vazamento
- [ ] `recall@5` publicado no README para cada uma das configurações do estudo de ablação, calculado
      sem nenhuma chamada a serviço externo
- [ ] Quem clonar o repositório consulta a base pelo Claude Desktop em menos de dez minutos, sem chave
      de API e sem conta em serviço nenhum

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Geração de resposta / qualquer chamada a LLM | Decisão de consumo: o cliente MCP gera, o servidor recupera. Mantém o servidor testável sem LLM e sem custo por pergunta |
| RAGAS e métricas com LLM-juiz | Exigem chave de API, contradizendo o "clone e rode"; e `faithfulness` não se aplica a servidor que não gera resposta |
| Qualquer dado real da SH3, de cliente ou de produto | Repositório público; o corpus é inventado e versionado aqui |
| Conector para a tabela `conhecimento_artigos` do Hub | Pertence ao `sh3-conhecimento` — este repo é o ensaio técnico, não o serviço |
| Eixo `sistema × visibilidade` no lugar de `tenant_id` | O desenho do predicado RLS deve permitir a troca; implementá-la é do serviço interno |
| Vetorização dos bancos de produto via `sh3-mcp-server` | Dado operacional com CPF e e-mail é consulta com SQL, não recuperação; embeddar sairia do isolamento por schema |
| Transporte HTTP/SSE e multiusuário por requisição | `stdio` cobre Claude Desktop e Claude Code sem infraestrutura; a identidade é por instância de servidor |
| Interface web ou página de busca | O primeiro corte é consumido só por MCP |
| Atualização incremental do índice, watch de arquivos | A reingestão idempotente cobre o caso de um corpus versionado no repositório |
| Rate limiting, quotas, autenticação de usuário | Servidor local monousuário, iniciado pelo próprio cliente MCP |
| Treinar ou ajustar modelo de embedding ou de reranking | Só modelos prontos; o objeto do estudo é a arquitetura de recuperação, não o modelo |

---

## Assumptions & Open Questions

Toda ambiguidade está resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Entrada da identidade do tenant | Variável de ambiente por instância do servidor; nenhuma tool aceita `tenant_id` | Decidido na discussão. O cliente não tem como forjar o que nunca envia | y |
| Quem garante o isolamento | RLS no PostgreSQL ancorada em `current_setting('app.tenant_id')`, aplicada via `SET LOCAL` na conexão | Decidido na discussão. A afirmação do README passa a ser "o banco recusa", não "meus WHEREs estão corretos" | y |
| Papel de banco usado pelo servidor | Papel sem `BYPASSRLS` e sem `SUPERUSER`, distinto do dono das tabelas | Dono de tabela ignora RLS por padrão; sem papel separado a política não vale nada | y |
| Domínio do corpus | Bases de suporte de dois SaaS fictícios, artigos com categoria, versão e visibilidade | Decidido na discussão. Legível em inglês sem contexto prévio, e ensaia o formato do `sh3-conhecimento` | y |
| Nomes dos tenants fictícios | `meridian` (CRM) e `halcyon` (faturamento) | Nomes neutros, sem colisão com produto real; a critério do agente conforme `context.md` | y |
| Sobreposição temática do corpus | Ao menos 8 assuntos presentes nas duas bases com procedimento diferente (erro de login, importação de CSV, 2FA, limites de API, exportação de fatura, webhooks, SSO, retenção de logs) | Sem sobreposição o teste de isolamento é vacuoso: a busca de um tenant nunca chegaria perto do outro por acaso | y |
| Superfície do `explain_retrieval` | Só candidatos do escopo; nenhuma contagem ou indício do que foi descartado por escopo | Decidido na discussão. Contagem agregada vaza cardinalidade e permite inferir assunto sem ler chunk | y |
| Tamanho e forma do golden set | 30 perguntas por tenant, escritas à mão, com chunks relevantes anotados; cada pergunta roda também contra a identidade do outro tenant com resultado esperado vazio | Decidido na discussão. 60 perguntas × 3 modos × 2 perfis = 360 consultas de isolamento sem escrever pergunta nova | y |
| Métricas | recall@k, precision@k, MRR e nDCG@10, determinísticas | Reprodutíveis por qualquer pessoa que clonar, sem chave de API — é o que faz a tabela de ablação valer como evidência pública | y |
| Manchete do README | `recall@5` por configuração + zero vazamento em 360 consultas cruzadas | Dois números, um de qualidade e um de segurança; é o que o leitor decide em dez segundos | y |
| Busca léxica | `ts_rank_cd` sobre coluna `tsvector` gerada, dicionário `english` + `unaccent` | PostgreSQL **não tem BM25** — o ranking nativo é tf-idf com normalização por tamanho. Chamar de BM25 seria erro factual no README | y |
| Fusão híbrida | Reciprocal Rank Fusion com k=60 | RRF combina posições, não notas — resolve a incompatibilidade de escala entre cosseno e `ts_rank_cd` sem normalização arbitrária | y |
| Mitigação da filtragem sobre índice ANN | `hnsw.iterative_scan = strict_order` (pgvector ≥ 0.8), com teste que compara a recall da busca com escopo contra a mesma busca em base de tenant único | O predicado de RLS não é *leakproof* e portanto não desce para dentro da varredura do índice: sem mitigação a busca pode devolver menos que `top_k`. Índice parcial por tenant fica como plano B se a recall medida não fechar | y |
| Modelo de embedding | `multilingual-e5-base` local, 768 dimensões, com prefixos `query:` e `passage:` | Roda sem chave de API; os prefixos são exigência do modelo e omiti-los custa recall medível | y |
| Chunking | Por fronteira de seção quando o documento tem títulos markdown; tamanho fixo com 15% de overlap quando não tem | Estrutura quando existe, overlap quando não existe — "overlap é obsoleto" é forte demais, o correto é "prefira estrutura" | y |
| Tamanhos de chunk do estudo de ablação | 512 e 1024 tokens | Dois pontos bastam para mostrar direção sem multiplicar o custo da tabela | y |
| Reranking | `bge-reranker-v2-m3`, atrás de flag, desligado por padrão | Só sob flag o estudo consegue medir o que ele acrescenta de fato | y |
| Linguagem e runtime | Python 3.12 gerenciado por `uv` | O Python do sistema é 3.9.6; `uv` não está instalado e entra como pré-requisito documentado | y |
| Banco | PostgreSQL 17 + pgvector 0.8.1, por Docker Compose no próprio repositório | Não há PostgreSQL local nesta máquina; Docker está disponível. 0.8.1 é a versão corrente (mai/2026), compatível com PG 12–17, e o `iterative_scan` exige ≥ 0.8 | y |
| SDK de MCP | Pacote oficial `mcp` v2, classe `MCPServer` importada de `mcp.server`, Python ≥ 3.10 | `FastMCP` **não existe mais com esse nome** na v2 do SDK — o artefato de origem e a aula ainda falam em FastMCP. Publicar isso no README seria documentar API inexistente | y |
| Transporte MCP | `stdio` | É o que Claude Desktop e Claude Code consomem sem infraestrutura; premissa assumida e não questionada na discussão | y |
| Idempotência da ingestão | Chave `(tenant_id, origem, hash_do_conteudo)`; reingestão sem alteração não altera contagens | Rodar duas vezes duplicando a base invalidaria toda métrica publicada | y |
| CI | GitHub Actions com PostgreSQL como service container; a suíte de isolamento é gate obrigatório | O README afirma zero vazamento — a afirmação precisa de execução automática, não de captura de tela | y |
| Conta e identidade do git | Repositório na conta pessoal `saragilberto`, com `git config user.email` **local** apontando para o `noreply` pessoal | Verificado nesta máquina: o `user.email` global é `168448310+saracristina-sh3@users.noreply.github.com`. Commitar sem sobrescrever localmente atribui todo commit à conta de trabalho e expõe o nome da empresa no histórico | y |
| Idioma | Código, README e mensagens de commit em inglês; `.specs/` em português | O README é o entregável público e o público-alvo é internacional; o planejamento é ferramenta de trabalho pessoal | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## Cobertura das dimensões implícitas

Escopo Complex: cada dimensão resolve em requisito ou em `N/A` justificado.

| Dimensão | Resolução |
| -------- | --------- |
| Validação de entrada e limites | RAG-11, RAG-12, RAG-13 (`top_k` 1–50, consulta não vazia, `mode` fechado em três valores) |
| Falha e falha parcial | RAG-05 (arquivo do corpus que falha não aborta a ingestão), RAG-22 (banco inacessível não derruba o servidor) |
| Idempotência / retry / duplicata | RAG-02 (reingestão não altera contagens) |
| Fronteiras de autorização e limites de taxa | RAG-14 a RAG-20 (RLS, escopo não desligável, falha ao iniciar sem tenant). Limite de taxa: **N/A porque** o servidor é local, monousuário e iniciado pelo próprio cliente MCP |
| Concorrência e ordenação | **N/A porque** o servidor é exclusivamente de leitura e a ingestão é um comando de execução única e offline; duas instâncias lendo a mesma base não disputam estado |
| Ciclo de vida e expiração do dado | **N/A porque** o corpus é versionado no repositório e a reingestão idempotente (RAG-02) é o único caminho de atualização; não há retenção nem expurgo a definir |
| Observabilidade | RAG-27 (`explain_retrieval` como instrumento de diagnóstico), RAG-05 (relatório de falhas da ingestão) |
| Falha de dependência externa | RAG-22 (banco), RAG-34 (modelo de reranking ausente sob flag ativa) |
| Integridade de transição de estado | **N/A porque** não há máquina de estados: documento é ingerido ou não é, e não existe fluxo de aprovação, publicação ou arquivamento neste escopo |

---

## User Stories

### P1: Ingerir o corpus com um comando ⭐ MVP

**User Story**: Como pessoa que acabou de clonar o repositório, quero carregar o corpus inteiro com um comando, para poder consultar a base sem montar nada à mão.

**Why P1**: Sem base carregada não existe busca, isolamento nem métrica — é o pré-requisito de todo o resto.

**Acceptance Criteria**:

1. **RAG-01** — WHEN `ingest corpus/` é executado sobre uma base vazia THEN o sistema SHALL gravar cada documento com `tenant_id`, origem, versão e o texto original íntegro, e cada chunk com seu vetor de 768 dimensões e sua coluna `tsvector`
2. **RAG-02** — WHEN `ingest corpus/` é executado uma segunda vez sem alteração nos arquivos THEN o sistema SHALL terminar com as contagens de documentos e de chunks idênticas às da primeira execução
3. **RAG-03** — WHEN um documento do corpus contém títulos markdown THEN o sistema SHALL dividir os chunks nas fronteiras de seção, sem overlap
4. **RAG-04** — IF um documento do corpus não contém nenhum título markdown THEN o sistema SHALL dividi-lo em chunks de tamanho fixo com 15% de overlap
5. **RAG-05** — IF um arquivo do corpus falha ao ser processado THEN o sistema SHALL registrar caminho e causa, prosseguir com os demais arquivos e terminar com código de saída diferente de zero
6. **RAG-06** — WHEN um chunk é enviado ao modelo de embedding durante a ingestão THEN o sistema SHALL prefixar o texto com `passage: `

**Independent Test**: subir o banco por Docker Compose, rodar `ingest corpus/` duas vezes e conferir que a segunda execução não muda nenhuma contagem.

---

### P1: Buscar nos três modos ⭐ MVP

**User Story**: Como agente conectado ao servidor, quero escolher entre busca semântica, léxica e híbrida, para comparar o que cada uma encontra na mesma pergunta.

**Why P1**: Expor os três modos é o que torna o estudo de ablação possível — e a ablação é o entregável público do projeto.

**Acceptance Criteria**:

1. **RAG-07** — WHEN `search` é chamada com `mode="semantic"` THEN o sistema SHALL prefixar a consulta com `query: ` antes de gerar o vetor e SHALL ordenar por distância de cosseno
2. **RAG-08** — WHEN `search` é chamada com `mode="lexical"` THEN o sistema SHALL ordenar por `ts_rank_cd` sobre a coluna `tsvector`, com dicionário `english` e `unaccent`
3. **RAG-09** — WHEN `search` é chamada com `mode="hybrid"` THEN o sistema SHALL fundir os rankings semântico e léxico por Reciprocal Rank Fusion com k=60, combinando posições e nunca somando os scores brutos das duas escalas
4. **RAG-10** — WHEN `search` é executada com escopo ativo e existem ao menos `top_k` chunks no escopo que satisfazem a consulta THEN o sistema SHALL retornar exatamente `top_k` resultados
5. **RAG-11** — IF `top_k` está fora do intervalo de 1 a 50 THEN o sistema SHALL rejeitar a chamada com erro de validação, sem executar consulta no banco
6. **RAG-12** — IF `query` é vazia ou contém apenas espaços THEN o sistema SHALL rejeitar a chamada com erro de validação
7. **RAG-13** — The system SHALL aceitar em `mode` exclusivamente os valores `semantic`, `lexical` e `hybrid`, rejeitando qualquer outro com erro de validação

**Independent Test**: a mesma pergunta nos três modos devolve três ordenações e, no modo híbrido, um documento fora do top-3 de ambos os rankings isolados pode aparecer no top-3 fundido.

---

### P1: Isolamento garantido pelo banco ⭐ MVP

**User Story**: Como pessoa avaliando o repositório, quero que o isolamento entre tenants seja imposto pelo PostgreSQL e demonstrado por teste, para não ter que acreditar na palavra do README.

**Why P1**: É a tese do projeto. Sem isso, o repositório é mais um `rag-example`.

**Acceptance Criteria**:

1. **RAG-14** — The system SHALL manter política RLS de leitura habilitada em toda tabela que contenha texto, metadado ou vetor do corpus, ancorada em `current_setting('app.tenant_id')`
2. **RAG-15** — WHEN o servidor abre conexão com o banco THEN o sistema SHALL aplicar `SET LOCAL app.tenant_id` com o valor da variável de ambiente e SHALL usar papel de banco sem `BYPASSRLS` e que não é dono das tabelas
3. **RAG-16** — The system SHALL não expor, em nenhuma das quatro tools, parâmetro capaz de alterar, ampliar ou desligar o escopo ativo
4. **RAG-17** — IF a variável de ambiente que define o tenant está ausente, vazia ou não corresponde a um tenant existente THEN o servidor SHALL encerrar na inicialização com mensagem explícita, sem anunciar nenhuma tool
5. **RAG-18** — WHEN cada uma das 30 perguntas do golden set de um tenant é executada sob a identidade do outro THEN o sistema SHALL retornar zero chunk pertencente ao tenant de origem da pergunta
6. **RAG-19** — WHILE a política RLS está removida em ambiente de teste dedicado a suíte de isolamento SHALL falhar
7. **RAG-20** — IF o texto da consulta contém instrução que tenta alterar o escopo THEN o sistema SHALL tratá-lo como texto de busca comum, sem qualquer efeito sobre o escopo ativo

**Independent Test**: subir duas instâncias do servidor contra o mesmo banco, uma por tenant, e rodar a suíte cruzada; depois derrubar a política RLS e confirmar que a mesma suíte fica vermelha.

---

### P1: Servidor MCP conectável ⭐ MVP

**User Story**: Como pessoa que clonou o repositório, quero conectar o servidor ao Claude Desktop ou ao Claude Code e conversar com a base, para ver a coisa funcionando antes de ler qualquer código.

**Why P1**: É o que transforma o repositório em demonstração em vez de biblioteca.

**Acceptance Criteria**:

1. **RAG-21** — WHEN um cliente MCP realiza o handshake por `stdio` THEN o servidor SHALL anunciar as tools `search`, `get_document`, `list_sources` e `explain_retrieval` com seus esquemas de parâmetros
2. **RAG-22** — IF o banco está inacessível no momento de uma chamada de tool THEN o servidor SHALL devolver erro identificando a falha de conexão e SHALL permanecer em execução
3. **RAG-23** — The system SHALL ser iniciável pelo cliente MCP com um único comando declarado na configuração, sem etapa manual além de subir o banco e executar a ingestão

**Independent Test**: colar a configuração do README no Claude Desktop, reiniciar e fazer uma pergunta que devolva trecho do corpus.

---

### P2: Auditar de onde veio o resultado

**User Story**: Como pessoa depurando uma resposta ruim, quero ver o documento original e o porquê de cada candidato ter entrado ou saído, para descobrir se o erro é da recuperação ou da geração.

**Why P2**: Não é necessário para a tese do isolamento, mas é o que separa engenharia de caixa-preta — e é o material do texto público.

**Acceptance Criteria**:

1. **RAG-24** — WHEN `get_document` é chamada com um `doc_id` do escopo ativo THEN o sistema SHALL devolver o texto original completo do documento e seus metadados
2. **RAG-25** — IF `get_document` é chamada com `doc_id` fora do escopo ativo ou inexistente THEN o sistema SHALL devolver resposta de não encontrado indistinguível entre os dois casos
3. **RAG-26** — WHEN `list_sources` é chamada THEN o sistema SHALL listar exclusivamente os documentos do escopo ativo, com a contagem de chunks de cada um
4. **RAG-27** — WHEN `explain_retrieval` é chamada THEN o sistema SHALL devolver, para cada candidato do escopo, o score em cada ranking, a posição em cada ranking, o score fundido e o motivo do corte
5. **RAG-28** — The system SHALL omitir de `explain_retrieval` qualquer contagem, identificador ou indício de existência de candidato fora do escopo ativo

**Independent Test**: `explain_retrieval` sobre uma pergunta cujo assunto existe nos dois tenants devolve apenas candidatos do escopo ativo, sem nenhum número que denuncie o outro.

---

### P2: Tabela de ablação reprodutível

**User Story**: Como leitor do README, quero ver números medidos comparando as configurações de busca, para julgar se quem escreveu sabe do que fala.

**Why P2**: É o entregável público e o material do primeiro texto em inglês, mas depende de tudo acima estar funcionando.

**Acceptance Criteria**:

1. **RAG-29** — WHEN o harness de avaliação é executado THEN o sistema SHALL calcular recall@k, precision@k, MRR e nDCG@10 a partir do golden set sem realizar nenhuma chamada a serviço externo
2. **RAG-30** — WHEN o estudo de ablação é executado THEN o sistema SHALL medir cada modo de busca isolado, com e sem reranking, nos tamanhos de chunk de 512 e 1024 tokens, e SHALL emitir o resultado como tabela markdown
3. **RAG-31** — The system SHALL manter o golden set versionado no repositório em formato de texto legível e editável à mão

**Independent Test**: rodar o harness duas vezes sobre a mesma base produz números idênticos.

---

### P3: Reranking opcional

**User Story**: Como pessoa conduzindo o estudo, quero ligar e desligar o reranking, para medir o que ele acrescenta de fato em vez de assumir que melhora.

**Why P3**: O projeto entrega valor sem ele; sua função é ser mais uma linha da tabela de ablação.

**Acceptance Criteria**:

1. **RAG-32** — WHERE a flag de reranking está ativa THEN o sistema SHALL reordenar os candidatos com `bge-reranker-v2-m3` antes de aplicar o corte em `top_k`
2. **RAG-33** — The system SHALL manter o reranking desligado por padrão
3. **RAG-34** — WHERE a flag de reranking está ativa e o modelo não está disponível localmente THEN o sistema SHALL falhar com mensagem explícita, sem devolver silenciosamente a ordem não reordenada

**Independent Test**: a mesma consulta com e sem a flag produz ordenações diferentes, e a tabela de ablação ganha a linha correspondente.

---

## Edge Cases

- IF a consulta não casa com nenhum chunk do escopo THEN o sistema SHALL devolver lista vazia, nunca erro nem o chunk menos ruim
- IF o corpus de um tenant está vazio no momento da consulta THEN o sistema SHALL devolver lista vazia sem revelar que o outro tenant tem conteúdo
- IF a consulta excede 2.000 caracteres THEN o sistema SHALL rejeitá-la com erro de validação antes de gerar embedding
- WHEN um documento do corpus é maior que o limite de um único chunk e não tem títulos THEN o sistema SHALL produzir múltiplos chunks contíguos com overlap, sem perder texto nas fronteiras
- IF o modelo de embedding não está em cache local na primeira execução THEN o sistema SHALL baixá-lo informando o progresso, e SHALL falhar com mensagem explícita se não houver rede

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| RAG-01 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-02 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-03 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-04 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-05 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-06 | P1: Ingerir o corpus | Design | In Tasks |
| RAG-07 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-08 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-09 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-10 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-11 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-12 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-13 | P1: Buscar nos três modos | Design | In Tasks |
| RAG-14 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-15 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-16 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-17 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-18 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-19 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-20 | P1: Isolamento garantido pelo banco | Design | In Tasks |
| RAG-21 | P1: Servidor MCP conectável | Design | In Tasks |
| RAG-22 | P1: Servidor MCP conectável | Design | In Tasks |
| RAG-23 | P1: Servidor MCP conectável | Design | In Tasks |
| RAG-24 | P2: Auditar de onde veio o resultado | Design | In Tasks |
| RAG-25 | P2: Auditar de onde veio o resultado | Design | In Tasks |
| RAG-26 | P2: Auditar de onde veio o resultado | Design | In Tasks |
| RAG-27 | P2: Auditar de onde veio o resultado | Design | In Tasks |
| RAG-28 | P2: Auditar de onde veio o resultado | Design | In Tasks |
| RAG-29 | P2: Tabela de ablação reprodutível | Design | In Tasks |
| RAG-30 | P2: Tabela de ablação reprodutível | Design | In Tasks |
| RAG-31 | P2: Tabela de ablação reprodutível | Design | In Tasks |
| RAG-32 | P3: Reranking opcional | T21 | Done |
| RAG-33 | P3: Reranking opcional | T21 | Done |
| RAG-34 | P3: Reranking opcional | T21 | Done |

**ID format:** `RAG-[NÚMERO]`

**Coverage:** 34 total, 34 mapeados a tasks (T1–T32), 0 não mapeados ✅

---

## Success Criteria

- [ ] A suíte de isolamento roda em GitHub Actions e cobre 360 consultas cruzadas com zero vazamento
- [ ] O teste-canário derruba a suíte de isolamento ao remover a RLS — provando que ela detecta vazamento
- [ ] A busca com escopo devolve `top_k` completo sempre que há `top_k` chunks no escopo, com a recall medida contra base de tenant único
- [ ] O README publica `recall@5` para cada configuração de busca, reprodutível por `git clone` sem chave de API
- [ ] Um estranho conecta o servidor ao Claude Desktop e obtém trecho do corpus em menos de dez minutos
- [ ] Nenhum commit do repositório está atribuído à conta de trabalho
