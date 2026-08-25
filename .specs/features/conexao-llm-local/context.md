# Conexão com LLM Local — Context

**Gathered:** 2026-08-24
**Spec:** `.specs/features/conexao-llm-local/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Um comando de linha de comando neste repositório que recupera, para uma pergunta, o contexto
relevante do tenant ativo (reaproveitando a recuperação e o `RAG_TENANT_ID` já existentes) e entrega
esse contexto pronto para uso no chat que o `llamafile` já serve no navegador em `/Volumes/LocalAgent`.
O comando também verifica se o LLM local está respondendo, como aviso, não como bloqueio.

O servidor MCP e suas quatro tools de recuperação não mudam. Nenhuma chamada de geração (chat
completion) é feita a partir do Python deste repositório — quem gera é o chat do próprio llamafile.

---

## Implementation Decisions

### Propósito da conexão

- A conexão serve para **gerar respostas** fundamentadas no corpus (retrieve, depois generate) —
  não para usar o LLM local como juiz de avaliação. Essa segunda ideia (métrica de qualidade tipo
  RAGAS agora sem barreira de chave de API) fica registrada em Deferred Ideas, decisão separada.

### Fronteira com o servidor MCP

- A geração **não** entra como tool nova no servidor MCP. O contrato das quatro tools
  (`search`, `get_document`, `list_sources`, `explain_retrieval`) e a decisão "servidor recupera,
  cliente gera" (RAG-16/AD-003) continuam exatamente como estão.
- A peça nova é um comando **separado**, fora do MCP, que só existe para preparar o material que vai
  para o chat do llamafile.

### Formato do chat

- Depois de uma primeira resposta dizendo "quero usar direto na interface, no chat", uma segunda
  rodada fechou qual interface: **a página web que o próprio llamafile serve no navegador**
  (a que aparece ao abrir `http://127.0.0.1:8080` depois de rodar o binário) — não um chat novo no
  terminal, nem um script com loop de pergunta/resposta.
- Consequência direta: este repositório nunca chama o endpoint de chat completion do llamafile.
  Quem conversa com o modelo é a pessoa, pelo navegador. O papel do código é só preparar o texto que
  vai ser colado lá.

### Mecanismo de entrega do contexto

- **Decisão do agente (ver Assumptions do spec):** copiar o bloco de contexto para a área de
  transferência do sistema operacional (`pbcopy` no macOS) e também imprimir em stdout. Escolhido
  porque funciona sem depender de nenhum detalhe interno da UI do llamafile (que não documenta um
  parâmetro oficial de pré-preenchimento) e sem automação de navegador.

### Agent's Discretion

- Endpoint/porta padrão do LLM local (`http://127.0.0.1:8080`), timeout da checagem de saúde,
  formato exato do bloco de prompt (pergunta + chunks citados por `document_id` e posição +
  instrução de responder só com base no conteúdo) e nomes de flags da CLI (`--mode`, `--top-k`,
  `--profile`, `--open`) ficam a critério do agente, registrados como assumptions no spec.
- Reaproveitar `RAG_TENANT_ID`, `resolve_tenant_from_env()` e os módulos de busca existentes
  (`rag.retrieval.semantic/lexical/hybrid`) em vez de inventar um mecanismo de identidade novo.

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma área foi declinada nas duas rodadas de discussão. Detalhes técnicos que não foram levados à
conversa (porta/endpoint padrão do llamafile, timeout da checagem de saúde, exigir vs. só avisar
quando o LLM local está fora do ar, formato do bloco de prompt) estão na tabela de premissas do spec,
com default e justificativa.

---

## Specific References

- Binário e modelo em `/Volumes/LocalAgent`: `llamafile-0.10.5-thin` + `Qwen3.5-0.8B-Q8_0.llamafile`.
  `iniciar_ai.bat` (arquivo RTF com extensão `.bat`, artefato de um ambiente Windows) documenta o
  comando de referência: `llamafile-0.10.5-thin.exe -m Qwen3.5-0.8B-Q8_0.llamafile.gguf --host 127.0.0.1`.
  Nesta máquina (macOS), o binário e o modelo já vêm no formato llamafile executável direto — não há
  processo do llamafile em execução no momento deste planejamento (verificado: nada escutando em
  `127.0.0.1:8080`).
- Retoma o item "Camada de geração com resposta em linguagem natural" deixado em
  `.specs/features/rag-com-escopo-de-tenant/context.md` §Deferred Ideas, que a época apontava chave de
  API e custo por pergunta como bloqueio — um LLM local remove os dois.

---

## Deferred Ideas

- **LLM local como juiz de avaliação** (métricas de qualidade de geração no harness de eval, estilo
  RAGAS, hoje fora por causa da AD-004) — fica para decisão separada, depois desta conexão existir.
- **Chamada automática ao endpoint de chat completion do llamafile a partir do Python** — o usuário
  optou por continuar usando a interface web do próprio llamafile para a geração; automatizar a
  chamada de chat é outra decisão, que reabriria a fronteira "servidor recupera, cliente gera".
- **Nova tool de geração no servidor MCP** — decisão explicitamente descartada nesta rodada; mantém
  RAG-16/AD-003 intactos.
- **Gerenciar o processo do llamafile (start/stop/monitor) a partir deste repositório** — o binário e
  o modelo vivem num volume externo (`/Volumes/LocalAgent`), fora do repositório; a pessoa inicia o
  servidor manualmente, como já acontece com o Postgres via Docker Compose.
- **Injeção automática do contexto na página do navegador** (via automação ou parâmetro de URL) —
  não descartada, mas não verificada: fica para o Design conferir se o llamafile expõe algum
  mecanismo oficial antes de decidir entre isso e a cópia para a área de transferência.
