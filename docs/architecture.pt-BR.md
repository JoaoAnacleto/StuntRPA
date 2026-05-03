# Arquitetura

Este documento descreve a arquitetura interna, o fluxo de dados e as decisões de design do StuntRPA.

> 🇺🇸 [English version](architecture.md)

## Visão Geral

O StuntRPA implementa um padrão **Gravação-Replay** para aplicações web. Consiste em dois pipelines principais:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Gravador   │──────▶  │  Armazenamento │◀──────▶  │   Replay    │
│  (captura)   │         │ (cenário)  │         │   (motor)   │
└─────────────┘         └─────────────┘         └─────────────┘
      │                       │                       │
  Playwright            HAR + JSON + HTML         Playwright
  + Injeção JS           (sistema de arquivos)     + Interceptação de Rotas
```

## Arquitetura de Módulos

```
                    ┌──────────────────────┐
                    │       CLI (Typer)     │
                    │  record | replay |    │
                    │  list | info | delete │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
     ┌─────────────────┐              ┌─────────────────┐
     │    Gravador      │              │    Replay        │
     │                  │              │                  │
     │  capture.py      │              │  engine.py       │
     │  snapshot.py     │              │  matcher.py      │
     │  injection.py    │              │                  │
     └────────┬────────┘              └────────┬────────┘
              │                                 │
              ▼                                 ▼
     ┌─────────────────────────────────────────────────┐
     │              Armazenamento                       │
     │                                                 │
     │  scenario.py  (CRUD + metadados + eventos)      │
     │  paths.py     (resolução de caminhos no FS)     │
     └─────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Sistema de Arquivos │
              │  ~/.stuntrpa/     │
              │    scenarios/     │
              │      <name>/      │
              │        metadata   │
              │        session    │
              │        snapshots  │
              └──────────────────┘
```

## Pipeline de Gravação

O pipeline de gravação captura três tipos de dados simultaneamente:

### Fluxo passo a passo

```
  Navegador               Python (capture.py)          Armazenamento (scenario.py)
    │                           │                              │
    │  1. Lançar navegador     │                              │
    │  com gravação HAR         │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  2. Injetar JS            │                              │
    │  (MutationObserver)       │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  3. Navegar para URL      │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  4. Mudanças no DOM       │                              │
    │────────────────────────▶  │                              │
    │  (stuntRpaOnSnapshot)     │  5. Analisar JSON            │
    │                           │─────────────────────────────▶│
    │                           │  save_snapshot(html, url)     │
    │                           │                              │
    │  6. Requisições HTTP      │                              │
    │  (auto-capturadas pelo HAR) │  7. increment_stat         │
    │                           │─────────────────────────────▶│
    │                           │                              │
    │  8. Usuário clica STOP    │                              │
    │  (stuntRpaStopRecording)  │                              │
    │────────────────────────▶  │                              │
    │                           │  9. finalize()               │
    │                           │─────────────────────────────▶│
    │                           │  (duração, versões, etc.)    │
    │                           │                              │
