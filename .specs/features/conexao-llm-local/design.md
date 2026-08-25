# Conexão com LLM Local Design

**Spec**: `.specs/features/conexao-llm-local/spec.md`
**Status**: Approved

---

## Architecture Overview

Um comando novo, `rag-context`, fora do servidor MCP. Ele reaproveita a mesma recuperação e a mesma
identidade de tenant do servidor, monta um bloco de texto e entrega esse bloco por stdout + área de
transferência. Nenhuma chamada de geração é feita por este repositório — quem gera é a pessoa, no
chat que o `llamafile` já serve no navegador.

```mermaid
graph TD
    A["rag-context "pergunta" [--mode] [--top-k] [--profile] [--open]"] --> B[context_cli.main]
    B --> C["rag.db.resolve_tenant_from_env()"]
    C -->|falha| C1[sys.exit - mesma mensagem do server]
    C -->|ok| D["rag.query.validate_query / validate_top_k / validate_mode"]
    D -->|inválido| D1[erro em stderr, exit != 0, sem tocar banco]
    D -->|ok| E["rag.local_llm.resolve_base_url() + check_health()"]
    E -->|indisponível/timeout| E1[warning em stderr - endpoint + sugestão]
    E -->|ok| E2["guarda meta.n_ctx da resposta"]
    E1 --> F
    E2 --> F["rag.db.scoped_connection(tenant) + rag.query.run_search(...)"]
    F -->|OperationalError| F1[erro em stderr, exit != 0]
    F -->|zero candidatos| F2["aviso stderr/stdout: nada encontrado, sem copiar bloco vazio"]
    F -->|>=1 candidato| G["rag.context_block.build_block(pergunta, candidatos)"]
    G --> H{"bloco grande demais para n_ctx?"}
    H -->|sim| H1[warning em stderr com tamanho estimado x n_ctx]
    H -->|não| I
    H1 --> I["print(bloco) em stdout"]
    I --> J["rag.context_block.copy_to_clipboard(bloco) - best effort"]
    J -->|--open| K["rag.local_llm.open_browser(base_url) - best effort"]
```

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --------- | -------- | ---------- |
| `resolve_tenant_from_env` | `src/rag/db.py:47` | Import direto, sem mudança — mesma resolução de identidade e mesma mensagem de erro do servidor MCP |
| `scoped_connection` | `src/rag/db.py:32` | Import direto — mesma conexão `rag_app` com `SET LOCAL app.tenant_id` |
| `semantic.search` / `lexical.search` / `hybrid.search` | `src/rag/retrieval/*.py` | Chamados através do novo `rag.query.run_search`, não diretamente |
| `Candidate` | `src/rag/retrieval/__init__.py` | Mesma dataclass; `context_block.build_block` consome `chunk_id`, `document_id`, `text`, `position` |
| `ChunkProfile` | `src/rag/chunking.py:22` | Reaproveitado como tipo do `--profile` |

### Integration Points

| System | Integration Method |
| ------ | ------------------- |
| PostgreSQL (RLS) | Mesma `scoped_connection`, mesma política de RLS — nenhuma tabela ou query nova |
| LLM local (`llamafile`) | `GET {base_url}/v1/models`, best-effort, timeout de 2s, via `urllib.request` (stdlib) |
| Área de transferência do SO | `pbcopy` (macOS) via `subprocess`, best-effort |
| Navegador (P3, `--open`) | `webbrowser.open()` (stdlib), best-effort |

---

## Components

### `rag/query.py` (novo — extraído de `server.py`)

- **Purpose**: único ponto de verdade para validar `query`/`top_k`/`mode` e despachar para o módulo
  de busca certo — hoje duplicado seria um risco, hoje evitado por extração.
- **Location**: `src/rag/query.py`
- **Interfaces**:
  - `MAX_QUERY_CHARS: int`, `MIN_TOP_K: int`, `MAX_TOP_K: int` — movidos de `server.py` sem mudar valor
  - `SEARCH_MODULES: dict[str, ModuleType]` — o mesmo dicionário `{"semantic": ..., "lexical": ..., "hybrid": ...}`
  - `validate_query(query: str) -> str`
  - `validate_top_k(top_k: int) -> int`
  - `validate_mode(mode: str) -> Mode`
  - `run_search(conn: psycopg.Connection, query: str, mode: Mode, top_k: int, profile: ChunkProfile) -> list[Candidate]` — novo, fatora `_SEARCH_MODULES[mode].search(conn, query, top_k, profile)`, hoje repetido inline em `server.search` e `server.explain_retrieval`
- **Dependencies**: `rag.retrieval` (semantic/lexical/hybrid), `rag.chunking`
- **Reuses**: nada externo — é puramente a extração do que já existe em `server.py:22-38,72-76,94-96`

### `rag/server.py` (modificado — só a extração)

