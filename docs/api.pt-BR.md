# Referência de API

Referência completa de todos os módulos, classes e funções públicas do StuntRPA.

---

## `stuntrpa` (pacote de nível superior)

**Arquivo:** `src/stuntrpa/__init__.py`

```python
from stuntrpa import create_replay_context, __version__
```

| Exportação | Tipo | Descrição |
|-----------|------|-----------|
| `create_replay_context` | função assíncrona | Cria um `BrowserContext` e `Page` do Playwright prontos para replay |
| `__version__` | `str` | Versão do pacote (`"0.1.0"`) |

---

## `stuntrpa.constants`

**Arquivo:** `src/stuntrpa/constants.py`

### `DEFAULT_STORAGE_PATH`

```python
DEFAULT_STORAGE_PATH: Path  # ~/.stuntrpa/scenarios
```

Diretório padrão onde os cenários são armazenados.

### `EPHEMERAL_QUERY_PARAMS`

```python
EPHEMERAL_QUERY_PARAMS: frozenset[str]
```

Conjunto de nomes de parâmetros de consulta que são removidos durante a normalização de URLs. Inclui parâmetros de cache-busting (`_`, `timestamp`, `cachebuster`, `rand`, etc.) e IDs de rastreamento (`nonce`, `request_id`, `trace_id`, `span_id`, etc.).

### `SNAPSHOT_DEBOUNCE_MS`

```python
SNAPSHOT_DEBOUNCE_MS: int  # 500
```

Intervalo de debounce em milissegundos para o gatilho de snapshot do MutationObserver. Nota: o JS atual usa um valor fixo; esta constante é para referência.

---

## `stuntrpa.cli`

**Arquivo:** `src/stuntrpa/cli.py`

Aplicação CLI Typer. Ponto de entrada registrado como console script `stuntrpa`.

### `app`

```python
app: typer.Typer
```

A instância principal da aplicação Typer.

### Comandos

#### `version()`

Imprime a versão atual: `stuntrpa 0.1.0`

#### `record(url, name, storage, headless, browser, verbose)`

Grava uma nova sessão web. Abre um navegador, navega para `url`, captura todas as interações. Retorna código de saída 1 se um cenário com `name` já existir.

#### `replay(name, storage, headless, browser, simulate_latency, verbose)`

Reproduz um cenário gravado. Intercepta todas as requisições de rede e serve as respostas a partir do arquivo HAR capturado. Retorna código de saída 1 se o cenário não for encontrado.

#### `list_scenarios(storage)`

Lista todos os cenários gravados em uma tabela formatada com nome, data de criação, URL, contagem de requisições, contagem de snapshots e duração.

#### `delete(name, storage, confirm)`

Exclui um cenário. Solicita confirmação a menos que `--yes` seja passado.

#### `info(name, storage)`

Exibe informações detalhadas do cenário: metadados, estatísticas e uma tabela de eventos (até 20 são mostrados).

---

## `stuntrpa.recorder`

**Arquivo:** `src/stuntrpa/recorder/__init__.py`

### `record_session()`

```python
async def record_session(
    url: str,
    name: str,
    storage_path: Path | None = None,
    headless: bool = False,
    browser_type: str = "chromium",
) -> Scenario
```

Grava uma sessão web completa.

**Parâmetros:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `url` | `str` | obrigatório | URL inicial para navegar |
| `name` | `str` | obrigatório | Nome único do cenário |
| `storage_path` | `Path \| None` | `None` | Diretório de armazenamento personalizado (usa o padrão se `None`) |
| `headless` | `bool` | `False` | Executar navegador em modo headless |
| `browser_type` | `str` | `"chromium"` | Motor do navegador Playwright (`chromium`, `firefox`, `webkit`) |

**Retorna:** Um objeto `Scenario` finalizado com as estatísticas preenchidas.

**Exceções:**
- `FileExistsError` - Se um cenário com o mesmo nome já existir

**Comportamento:**
1. Cria uma estrutura de diretório `Scenario` no disco
2. Lança um navegador Playwright com gravação HAR habilitada
3. Injeta um MutationObserver para capturar snapshots do DOM em mudanças (com debounce de 500ms)
4. Injeta uma UI de overlay flutuante mostrando contadores em tempo real
5. Grava todo o tráfego de rede em um arquivo HAR
6. Captura eventos de navegação
7. Finaliza os metadados quando o navegador é fechado ou a parada é acionada

---

### `SnapshotManager`

**Arquivo:** `src/stuntrpa/recorder/snapshot.py`

Gerencia os snapshots do DOM recebidos do JavaScript injetado.

```python
class SnapshotManager:
    def __init__(self, scenario: Scenario)
    def create_handler(self) -> Callable[[str], Awaitable[None]]
```

#### `__init__(scenario)`

Inicializa o gerenciador com um `Scenario` alvo.

#### `create_handler()`

Retorna um callable assíncrono adequado para `page.expose_function()`. O handler:
1. Recebe uma string JSON com campos `html`, `url`, `timestamp`, `count`
2. Salva o HTML como um arquivo de snapshot numerado sequencialmente
3. Registra o evento no cenário

