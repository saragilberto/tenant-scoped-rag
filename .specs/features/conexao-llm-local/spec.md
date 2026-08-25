# Conexão com LLM Local Specification

**Status:** confirmada em 2026-08-24
**Data:** 2026-08-24
**Origem:** discussão nesta sessão (duas rodadas, ver `context.md`)
**Escopo avaliado:** Complex (reabre um limite de arquitetura já registrado — RAG-16/AD-003 — e
integra uma dependência externa nova)

## Problem Statement

O servidor MCP deste repositório é, por decisão deliberada, só de recuperação: "o servidor recupera,
o cliente gera" (RAG-16/AD-003). Isso deixou a geração de resposta em `Deferred Ideas` da feature
anterior, bloqueada por chave de API e custo por pergunta. Agora existe um LLM rodando localmente
via `llamafile` (`/Volumes/LocalAgent`), sem chave de API e sem custo por pergunta, com sua própria
interface de chat no navegador — o bloqueio que adiou a geração não existe mais. Falta a peça que
liga as duas partes: pegar a pergunta da pessoa, recuperar o contexto certo do tenant ativo, e
entregar esse contexto pronto para uso no chat que o llamafile já serve, sem tocar no contrato do
servidor MCP.

## Goals

- [ ] Uma pergunta roda por um comando novo, recupera o contexto do tenant ativo (mesmo mecanismo de
      identidade e busca do servidor MCP) e entrega um bloco pronto para colar no chat do llamafile,
      sem nenhuma chamada deste repositório ao endpoint de geração do LLM
- [ ] O contrato das quatro tools do servidor MCP (`search`, `get_document`, `list_sources`,
      `explain_retrieval`) permanece idêntico — nenhuma tool nova, nenhuma mudança de assinatura
- [ ] Ausência ou indisponibilidade do LLM local nunca impede a entrega do contexto — a checagem de
      saúde é um aviso, não um bloqueio

## Out of Scope

Explicitamente excluído. Documentado para evitar scope creep.

| Feature | Reason |
| ------- | ------ |
| Chamada ao endpoint de chat completion do llamafile a partir do Python | Decisão desta rodada: quem gera é a pessoa, pelo chat do navegador. Automatizar a chamada é outra decisão, que reabriria RAG-16/AD-003 |
| Nova tool de geração no servidor MCP (ex.: `ask`) | Mantém RAG-16/AD-003 intactos; decisão explicitamente descartada nesta discussão |
| LLM local como juiz de avaliação (métricas estilo RAGAS no harness) | Reabre a exclusão da AD-004 por um motivo diferente (custo de API); decisão separada, registrada em Deferred Ideas |
| Gerenciar o processo do llamafile (iniciar, parar, monitorar saúde contínua) | O binário e o modelo vivem em `/Volumes/LocalAgent`, volume externo ao repositório; a pessoa inicia o servidor manualmente, como já acontece com o Postgres via Docker Compose |
| Chat interativo com histórico de turnos no terminal | Opção descartada explicitamente na discussão em favor da interface web do próprio llamafile |
| Injeção automática do contexto na página do navegador (DOM, automação, parâmetro de URL) | Não verificado se o llamafile expõe um mecanismo oficial; mecanismo de entrega desta rodada é área de transferência + stdout (ver Assumptions) |
| Multi-tenant simultâneo no mesmo comando | Reaproveita a mesma restrição do servidor MCP: uma execução, um `RAG_TENANT_ID` |
| Autenticação, rate limiting no comando novo | Ferramenta local de linha de comando, monousuário, mesma justificativa já usada para o servidor MCP |

---

## Assumptions & Open Questions