- **Purpose**: inalterado — servidor MCP somente-leitura, escopado por tenant
- **Location**: `src/rag/server.py`
- **Mudança**: `_validate_query`/`_validate_top_k`/`_validate_mode`/`_SEARCH_MODULES`/`_MAX_QUERY_CHARS`/`_MIN_TOP_K`/`_MAX_TOP_K` somem daqui; `server.py` passa a importar de `rag.query`. `search()` e `explain_retrieval()` chamam `query.run_search(...)` no lugar de `_SEARCH_MODULES[mode].search(...)` inline. Nenhuma tool, assinatura, mensagem de erro ou comportamento observável muda — regression gate é a suíte `tests/integration/test_server*.py` e `tests/isolation/*` continuando verdes, sem editar nenhum teste.
- **Reuses**: `rag.query` (novo)

### `rag/local_llm.py` (novo)

- **Purpose**: tudo que fala com o processo do `llamafile` — checagem de saúde e abertura do navegador. Nunca envia a pergunta nem lê uma resposta de chat.
- **Location**: `src/rag/local_llm.py`
- **Interfaces**:
  - `resolve_base_url() -> str` — lê `LOCAL_LLM_BASE_URL`, default `http://127.0.0.1:8080`; levanta `ValueError` se o valor não for uma URL `http(s)` (edge case do spec)
  - `HealthStatus` — `@dataclass(frozen=True)`: `reachable: bool`, `detail: str`, `context_window: int | None`
  - `check_health(base_url: str, timeout: float = 2.0) -> HealthStatus` — `GET {base_url}/v1/models`; sucesso preenche `context_window` a partir de `data[0].meta.n_ctx` quando presente; qualquer exceção de rede/timeout/JSON vira `HealthStatus(reachable=False, detail=str(exc), context_window=None)` — nunca propaga
  - `open_browser(base_url: str) -> bool` — `webbrowser.open(base_url)`, captura exceção e retorna `False`
- **Dependencies**: `urllib.request`, `webbrowser` (stdlib, nenhuma dependência nova)
- **Reuses**: nada

### `rag/context_block.py` (novo)

- **Purpose**: montar o bloco de texto (pergunta + chunks citados + instrução) e entregá-lo por
  stdout/área de transferência.
- **Location**: `src/rag/context_block.py`
- **Interfaces**:
  - `build_block(question: str, candidates: list[Candidate]) -> str`
  - `estimate_tokens(text: str) -> int` — heurística `len(text) // 4` (sem tokenizer novo; só para o aviso de tamanho, nunca para bloquear)
  - `copy_to_clipboard(text: str) -> bool` — `subprocess.run(["pbcopy"], input=text, ...)` se `shutil.which("pbcopy")`; senão retorna `False` sem tentar
- **Dependencies**: `subprocess`, `shutil` (stdlib)
- **Reuses**: `Candidate` de `rag.retrieval`

### `rag/context_cli.py` (novo — entrypoint `rag-context`)

- **Purpose**: orquestra o fluxo descrito no diagrama; é o único lugar com `argparse` e `print`.
- **Location**: `src/rag/context_cli.py`
- **Interfaces**:
  - `main() -> None` — ponto de entrada registrado em `pyproject.toml`
  - `build_parser() -> argparse.ArgumentParser` — separado de `main` para ser testável sem rodar o processo inteiro
- **Dependencies**: `rag.db`, `rag.query`, `rag.local_llm`, `rag.context_block`, `rag.chunking`
- **Reuses**: todos os componentes acima

---

## Data Models (if applicable)

Nenhum modelo novo. `Candidate` (já existe em `rag/retrieval/__init__.py`) e `HealthStatus` (novo,
`rag/local_llm.py`, descrito acima) são as únicas estruturas de dados envolvidas — nenhuma tabela,
nenhuma migração.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| --------------- | -------- | ------------ |
| `RAG_TENANT_ID` ausente/desconhecido | `resolve_tenant_from_env()` já chama `sys.exit` com a mensagem existente — reaproveitada sem mudança | Mesma mensagem que já aparece ao rodar o servidor MCP sem tenant |
| Pergunta vazia ou maior que `MAX_QUERY_CHARS` | `rag.query.validate_query` levanta `ValueError`; `context_cli` captura e sai com mensagem em stderr, sem tocar banco nem LLM | Mensagem nomeando o limite, comando sai com código != 0 |
| `top_k` fora de 1–50 | `rag.query.validate_top_k` levanta `ValueError`, mesmo tratamento acima | Mensagem nomeando o intervalo |
| `LOCAL_LLM_BASE_URL` não é `http(s)` válido | `resolve_base_url()` levanta `ValueError` antes de qualquer tentativa de rede | Mensagem citando o valor recebido, comando sai com código != 0 |
| LLM local inacessível ou expira o timeout | `check_health` retorna `HealthStatus(reachable=False, ...)` — nunca levanta | Aviso em stderr citando `base_url` e sugestão de iniciar o llamafile; o comando continua |
| Bloco de contexto maior que `context_window` reportado | Comparação simples `estimate_tokens(block) > context_window` | Aviso em stderr com tamanho estimado x janela do modelo; o bloco é entregue do mesmo jeito |
| Banco de dados inacessível (`psycopg.OperationalError`) | Capturado em `context_cli`, mesma classe de erro que `server.search` já trata | Mensagem clara em stderr, comando sai com código != 0 |
| Zero chunks retornados | `context_cli` verifica lista vazia antes de montar o bloco | Aviso "nenhum contexto encontrado", nada é copiado nem impresso como bloco, código de saída 0 |
| `pbcopy` ausente ou falha | `copy_to_clipboard` retorna `False`, capturado, nunca levanta | Nota em stderr de que a cópia não funcionou; o bloco já está em stdout |
| `--open` falha ao abrir navegador | `open_browser` retorna `False`, capturado | Aviso em stderr; comando sai com código 0 do mesmo jeito |