---

### Scripts de Injeção JavaScript

**Arquivo:** `src/stuntrpa/recorder/injection.py`

#### `MUTATION_OBSERVER_JS`

```python
MUTATION_OBSERVER_JS: str
```

JavaScript que configura um `MutationObserver` em `document.documentElement`. Em qualquer mutação do DOM (childList, subtree, attributes, characterData), aplica debounce de 500ms e captura o `outerHTML` completo, enviando-o ao Python via `window.stuntRpaOnSnapshot()`. Protege contra dupla inicialização via `window.__stuntrpa_observer_active`.

#### `OVERLAY_JS`

```python
OVERLAY_JS: str
```

JavaScript que cria um overlay de posição fixa no canto inferior direito com:
- Um ponto vermelho pulsante e o rótulo "StuntRPA REC"
- Contadores de snapshots e requisições em tempo real
- Um botão "STOP RECORDING" que chama `window.stuntRpaStopRecording()`

#### `REQUEST_COUNTER_UPDATE_JS`

```python
REQUEST_COUNTER_UPDATE_JS: str
```

JavaScript IIFE que atualiza o elemento contador de requisições no overlay. Chamado do Python com a contagem atual: `page.evaluate(f"{REQUEST_COUNTER_UPDATE_JS}({count})")`.

---

## `stuntrpa.replayer`

**Arquivo:** `src/stuntrpa/replayer/__init__.py`

### `replay_session()`

```python
async def replay_session(
    scenario_name: str,
    storage_path: Path | None = None,
    simulate_latency: bool = False,
    headless: bool = False,
    browser_type: str = "chromium",
) -> None
```

Reproduz um cenário gravado de forma bloqueante. Abre um navegador, configura a interceptação de rotas, navega para a URL inicial e aguarda o fechamento da página.

**Parâmetros:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `scenario_name` | `str` | obrigatório | Nome do cenário a reproduzir |
| `storage_path` | `Path \| None` | `None` | Diretório de armazenamento personalizado |
| `simulate_latency` | `bool` | `False` | Simular latência de rede original (limitada a 5s) |
| `headless` | `bool` | `False` | Executar navegador em modo headless |
| `browser_type` | `str` | `"chromium"` | Motor do navegador Playwright |

**Exceções:**
- `FileNotFoundError` - Se o cenário não for encontrado

---

### `create_replay_context()`

```python
async def create_replay_context(
    scenario_name: str,
    storage_path: Path | None = None,
    simulate_latency: bool = False,
    browser_type: str = "chromium",
    headless: bool = False,
    ephemeral_params: set[str] | None = None,
) -> tuple[BrowserContext, Page]
```

Cria um contexto de navegador Playwright pronto para replay com todas as rotas configuradas. Retorna `(context, page)` para uso programático.

**Parâmetros:**
| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `scenario_name` | `str` | obrigatório | Nome do cenário a reproduzir |
| `storage_path` | `Path \| None` | `None` | Diretório de armazenamento personalizado |
| `simulate_latency` | `bool` | `False` | Simular latência de rede original |
| `browser_type` | `str` | `"chromium"` | Motor do navegador Playwright |
| `headless` | `bool` | `False` | Executar navegador em modo headless |
| `ephemeral_params` | `set[str] \| None` | `None` | Parâmetros de consulta efêmeros personalizados para correspondência de URLs |

**Retorna:** Uma tupla de `(BrowserContext, Page)`. As instâncias do navegador/Playwright são limpas automaticamente quando a página é fechada.

**Uso:**

```python
context, page = await create_replay_context("meu-cenario", headless=True)
await page.goto(scenario.start_url)
# ... interaja com a página reproduzida
await context.close()
```

---

### `URLMatcher`

**Arquivo:** `src/stuntrpa/replayer/matcher.py`

Gerencia a normalização e correspondência de URLs para interceptação de rotas no replay.

```python
class URLMatcher:
    def __init__(self, ephemeral_params: set[str] | None = None)
    def normalize_url(self, url: str) -> str
    def find_best_match(self, har_entries: list[dict], url: str, method: str) -> dict | None
    @staticmethod
    def extract_response_body(response: dict) -> bytes | str
```

#### `__init__(ephemeral_params=None)`

Inicializa com um conjunto de nomes de parâmetros de consulta efêmeros a serem removidos durante a normalização. Usa `EPHEMERAL_QUERY_PARAMS` das constantes por padrão.

#### `normalize_url(url)`

Remove todos os parâmetros de consulta efêmeros da URL. A comparação é insensível a maiúsculas e minúsculas.

```python
matcher = URLMatcher()
matcher.normalize_url("https://api.com/data?_=123&key=abc")
# => "https://api.com/data?key=abc"
```

#### `find_best_match(har_entries, url, method)`

Busca nas entradas HAR pela melhor correspondência usando uma estratégia de 3 níveis:

1. **Correspondência exata** - Retorna imediatamente se a string da URL é idêntica
2. **Correspondência normalizada** - Compara URLs após remover parâmetros efêmeros
3. **Fallback de URL base** - Compara URLs ignorando todos os parâmetros de consulta