Toda ambiguidade está resolvida ou registrada aqui — nada fica silenciosamente indefinido.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Endpoint HTTP do LLM local | `http://127.0.0.1:8080`, configurável via `LOCAL_LLM_BASE_URL` | Confirmado na fase de Design: subimos `Qwen3.5-0.8B-Q8_0.llamafile --server --host 127.0.0.1 --port 8080` nesta máquina e o servidor respondeu em `127.0.0.1:8080`, sem exigir chave de API | y |
| Caminho da checagem de saúde | `GET {base_url}/v1/models`; tratar qualquer erro de conexão, timeout ou status não-200 como "indisponível" | Confirmado na fase de Design: retornou HTTP 200 com metadados do modelo, incluindo `meta.n_ctx` (janela de contexto), que o Design reaproveita para avisar sobre bloco de contexto grande demais (ver `design.md` — Risks & Concerns) | y |
| Timeout da checagem de saúde | 2 segundos | Rápido o bastante para não atrasar a entrega do contexto quando o LLM está fora do ar, generoso o bastante para uma chamada local | y (default do agente, sem objeção levantada) |
| LLM local indisponível | Aviso, nunca bloqueio — o bloco de contexto é entregue de qualquer forma (stdout + área de transferência) | A recuperação não depende do LLM estar de pé; bloquear a entrega do contexto obrigaria a pessoa a rodar o comando de novo depois de abrir o llamafile | y |
| Mecanismo de entrega do contexto | Copiar para a área de transferência do sistema operacional e sempre também imprimir em stdout | Funciona sem depender de nenhum detalhe interno, documentado ou não, da UI do llamafile; stdout garante visibilidade mesmo sem acesso à área de transferência (ambiente headless, SSH) | y |
| Identidade do tenant | Reaproveita `RAG_TENANT_ID` e `resolve_tenant_from_env()`, sem mecanismo novo | Mesma fronteira de identidade do servidor MCP (RAG-16/AD-003); inventar um segundo mecanismo duplicaria a superfície de risco que a feature anterior resolveu | y |
| Modo e `top_k` padrão da recuperação | `hybrid`, `top_k=5`, perfil `P512` | Mesmos padrões da tool `search` do servidor MCP — consistência de comportamento entre os dois pontos de entrada | y |
| Formato do bloco de contexto | Pergunta + cada chunk citado por `document_id` e posição + instrução de responder só com base no conteúdo apresentado | Formato mínimo de prompt fundamentado (grounded), sem inventar um template de citação mais elaborado sem pedido explícito | y |
| Nome e flags do comando | `rag-context "<pergunta>"`, com `--mode`, `--top-k`, `--profile`, `--open` | Segue a convenção de scripts já registrada em `pyproject.toml` (`ingest`, `rag-server`, `rag-eval`) | y |
| Falha ao copiar para a área de transferência | Não falha o comando; a impressão em stdout já cobre o caso | Ambientes sem utilitário de clipboard (CI, containers) não devem impedir o uso do comando | y |
| Zero chunks retornados | Avisar que nada foi encontrado; não copiar nem imprimir um bloco de prompt vazio | Copiar um bloco vazio para a área de transferência seria pior que avisar — a pessoa perguntaria sem perceber que não há contexto | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Contexto pronto para o chat do LLM local ⭐ MVP

**User Story**: Como pessoa usando o laboratório localmente, quero rodar um comando que recupera o
contexto relevante da minha pergunta, escopado ao tenant ativo, e entrega esse contexto pronto para
colar no chat do llamafile, para obter uma resposta fundamentada no meu corpus sem escrever nenhuma
integração de LLM.

**Why P1**: É a peça que faltava depois da feature de recuperação — sem ela, "conectar o RAG a um
LLM local" não existe, só a recuperação isolada e o LLM isolado.

**Acceptance Criteria**:

1. WHEN a pessoa roda `rag-context "<pergunta>"` com `RAG_TENANT_ID` definido para um tenant
   conhecido THEN o sistema SHALL recuperar os 5 chunks de maior posição em modo `hybrid` do perfil
   `P512` para essa pergunta, usando a mesma `scoped_connection` do servidor MCP.
2. WHEN a recuperação retorna ao menos um chunk THEN o sistema SHALL montar um único bloco de texto
   contendo a pergunta, cada chunk recuperado identificado por `document_id` e posição, e uma
   instrução para responder somente com base nesse conteúdo.
3. WHEN o bloco de contexto é montado THEN o sistema SHALL copiá-lo para a área de transferência do
   sistema operacional e SHALL também imprimi-lo em stdout.
