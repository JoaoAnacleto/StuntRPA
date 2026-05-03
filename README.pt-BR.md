# StuntRPA

**Ecosistema de Digital Twin para RPA - Gravação & Replay de sessões web.**

StuntRPA captura sessões web completas (tráfego de rede, snapshots do DOM, eventos de navegação) e as reproduz como "digital twins" autônomos da aplicação web original. Isso permite testes e automação RPA determinísticos e offline, sem depender de servidores ativos.

> 🇺🇸 [English version](README.md)

## Funcionalidades

- **Gravação de Sessão** - Captura todas as requisições/respostas HTTP via HAR, mutações do DOM via MutationObserver e eventos de navegação
- **Replay de Sessão** - Reproduz sessões gravadas interceptando todas as requisições de rede e servindo as respostas a partir do arquivo HAR capturado
- **Correspondência Inteligente de URLs** - Normalização inteligente de URLs que remove parâmetros de consulta efêmeros (`_`, `timestamp`, `nonce`, cache busters, trace IDs, etc.) para correspondência confiável durante o replay
- **Simulação de Latência** - Opcionalmente reproduz a latência de rede original durante o replay (com limite configurável)
- **Overlay em Tempo Real** - Overlay de gravação no navegador mostrando contadores de snapshots/requisições com um botão de parada
- **Suporte a Múltiplos Navegadores** - Chromium, Firefox e WebKit via Playwright
- **CLI & API Python** - Use como ferramenta de linha de comando ou importe como biblioteca