---

## Risks & Concerns

| Concern | Location (file:line) | Impact | Mitigation |
| ------- | --------------------- | ------ | ---------- |
| Bloco de contexto pode ultrapassar a janela de contexto do modelo local | `context_block.build_block` combinado com `--top-k 50 --profile P1024` (P2) | Com `top_k=50` e chunks de ~1024 tokens, o bloco pode chegar a ~50k tokens; a instância testada nesta máquina reporta `n_ctx=16384` — a pessoa colaria um prompt que o llamafile trunca ou rejeita, sem aviso nenhum se nada checar isso | `check_health` já captura `context_window` do `/v1/models`; `context_cli` compara com `estimate_tokens(block)` e avisa em stderr sem bloquear a entrega (ver Error Handling Strategy) |
| `copy_to_clipboard` é macOS-only (`pbcopy`) | `rag/context_block.py` (novo) | Em Linux/CI a cópia sempre falha silenciosamente para "não copiado" | `shutil.which("pbcopy")` evita até tentar fora do macOS; stdout (AC LLM-04) já é o caminho garantido em qualquer SO — documentado no `--help` do comando |
| `llamafile` roda sem chave de API e com CORS aberto para qualquer origem (confirmado no log da instância testada: `CORS is set to allow all origins ('*') and no API key is set`) | Processo externo, fora deste repositório | Qualquer outro processo/aba do navegador na mesma máquina também alcança o LLM enquanto ele está de pé | Fora do escopo deste comando (não é este repositório quem inicia nem configura o llamafile); `--host 127.0.0.1` já limita ao próprio host — mesma postura de risco aceito que o projeto já assume para o Postgres local |
| Extração de `_validate_query`/`_validate_top_k`/`_validate_mode`/`_SEARCH_MODULES` para fora de `server.py` | `src/rag/server.py:22-38,72-76,88-99,153-166` | `server.py` é o arquivo mais sensível do repositório para isolamento entre tenants (RAG-16/AD-003); um deslize na extração poderia mudar comportamento validado pela suíte de isolamento | Extração é só código-movido, sem mudança de lógica; a task correspondente roda `tests/integration/test_server*.py` e `tests/isolation/*` como gate antes de qualquer linha do comando novo ser escrita |

> Nenhum outro risco identificado além dos quatro acima.

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| -------- | ------ | --------- |
| Cliente HTTP para a checagem de saúde | `urllib.request` (stdlib) | Uma única requisição GET não justifica adicionar `requests`/`httpx` como dependência nova |
| Endpoint da checagem de saúde | `GET /v1/models` (não `/health`) | Confirmado nesta sessão contra a instância real: `/v1/models` responde 200 sem auth e já traz `meta.n_ctx`, reaproveitado para o aviso de bloco grande demais — uma requisição serve dois propósitos |
| Extrair validação + dispatch de modo para `rag/query.py` | Extração, não duplicação (decisão confirmada com a pessoa) | Evita duas cópias das regras RAG-11/12/13 e do dicionário de modos; o custo (tocar `server.py`) é mitigado por ser puro código-movido com o teste de isolamento existente como gate |
| Separação stdout / stderr | Bloco de contexto **somente** em stdout; toda checagem, aviso ou erro em stderr | Mantém `rag-context "..." | pbcopy` ou redirecionamento de stdout para arquivo limpo, sem misturar diagnóstico com o texto que vai ser colado no chat |
| Abrir navegador (P3) | `webbrowser.open()` (stdlib) em vez de invocar `open`/`xdg-open` via `subprocess` | API padrão do Python já resolve o comando certo por sistema operacional, sem `subprocess` extra |
| Cópia para área de transferência | `pbcopy` via `subprocess`, sem biblioteca de clipboard nova | Ambiente de desenvolvimento documentado deste repositório é macOS (Darwin); stdout cobre o resto |

> **Project-level decision:** a decisão de onde a geração assistida por LLM entra no projeto (comando
> externo ao MCP, nunca chamada de chat completion do Python) é registrada como `AD-006` em
> `.specs/STATE.md`.

---

## Novo comando no `pyproject.toml`

```toml
[project.scripts]
ingest = "rag.ingest:main"
rag-server = "rag.server:main"
rag-eval = "eval.harness:main"
rag-context = "rag.context_cli:main"
```