4. WHEN o comando roda THEN o sistema SHALL, antes de terminar, tentar uma checagem de saúde no
   endpoint HTTP do LLM local (`LOCAL_LLM_BASE_URL`, padrão `http://127.0.0.1:8080`) com timeout de
   2 segundos.
5. IF a checagem de saúde do LLM local falhar ou expirar THEN o sistema SHALL imprimir um aviso
   citando o endpoint configurado e a sugestão de iniciar o llamafile, e SHALL entregar o bloco de
   contexto normalmente (stdout + área de transferência).
6. IF `RAG_TENANT_ID` não está definido ou não corresponde a um tenant conhecido THEN o sistema
   SHALL falhar com a mesma mensagem que `resolve_tenant_from_env()` já produz, sem tentar a
   checagem de saúde do LLM local nem a recuperação.
7. IF a pergunta está vazia ou excede o limite de caracteres já usado pelo servidor MCP
   (`_MAX_QUERY_CHARS`) THEN o sistema SHALL rejeitar com uma mensagem que nomeia o limite, sem
   chegar a consultar o banco.
8. IF a busca retorna zero chunks THEN o sistema SHALL informar que nenhum contexto foi encontrado e
   SHALL não copiar nem imprimir um bloco de prompt vazio.
9. IF o banco de dados está inacessível THEN o sistema SHALL falhar com uma mensagem clara,
   reaproveitando o mesmo tratamento de erro de conexão já usado pela tool `search` do servidor MCP.
10. IF a área de transferência do sistema operacional não está disponível THEN o sistema SHALL não
    falhar o comando — a impressão em stdout do critério 3 já cobre o caso.

**Independent Test**: com o Postgres do repositório de pé e `RAG_TENANT_ID` definido, rodar
`rag-context "pergunta do golden set"` e verificar que o bloco impresso em stdout contém a pergunta e
os chunks esperados, e que a área de transferência contém o mesmo conteúdo — sem que o llamafile
precise estar rodando.

---

### P2: Escolher modo, `top_k` e perfil de chunk

**User Story**: Como pessoa usando o comando, quero escolher o modo de busca, quantos chunks trazer
e o perfil de chunking, para comparar o que cada configuração entrega ao LLM local.

**Why P2**: Não é necessário para a primeira pergunta funcionar, mas espelha os mesmos parâmetros já
expostos pela tool `search` do servidor MCP — sem isso o comando novo seria menos flexível que o que
já existe.

**Acceptance Criteria**:

1. WHEN a pessoa passa `--mode semantic|lexical|hybrid` THEN o sistema SHALL usar esse modo no lugar
   do padrão `hybrid`.
2. WHEN a pessoa passa `--top-k N` com N entre 1 e 50 THEN o sistema SHALL recuperar N chunks.
3. IF `--top-k` estiver fora do intervalo 1–50 THEN o sistema SHALL rejeitar com a mesma mensagem já
   usada pela validação de `top_k` do servidor MCP.
4. WHEN a pessoa passa `--profile P512|P1024` THEN o sistema SHALL usar esse perfil de chunk na
   recuperação.

**Independent Test**: rodar o mesmo comando com `--mode lexical --top-k 3 --profile P1024` e
verificar que o bloco de contexto reflete exatamente esses três parâmetros.

---

### P3: Abrir o chat do llamafile automaticamente

**User Story**: Como pessoa usando o comando, quero uma flag que abra o navegador na página do
llamafile depois de preparar o contexto, para economizar o passo manual de trocar de janela.

**Why P3**: Conveniência pura — o fluxo funciona sem isso (P1 já entrega o contexto pronto), então
fica de fora do MVP.

**Acceptance Criteria**:

1. WHEN a pessoa passa `--open` THEN o sistema SHALL abrir, no navegador padrão do sistema, a URL
   base configurada do LLM local, depois de copiar o bloco de contexto para a área de transferência.
2. IF o comando de abrir o navegador falhar THEN o sistema SHALL registrar um aviso e SHALL continuar
   sem abortar a entrega do contexto.

---

## Edge Cases