```

### Injeção de JavaScript

Três snippets de JavaScript são injetados no navegador:

1. **`MUTATION_OBSERVER_JS`** - Injetado via `page.add_init_script()` para ser executado em cada carregamento de página:
   - Cria um `MutationObserver` em `document.documentElement`
   - Observa: `childList`, `subtree`, `attributes`, `characterData`
   - Aplica debounce de 500ms antes de capturar
   - Envia `document.documentElement.outerHTML` para o Python via `window.stuntRpaOnSnapshot()`
   - Protege contra reinicialização com `window.__stuntrpa_observer_active`

2. **`OVERLAY_JS`** - Injetado em cada evento `domcontentloaded` e `load`:
   - Cria um overlay de posição fixa (z-index: 2147483647)
   - Mostra contadores de snapshots e requisições em tempo real
   - Fornece um botão STOP que chama `window.stuntRpaStopRecording()`

3. **`REQUEST_COUNTER_UPDATE_JS`** - Chamado do Python a cada requisição:
   - Atualiza o contador de requisições no overlay

### Ponte de Comunicação

A função `page.expose_function()` do Playwright é usada para criar uma ponte de JavaScript para Python:

| Função JS | Handler Python | Finalidade |
|-----------|---------------|------------|
| `stuntRpaOnSnapshot(data)` | `SnapshotManager.create_handler()` | Recebe snapshots do DOM |
| `stuntRpaStopRecording()` | `handle_stop()` em capture.py | Sinaliza o fim da gravação |

## Pipeline de Replay

O pipeline de replay intercepta todo o tráfego de rede e serve as respostas a partir do arquivo HAR gravado.

### Fluxo passo a passo

```
  Navegador               Python (engine.py)          Armazenamento (scenario.py)
    │                           │                              │
    │  1. Carregar cenário      │                              │
    │                           │◀─────────────────────────────│
    │                           │  Scenario.load()             │
    │                           │                              │
    │  2. Carregar entradas HAR │                              │
    │                           │◀─────────────────────────────│
    │                           │  _load_har_entries()         │
    │                           │                              │
    │  3. Lançar navegador     │                              │
    │  + configurar route("**") │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  4. Navegar para start_url │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  5. Requisição: GET /api/data│                           │
    │────────────────────────▶  │                              │
    │                           │  6. URLMatcher.find_best_match()
    │                           │     ├── correspondência exata   │
    │                           │     ├── correspondência normalizada │
    │                           │     └── fallback de URL base  │
    │                           │                              │
    │  7. route.fulfill()       │                              │
    │◀──────────────────────────│                              │
    │  (servido do HAR)         │                              │
    │                           │                              │
    │  8. Página fecha          │                              │
    │────────────────────────▶  │                              │
    │                           │  9. Limpeza                  │
    │                           │                              │
```

### Estratégia de Correspondência de URLs

O `URLMatcher` implementa uma estratégia de correspondência de 3 níveis com ordenação de prioridade:

```
Prioridade 1: Correspondência Exata
  https://api.example.com/data?key=1  ==  https://api.example.com/data?key=1
  ✓ Retorna imediatamente