Sempre exige que o método HTTP corresponda. Retorna `None` se nenhuma correspondência for encontrada.

```python
entry = matcher.find_best_match(entries, "https://api.com/data?_=999", "GET")
```

#### `extract_response_body(response) -> bytes | str`

Método estático que extrai o corpo da resposta de um objeto de resposta HAR. Manipula conteúdo codificado em base64.

```python
body = URLMatcher.extract_response_body(entry["response"])
# Retorna str para conteúdo de texto, bytes para conteúdo binário codificado em base64
```

---

## `stuntrpa.storage`

**Arquivo:** `src/stuntrpa/storage/__init__.py`

### `Scenario`

**Arquivo:** `src/stuntrpa/storage/scenario.py`

Classe de dados principal para gerenciar cenários gravados no disco.

```python
class Scenario:
    def __init__(self, name: str, path: Path)

    # Métodos de classe
    @classmethod
    def create(cls, name: str, start_url: str, storage_path: Path | None = None) -> Scenario

    @classmethod
    def load(cls, name: str, storage_path: Path | None = None) -> Scenario

    @classmethod
    def list_all(cls, storage_path: Path | None = None) -> list[str]

    @classmethod
    def delete(cls, name: str, storage_path: Path | None = None) -> None

    # Métodos de instância
    def add_event(self, event_type: str, **details) -> None
    def increment_stat(self, key: str, amount: int = 1) -> None
    def save_snapshot(self, html: str, url: str) -> str
    def finalize(self, browser_version: str = "", playwright_version: str = "") -> None

    # Propriedades
    @property
    def start_url(self) -> str

    @property
    def stats(self) -> dict

    @property
    def created_at(self) -> str

    @property
    def events(self) -> list[dict]
```

#### Métodos de Classe

##### `Scenario.create(name, start_url, storage_path=None)`

Cria um novo diretório de cenário com `metadata.json` e subdiretório `snapshots/`. Grava os metadados iniciais.

**Exceções:** `FileExistsError` se um cenário com o mesmo nome já existir.

##### `Scenario.load(name, storage_path=None)`

Carrega um cenário existente do disco. Lê e analisa o `metadata.json`.

**Exceções:** `FileNotFoundError` se o diretório do cenário não existir.

##### `Scenario.list_all(storage_path=None)`

Retorna uma lista ordenada de todos os nomes de cenários no diretório de armazenamento. Inclui apenas diretórios que contêm um `metadata.json` válido.

##### `Scenario.delete(name, storage_path=None)`

Exclui recursivamente o diretório do cenário.

**Exceções:** `FileNotFoundError` se o cenário não existir.

#### Métodos de Instância

##### `add_event(event_type, **details)`

Adiciona um evento com timestamp à lista de eventos do cenário e persiste no `metadata.json`.

##### `increment_stat(key, amount=1)`

Incrementa uma estatística numérica nos metadados (apenas em memória, chame `_save_metadata` ou `finalize` para persistir).

##### `save_snapshot(html, url) -> str`

Salva um snapshot HTML no diretório `snapshots/` com numeração sequencial (ex.: `0001.html`). Retorna o nome do arquivo. Incrementa a estatística `total_snapshots` e cria um evento do tipo `snapshot`.

##### `finalize(browser_version="", playwright_version="")`

Calcula e registra a duração da sessão, salva as versões do navegador/Playwright e grava os metadados no disco.

#### Propriedades

| Propriedade | Tipo | Descrição |
|------------|------|-----------|
| `name` | `str` | Nome do cenário |
| `path` | `Path` | Caminho absoluto para o diretório do cenário |
| `metadata_path` | `Path` | Caminho para `metadata.json` |
| `har_path` | `Path` | Caminho para `session.har` |
| `snapshots_dir` | `Path` | Caminho para o diretório `snapshots/` |
| `start_url` | `str` | A URL inicial da sessão gravada |
| `stats` | `dict` | Estatísticas incluindo `total_requests`, `total_snapshots`, `duration_seconds` |
| `created_at` | `str` | Timestamp de criação ISO 8601 |
| `events` | `list[dict]` | Lista de eventos gravados |

---

### Utilitários de Caminho

**Arquivo:** `src/stuntrpa/storage/paths.py`

```python
def get_storage_path(custom_path: Path | None = None) -> Path
def get_scenario_path(name: str, storage_path: Path | None = None) -> Path
def get_metadata_path(scenario_dir: Path) -> Path
def get_har_path(scenario_dir: Path) -> Path
def get_snapshots_dir(scenario_dir: Path) -> Path
```

| Função | Retorna |
|--------|---------|
| `get_storage_path()` | `~/.stuntrpa/scenarios` (ou caminho personalizado). Cria o diretório se não existir. |
| `get_scenario_path(name)` | `<storage_path>/<name>` |
| `get_metadata_path(dir)` | `<dir>/metadata.json` |
| `get_har_path(dir)` | `<dir>/session.har` |
| `get_snapshots_dir(dir)` | `<dir>/snapshots` |