- IF `LOCAL_LLM_BASE_URL` está definido com um valor que não é uma URL http(s) válida THEN o sistema
  SHALL rejeitar antes de tentar a checagem de saúde, citando o valor recebido.
- WHEN a pergunta contém apenas espaços em branco THEN o sistema SHALL tratá-la como vazia (mesma
  regra de `_validate_query`).
- IF dois chunks recuperados pertencem ao mesmo `document_id` THEN o sistema SHALL listar os dois no
  bloco de contexto, cada um com sua própria posição — sem deduplicar por documento.

---

## Cobertura das dimensões implícitas

Escopo Complex: cada dimensão resolve em requisito ou em `N/A` justificado.

| Dimensão | Resolução |
| -------- | --------- |
| Validação de entrada e limites | LLM-06, LLM-07 (query vazia/limite), LLM-12/LLM-13 (`top_k` 1–50) |
| Falha e falha parcial | LLM-05 (LLM local fora do ar não bloqueia), LLM-09 (banco inacessível falha com mensagem clara), LLM-10 (clipboard indisponível não falha o comando) |
| Idempotência / retry / duplicata | **N/A porque** o comando é de leitura pura, sem efeito colateral persistente — rodar duas vezes com a mesma pergunta produz o mesmo bloco |
| Fronteiras de autorização e limites de taxa | LLM-01 reaproveita `RAG_TENANT_ID` e `resolve_tenant_from_env()`. Rate limiting: **N/A porque** é ferramenta local monousuário, mesma justificativa do servidor MCP |
| Concorrência e ordenação | **N/A porque** é execução única de comando, sem estado compartilhado entre execuções |
| Ciclo de vida e expiração do dado | **N/A porque** nada é persistido por este comando; o bloco de contexto vive só na área de transferência e no stdout daquela execução |
| Observabilidade | LLM-05 (aviso nomeando endpoint e porta quando o LLM local não responde) |
| Falha de dependência externa | LLM-05 (LLM local), LLM-09 (banco) |
| Integridade de transição de estado | **N/A porque** não há máquina de estados — é uma execução única, sem fluxo de aprovação ou publicação |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --------------- | ----- | ----- | ------ |
| LLM-01 | P1: Contexto pronto para o chat do LLM local | Tasks | Implementing |
| LLM-02 | P1 | Design | Pending |
| LLM-03 | P1 | Design | Pending |
| LLM-04 | P1 | Tasks | Implementing |
| LLM-05 | P1 | Tasks | Implementing |
| LLM-06 | P1 | Tasks | Implementing |
| LLM-07 | P1 | Tasks | Implementing |
| LLM-08 | P1 | Design | Pending |
| LLM-09 | P1 | Design | Pending |
| LLM-10 | P1 | Design | Pending |
| LLM-11 | P2: Escolher modo, top_k e perfil | Design | Pending |
| LLM-12 | P2 | Tasks | Implementing |
| LLM-13 | P2 | Tasks | Implementing |
| LLM-14 | P2 | Design | Pending |
| LLM-15 | P3: Abrir o chat automaticamente | Tasks | Implementing |
| LLM-16 | P3 | Tasks | Implementing |

**ID format:** `LLM-NN`, numerado na ordem de aparição dos critérios de aceite acima (P1 critérios
1–10 → LLM-01 a LLM-10; P2 critérios 1–4 → LLM-11 a LLM-14; P3 critérios 1–2 → LLM-15 a LLM-16).

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 16 total, 0 mapped to tasks, 16 unmapped ⚠️ (esperado nesta fase — tasks ainda não
foram escritas)

---

## Success Criteria

- [ ] Uma pessoa com o llamafile já rodando consegue perguntar algo sobre o corpus do tenant ativo e
      colar uma resposta fundamentada no chat do navegador, sem escrever nenhuma chamada HTTP à mão
- [ ] O contrato das quatro tools do servidor MCP permanece idêntico — nenhum teste de isolamento
      existente muda de comportamento
- [ ] Nenhuma chamada de rede a serviço pago é feita por este comando; o único endpoint externo
      tocado é o LLM local, e só para a checagem de saúde