Prioridade 2: Correspondência Normalizada
  https://api.example.com/data?_=123&key=1  ≈  https://api.example.com/data?_=456&key=1
  (após remover parâmetros efêmeros: https://api.example.com/data?key=1)

Prioridade 3: Fallback de URL Base
  https://api.example.com/data?any=param  ~  https://api.example.com/data?other=param
  (ignorando todos os parâmetros de consulta: https://api.example.com/data)

Sem correspondência → abortar requisição (ou fallback para rede real)
```

O processo de normalização:

```
URL de entrada:  https://api.example.com/data?_=12345&timestamp=999&key=abc&page=1
                         │
                         ▼
              Analisar parâmetros de consulta
                         │
                         ▼
         Filtrar parâmetros efêmeros (_, timestamp)
                         │
                         ▼
         Restantes: key=abc&page=1
                         │
                         ▼
Normalizado: https://api.example.com/data?key=abc&page=1
```

### Servimento de Resposta

Quando uma correspondência é encontrada, a resposta é construída a partir da entrada HAR:

1. Extrair código de status de `entry.response.status`
2. Extrair headers de `entry.response.headers` (remove `content-encoding`, `content-length`, `transfer-encoding`)
3. Extrair corpo via `URLMatcher.extract_response_body()`:
   - Se `encoding == "base64"`: decodifica de base64, retorna `bytes`
   - Caso contrário: retorna como `str`
4. Se simulação de latência estiver habilitada: `asyncio.sleep(min(entry.time / 1000, 5.0))`
5. Servir via `route.fulfill(status, headers, body)`

## Camada de Armazenamento

### Estrutura de Diretório do Cenário

```
~/.stuntrpa/scenarios/<nome>/
├── metadata.json           # Metadados, estatísticas e eventos do cenário
├── session.har             # Arquivo HAR 1.2 completo
└── snapshots/
    ├── 0001.html           # Snapshot completo do DOM
    ├── 0002.html
    └── ...
```

### Ciclo de Vida do Cenário

```
  Scenario.create(name, url)
         │
         ▼
  [Ativo - gravação em andamento]
         │
         ├── add_event() ──────────▶ metadata.json (events[])
         ├── increment_stat() ─────▶ metadata.json (stats{})
         └── save_snapshot(html) ──▶ snapshots/0001.html
                                     metadata.json (stats.total_snapshots++)
         │
         ▼
  Scenario.finalize(versions)
         │
         ▼
  [Persistido - pronto para replay]
         │
         ├── Scenario.load(name)
         ├── Scenario.list_all()
         └── Scenario.delete(name)
```

### Esquema de Metadados

```json
{
  "name": "string",
  "start_url": "string",
  "created_at": "datetime ISO 8601",
  "browser_version": "string",
  "playwright_version": "string",
  "stats": {
    "total_requests": "integer",
    "total_snapshots": "integer",
    "duration_seconds": "float"
  },
  "events": [
    {
      "type": "navigation | snapshot",
      "timestamp": "datetime ISO 8601",
      "url": "string (eventos de navegação)",
      "file": "string (eventos de snapshot)"
    }
  ]
}
```

## Decisões de Design

### Por que o formato HAR?

O Playwright possui gravação HAR integrada via `context.record_har_path`. Usar o formato HAR 1.2 padrão:
- Não é necessária serialização personalizada para dados de rede
- Compatível com outras ferramentas (visualizadores HAR, analisadores)
- Suporta conteúdo binário via codificação base64

### Por que MutationObserver para snapshots?

Em vez de polling ou captura em intervalo, o `MutationObserver` oferece:
- Baseado em eventos: captura apenas quando o DOM realmente muda
- Cobertura completa: captura todos os tipos de mutação (elementos, atributos, texto)
- Com debounce: o debounce de 500ms evita snapshots excessivos durante mudanças rápidas

### Por que correspondência de URLs de 3 níveis?

Durante o replay, as URLs podem diferir da original devido a:
- **Parâmetros efêmeros**: cache busters, timestamps mudam entre sessões
- **Valores de parâmetros diferentes**: tokens de sessão, nonces diferem
- **Novos parâmetros**: parâmetros de analytics ou rastreamento adicionados pelo navegador

A estratégia de 3 níveis fornece degradação graciosa da correspondência exata para fuzzy.

### Por que `page.expose_function`?

A `expose_function` do Playwright cria um callback direto de JS para Python sem polling. Isso é mais eficiente do que:
- Polling por snapshots (adiciona latência)
- Escrever em arquivo e observar (overhead de I/O)
- Usar WebSocket (infraestrutura extra)

### Estratégia de Limpeza

Tanto o gravador quanto o replayer usam blocos `try/finally` para garantir que os contextos do navegador sejam fechados mesmo em caso de exceções. A função `create_replay_context` anexa um handler `page.on("close")` que limpa automaticamente o navegador e a instância do Playwright.

## Configuração

### Constantes (`src/stuntrpa/constants.py`)

| Constante | Valor | Finalidade |
|-----------|-------|------------|
| `DEFAULT_STORAGE_PATH` | `~/.stuntrpa/scenarios` | Local padrão de armazenamento de cenários |
| `EPHEMERAL_QUERY_PARAMS` | 18 parâmetros de cache/rastreamento | Parâmetros de consulta removidos durante a correspondência de URLs |
| `SNAPSHOT_DEBOUNCE_MS` | `500` | Intervalo de debounce para snapshots de mutação do DOM |

### Configuração de Build (`pyproject.toml`)

| Configuração | Valor |
|-------------|-------|
| Sistema de build | Hatchling |
| Versão do Python | >= 3.10 |
| Comprimento de linha (Ruff) | 100 |
| Target do Ruff | py310 |
| Licença | MIT |

## Tratamento de Erros

| Cenário | Módulo | Comportamento |
|---------|--------|---------------|
| Nome de cenário duplicado | `Scenario.create()` | Lança `FileExistsError` |
| Cenário não encontrado | `Scenario.load()` | Lança `FileNotFoundError` |
| Arquivo HAR inválido | `_load_har_entries()` | Lança `FileNotFoundError` ou retorna entradas vazias |
| Sem correspondência de URL no replay | `engine.py` | Aborta requisição (`route.abort()`) com log de aviso |
| Falha ao salvar snapshot | `SnapshotManager` | Registra exceção, continua gravação |
| Fechamento do navegador durante gravação | `capture.py` | Finaliza cenário no bloco `finally` |
| Página fechada durante replay | `engine.py` | Captura exceção, fecha contexto no bloco `finally` |
| JSON inválido do JS | `SnapshotManager` | Registra exceção, continua gravação |