## Requisitos

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes recomendado)
- [Playwright](https://playwright.dev/python/) >= 1.40.0
- Node.js (para executar testes de validação JavaScript)

## Instalação

### Uso Rápido (uvx)

Execute o StuntRPA diretamente sem instalá-lo permanentemente:

```bash
# Do PyPI (quando publicado)
uvx stuntrpa --help
uvx stuntrpa record https://example.com my-scenario

# De um repositório git
uvx --from git+https://github.com/JoaoAnacleto/StuntRPA stuntrpa --help

# Certifique-se de que os navegadores do Playwright estão disponíveis (primeira vez apenas)
uvx --from git+https://github.com/JoaoAnacleto/StuntRPA playwright install
```

### Instalar com uv

```bash
# Clonar o repositório
git clone https://github.com/JoaoAnacleto/StuntRPA.git
cd StuntRPA

# Criar ambiente virtual, resolver dependências e instalar em modo editável
uv sync

# Instalar navegadores do Playwright
uv run playwright install
```

### Dependências

| Pacote | Versão | Finalidade |
|--------|--------|------------|
| playwright | >= 1.40.0 | Automação de navegador e gravação HAR |
| typer | >= 0.9.0 | Framework CLI |
| rich | >= 13.0.0 | Formatação e saída no terminal |

## Início Rápido

### Gravando uma Sessão

```bash
stuntrpa record https://example.com meu-primeiro-cenario
```

Isso abre um navegador, navega até a URL e inicia a gravação. Um overlay flutuante aparece no canto inferior direito mostrando:
- Número de snapshots capturados
- Número de requisições capturadas
- Um botão **STOP RECORDING**

Interaja com a página normalmente. Quando terminar:
- Clique em **STOP RECORDING** no overlay
- Feche a janela do navegador
- Pressione `Ctrl+C` no terminal

### Reproduzindo uma Sessão

```bash
stuntrpa replay meu-primeiro-cenario
```

Isso abre um navegador que carrega a URL inicial gravada. Todas as requisições de rede são interceptadas e servidas a partir do arquivo HAR capturado, criando um replay totalmente offline e determinístico da sessão original.

### Outros Comandos

```bash
# Listar todos os cenários gravados
stuntrpa list

# Mostrar informações detalhadas de um cenário
stuntrpa info meu-primeiro-cenario

# Excluir um cenário
stuntrpa delete meu-primeiro-cenario

# Mostrar versão
stuntrpa version
```

## Referência CLI

### `stuntrpa record`

Grava um novo cenário de sessão web.

```
stuntrpa record [OPÇÕES] URL NOME
```

**Argumentos:**
| Argumento | Descrição |
|-----------|-----------|
| `URL` | URL inicial para navegar (obrigatório) |
| `NOME` | Nome do cenário (obrigatório, deve ser único) |

**Opções:**
| Opção | Curto | Padrão | Descrição |
|-------|-------|--------|-----------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Diretório de armazenamento personalizado |
| `--headless` | - | `False` | Executar navegador em modo headless |
| `--browser` | `-b` | `chromium` | Motor do navegador: `chromium`, `firefox`, `webkit` |
| `--verbose` | `-v` | `False` | Ativar log de depuração |

### `stuntrpa replay`

Reproduz um cenário previamente gravado.

```
stuntrpa replay [OPÇÕES] NOME
```

**Argumentos:**
| Argumento | Descrição |
|-----------|-----------|
| `NOME` | Nome do cenário a reproduzir (obrigatório) |

**Opções:**
| Opção | Curto | Padrão | Descrição |
|-------|-------|--------|-----------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Diretório de armazenamento personalizado |
| `--headless` | - | `False` | Executar navegador em modo headless |
| `--browser` | `-b` | `chromium` | Motor do navegador: `chromium`, `firefox`, `webkit` |
| `--simulate-latency` | `-l` | `False` | Simular latência de rede original |
| `--verbose` | `-v` | `False` | Ativar log de depuração |

### `stuntrpa list`

Lista todos os cenários gravados.

```
stuntrpa list [OPÇÕES]
```

**Opções:**
| Opção | Curto | Padrão | Descrição |
|-------|-------|--------|-----------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Diretório de armazenamento personalizado |

### `stuntrpa info`

Mostra informações detalhadas sobre um cenário.

```
stuntrpa info [OPÇÕES] NOME
```

**Argumentos:**
| Argumento | Descrição |
|-----------|-----------|
| `NOME` | Nome do cenário (obrigatório) |

**Opções:**
| Opção | Curto | Padrão | Descrição |
|-------|-------|--------|-----------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Diretório de armazenamento personalizado |

### `stuntrpa delete`

Exclui um cenário gravado.

```
stuntrpa delete [OPÇÕES] NOME
```

**Argumentos:**
| Argumento | Descrição |
|-----------|-----------|
| `NOME` | Nome do cenário (obrigatório) |

**Opções:**
| Opção | Curto | Padrão | Descrição |
|-------|-------|--------|-----------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Diretório de armazenamento personalizado |
| `--yes` | `-y` | `False` | Pular prompt de confirmação |

### `stuntrpa version`

Imprime a versão atual.

```
stuntrpa version
```

## API Python

O StuntRPA também pode ser usado programaticamente como uma biblioteca Python.

### Gravando uma Sessão

```python
import asyncio
from stuntrpa.recorder import record_session

scenario = asyncio.run(record_session(
    url="https://example.com",
    name="meu-cenario",
    storage_path=None,       # usa o padrão ~/.stuntrpa/scenarios
    headless=False,
    browser_type="chromium",
))

print(f"Gravou {scenario.stats['total_requests']} requisições")
print(f"Salvou {scenario.stats['total_snapshots']} snapshots")
print(f"Duração: {scenario.stats['duration_seconds']}s")
```

### Reproduzindo uma Sessão (Autônomo)

```python
import asyncio
from stuntrpa.replayer import replay_session

asyncio.run(replay_session(
    scenario_name="meu-cenario",
    storage_path=None,
    simulate_latency=True,
    headless=False,
    browser_type="chromium",
))
```

### Usando `create_replay_context` (Controle Programático)

Para controle programático sobre o contexto do navegador em replay (ex.: executar asserções contra páginas reproduzidas):

```python
import asyncio
from stuntrpa import create_replay_context

async def main():
    context, page = await create_replay_context(
        scenario_name="meu-cenario",
        simulate_latency=False,
        headless=True,
        browser_type="chromium",
    )

    await page.goto("https://example.com")
    title = await page.title()
    print(f"Título da página: {title}")

    # Interaja com a página reproduzida...
    await context.close()

asyncio.run(main())
```

### Trabalhando com Cenários

```python
from stuntrpa.storage import Scenario

# Listar todos os cenários
names = Scenario.list_all()
print(names)  # ['meu-cenario', 'outro-cenario']

# Carregar um cenário
scenario = Scenario.load("meu-cenario")
print(scenario.start_url)
print(scenario.created_at)
print(scenario.stats)
print(scenario.events)

# Excluir um cenário
Scenario.delete("meu-cenario")
```

### Correspondência de URLs

```python
from stuntrpa.replayer.matcher import URLMatcher

matcher = URLMatcher()

# Normalizar uma URL (remove parâmetros efêmeros)
normalized = matcher.normalize_url("https://api.example.com/data?_=12345&key=abc")
# => "https://api.example.com/data?key=abc"

# Parâmetros efêmeros personalizados
custom_matcher = URLMatcher(ephemeral_params={"session_id", "csrf_token"})

# Encontrar melhor correspondência nas entradas HAR
entry = matcher.find_best_match(har_entries, url="https://api.example.com/data", method="GET")
```

## Arquitetura

### Estrutura do Projeto

```
src/stuntrpa/
  __init__.py              # Ponto de entrada do pacote, exporta create_replay_context
  constants.py             # Paths padrão, parâmetros efêmeros, tempo de debounce
  cli.py                   # CLI Typer com record, replay, list, info, delete, version
  recorder/
    __init__.py             # Exporta record_session
    capture.py              # Orquestrador principal de gravação (Playwright + HAR + snapshots)
    snapshot.py             # SnapshotManager - gerencia snapshots do DOM recebidos do JS
    injection.py            # Snippets JavaScript: MutationObserver, overlay UI, atualização de contadores
  replayer/
    __init__.py             # Exporta create_replay_context, replay_session
    engine.py               # Motor de replay - carregamento HAR, interceptação de rotas, criação de contexto
    matcher.py              # URLMatcher - normalização e estratégias de correspondência de URLs
  storage/
    __init__.py             # Exporta Scenario
    scenario.py             # Classe Scenario - CRUD, metadados, snapshots, eventos
    paths.py                # Utilitários de resolução de caminhos
tests/
  test_cli.py               # Testes de comandos CLI
  test_engine.py            # Testes de carregamento HAR e SnapshotManager
  test_injection.py         # Testes de validação de sintaxe JavaScript (via subprocess Node.js)
  test_matcher.py           # Testes de normalização e correspondência de URLs
  test_storage.py           # Testes de CRUD de cenários, eventos, snapshots e caminhos
```

### Como Funciona a Gravação

1. **Lançamento do Navegador** - O Playwright lança um navegador (Chromium/Firefox/WebKit) com gravação HAR habilitada
2. **Injeção de JavaScript** - Um script `MutationObserver` é injetado via `add_init_script` para observar mudanças no DOM
3. **Navegação** - O navegador navega para a URL alvo
4. **Captura do DOM** - Em cada mutação do DOM (com debounce de 500ms), o `document.documentElement.outerHTML` completo é serializado e enviado ao Python via `page.expose_function`
5. **Captura de Rede** - A gravação HAR integrada do Playwright captura todas as requisições e respostas HTTP
6. **Overlay** - Uma UI flutuante é injetada em cada página mostrando contadores em tempo real e um botão de parada
7. **Finalização** - Quando a gravação para, metadados (duração, versão do navegador, estatísticas) são gravados

### Como Funciona o Replay

1. **Carregamento do HAR** - O arquivo HAR gravado é carregado e analisado em entradas
2. **Lançamento do Navegador** - Um novo contexto de navegador Playwright é criado
3. **Interceptação de Rotas** - Todas as requisições de rede (`**`) são interceptadas via `context.route()`
4. **Correspondência de URLs** - Para cada requisição, o motor busca uma entrada HAR correspondente usando uma estratégia de 3 níveis:
   - **Correspondência exata** - A string da URL é idêntica
   - **Correspondência normalizada** - As URLs correspondem após remover parâmetros de consulta efêmeros
   - **Fallback de URL base** - As URLs correspondem ignorando todos os parâmetros de consulta e fragmentos
5. **Servimento de Resposta** - A resposta da entrada HAR correspondente é servida via `route.fulfill()`
6. **Simulação de Latência** - Se habilitada, `asyncio.sleep()` atrasa a resposta pelo tempo da requisição original (limitado a 5s)

### Formato de Armazenamento de Cenários

Cada cenário é armazenado como um diretório:

```
~/.stuntrpa/scenarios/<nome-do-cenario>/
  metadata.json       # Metadados, eventos e estatísticas do cenário
  session.har         # Arquivo HAR completo de todo o tráfego de rede
  snapshots/
    0001.html         # Snapshots sequenciais do DOM
    0002.html
    ...
```

**Estrutura do metadata.json:**

```json
{
  "name": "meu-cenario",
  "start_url": "https://example.com",
  "created_at": "2024-01-15T10:30:00+00:00",
  "browser_version": "Chrome 120",
  "playwright_version": "1.42.0",
  "stats": {
    "total_requests": 42,
    "total_snapshots": 7,
    "duration_seconds": 35.2
  },
  "events": [
    {
      "type": "navigation",
      "timestamp": "2024-01-15T10:30:01+00:00",
      "url": "https://example.com"
    },
    {
      "type": "snapshot",
      "timestamp": "2024-01-15T10:30:02+00:00",
      "file": "0001.html",
      "url": "https://example.com"
    }
  ]
}
```

### Parâmetros de Consulta Efêmeros

Os seguintes parâmetros de consulta são automaticamente removidos durante a normalização de URLs para correspondência:

Cache-busting: `_`, `__`, `_t`, `_ts`, `timestamp`, `ts`, `time`, `t`, `cachebuster`, `cache_buster`, `bust`, `rand`, `random`

Rastreamento: `nonce`, `request_id`, `requestId`, `correlation_id`, `correlationId`, `x-request-id`, `trace_id`, `traceId`, `span_id`, `spanId`

Estes são definidos em `src/stuntrpa/constants.py:EPHEMERAL_QUERY_PARAMS`.

## Testes

```bash
# Executar todos os testes
pytest

# Executar módulos de teste específicos
pytest tests/test_storage.py
pytest tests/test_matcher.py
pytest tests/test_cli.py
pytest tests/test_engine.py
pytest tests/test_injection.py

# Executar com saída detalhada
pytest -v

# Executar com cobertura
pytest --cov=stuntrpa
```

### Estrutura dos Testes

| Arquivo | O que testa |
|---------|-------------|
| `test_storage.py` | CRUD de cenários, resolução de caminhos, rastreamento de eventos, salvamento de snapshots, persistência de metadados |
| `test_matcher.py` | Normalização de URLs, remoção de parâmetros efêmeros, estratégia de correspondência de 3 níveis, extração de corpo base64 |
| `test_engine.py` | Carregamento/análise de arquivos HAR, handlers assíncronos do SnapshotManager |
| `test_cli.py` | Todos os comandos CLI (version, list, info, delete, record, replay) via Typer test runner |
| `test_injection.py` | Validação de sintaxe JavaScript usando subprocess Node.js |

## Desenvolvimento

### Configuração

```bash
# Clonar e entrar no projeto
git clone https://github.com/JoaoAnacleto/StuntRPA.git
cd StuntRPA

# Criar ambiente, instalar todas as dependências
uv sync

# Instalar navegadores do Playwright
uv run playwright install
```

### Linting

Este projeto usa [Ruff](https://docs.astral.sh/ruff/) para linting:

```bash
ruff check src/ tests/
```

A configuração está em `pyproject.toml`:
- Comprimento de linha: 100
- Target: Python 3.10

### Sistema de Build

Construído com [Hatchling](https://hatch.pypa.io/):

```bash
# Usando uv (recomendado)
uv sync

# Usando pip
pip install -e .
```

## Licença

MIT