# API Reference

> 🇧🇷 [Versão em português](api.pt-BR.md)

Complete reference for all public modules, classes, and functions in StuntRPA.

---

## `stuntrpa` (top-level package)

**File:** `src/stuntrpa/__init__.py`

```python
from stuntrpa import create_replay_context, __version__
```

| Export | Type | Description |
|--------|------|-------------|
| `create_replay_context` | async function | Create a replay-ready Playwright `BrowserContext` and `Page` |
| `__version__` | `str` | Package version (`"0.1.0"`) |

---

## `stuntrpa.constants`

**File:** `src/stuntrpa/constants.py`

### `DEFAULT_STORAGE_PATH`

```python
DEFAULT_STORAGE_PATH: Path  # ~/.stuntrpa/scenarios
```

Default directory where scenarios are stored.

### `EPHEMERAL_QUERY_PARAMS`

```python
EPHEMERAL_QUERY_PARAMS: frozenset[str]
```

Set of query parameter names that are stripped during URL normalization. Includes cache-busting parameters (`_`, `timestamp`, `cachebuster`, `rand`, etc.) and tracing IDs (`nonce`, `request_id`, `trace_id`, `span_id`, etc.).

### `SNAPSHOT_DEBOUNCE_MS`

```python
SNAPSHOT_DEBOUNCE_MS: int  # 500
```

Debounce interval in milliseconds for the MutationObserver snapshot trigger. Note: the actual JS uses a hardcoded value; this constant is for reference.

---

## `stuntrpa.cli`

**File:** `src/stuntrpa/cli.py`

Typer CLI application. Entry point registered as `stuntrpa` console script.

### `app`

```python
app: typer.Typer
```

The main Typer application instance.

### Commands

#### `version()`

Prints the current version: `stuntrpa 0.1.0`

#### `record(url, name, storage, headless, browser, verbose)`

Records a new web session. Opens a browser, navigates to `url`, captures all interactions. Returns exit code 1 if a scenario with `name` already exists.

#### `replay(name, storage, headless, browser, simulate_latency, verbose)`

Replays a recorded scenario. Intercepts all network requests and serves responses from the captured HAR file. Returns exit code 1 if the scenario is not found.

#### `list_scenarios(storage)`

Lists all recorded scenarios in a formatted table with name, creation date, URL, request count, snapshot count, and duration.

#### `delete(name, storage, confirm)`

Deletes a scenario. Prompts for confirmation unless `--yes` is passed.

#### `info(name, storage)`

Displays detailed scenario information: metadata, stats, and a table of events (up to 20 shown).

---

## `stuntrpa.recorder`

**File:** `src/stuntrpa/recorder/__init__.py`

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

Records a complete web session.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Initial URL to navigate to |
| `name` | `str` | required | Unique scenario name |
| `storage_path` | `Path \| None` | `None` | Custom storage directory (uses default if `None`) |
| `headless` | `bool` | `False` | Run browser in headless mode |
| `browser_type` | `str` | `"chromium"` | Playwright browser engine (`chromium`, `firefox`, `webkit`) |

**Returns:** A finalized `Scenario` object with stats populated.

**Raises:**
- `FileExistsError` - If a scenario with the same name already exists

**Behavior:**
1. Creates a `Scenario` directory structure on disk
2. Launches a Playwright browser with HAR recording enabled
3. Injects a MutationObserver to capture DOM snapshots on changes (debounced at 500ms)
4. Injects a floating overlay UI showing live counters
5. Records all network traffic into a HAR file
6. Captures navigation events
7. Finalizes metadata when the browser is closed or stop is triggered

---

### `SnapshotManager`

**File:** `src/stuntrpa/recorder/snapshot.py`

Handles incoming DOM snapshots from the injected JavaScript.

```python
class SnapshotManager:
    def __init__(self, scenario: Scenario)
    def create_handler(self) -> Callable[[str], Awaitable[None]]
```

#### `__init__(scenario)`

Initializes the manager with a target `Scenario`.

#### `create_handler()`

Returns an async callable suitable for `page.expose_function()`. The handler:
1. Receives a JSON string with `html`, `url`, `timestamp`, `count` fields
2. Saves the HTML as a sequentially numbered snapshot file
3. Logs the event to the scenario

---

### JavaScript Injection Scripts

**File:** `src/stuntrpa/recorder/injection.py`

#### `MUTATION_OBSERVER_JS`

```python
MUTATION_OBSERVER_JS: str
```

JavaScript that sets up a `MutationObserver` on `document.documentElement`. On any DOM mutation (childList, subtree, attributes, characterData), it debounces for 500ms then captures the full `outerHTML` and sends it to Python via `window.stuntRpaOnSnapshot()`. Guards against double initialization via `window.__stuntrpa_observer_active`.

#### `OVERLAY_JS`

```python
OVERLAY_JS: str
```

JavaScript that creates a fixed-position overlay in the bottom-right corner with:
- A pulsing red dot and "StuntRPA REC" label
- Live snapshot and request counters
- A "STOP RECORDING" button that calls `window.stuntRpaStopRecording()`

#### `REQUEST_COUNTER_UPDATE_JS`

```python
REQUEST_COUNTER_UPDATE_JS: str
```

JavaScript IIFE that updates the request counter element in the overlay. Called from Python with the current count: `page.evaluate(f"{REQUEST_COUNTER_UPDATE_JS}({count})")`.

---

## `stuntrpa.replayer`

**File:** `src/stuntrpa/replayer/__init__.py`

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

Replays a recorded scenario in a blocking manner. Opens a browser, sets up route interception, navigates to the start URL, and waits for the page to close.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scenario_name` | `str` | required | Name of the scenario to replay |
| `storage_path` | `Path \| None` | `None` | Custom storage directory |
| `simulate_latency` | `bool` | `False` | Simulate original network latency (capped at 5s) |
| `headless` | `bool` | `False` | Run browser in headless mode |
| `browser_type` | `str` | `"chromium"` | Playwright browser engine |

**Raises:**
- `FileNotFoundError` - If the scenario is not found

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

Creates a replay-ready Playwright browser context with all routes configured. Returns `(context, page)` for programmatic use.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scenario_name` | `str` | required | Name of the scenario to replay |
| `storage_path` | `Path \| None` | `None` | Custom storage directory |
| `simulate_latency` | `bool` | `False` | Simulate original network latency |
| `browser_type` | `str` | `"chromium"` | Playwright browser engine |
| `headless` | `bool` | `False` | Run browser in headless mode |
| `ephemeral_params` | `set[str] \| None` | `None` | Custom ephemeral query parameters for URL matching |

**Returns:** A tuple of `(BrowserContext, Page)`. The browser/playwright instances are automatically cleaned up when the page is closed.

**Usage:**

```python
context, page = await create_replay_context("my-scenario", headless=True)
await page.goto(scenario.start_url)
# ... interact with the replayed page
await context.close()
```

---

### `URLMatcher`

**File:** `src/stuntrpa/replayer/matcher.py`

Handles URL normalization and matching for replay route interception.

```python
class URLMatcher:
    def __init__(self, ephemeral_params: set[str] | None = None)
    def normalize_url(self, url: str) -> str
    def find_best_match(self, har_entries: list[dict], url: str, method: str) -> dict | None
    @staticmethod
    def extract_response_body(response: dict) -> bytes | str
```

#### `__init__(ephemeral_params=None)`

Initializes with a set of ephemeral query parameter names to strip during normalization. Defaults to `EPHEMERAL_QUERY_PARAMS` from constants.

#### `normalize_url(url)`

Strips all ephemeral query parameters from the URL. Comparison is case-insensitive.

```python
matcher = URLMatcher()
matcher.normalize_url("https://api.com/data?_=123&key=abc")
# => "https://api.com/data?key=abc"
```

#### `find_best_match(har_entries, url, method)`

Searches HAR entries for the best match using a 3-tier strategy:

1. **Exact match** - Returns immediately if the URL string is identical
2. **Normalized match** - Compares URLs after stripping ephemeral params
3. **Base URL fallback** - Compares URLs ignoring all query parameters

Always requires HTTP method to match. Returns `None` if no match is found.

```python
entry = matcher.find_best_match(entries, "https://api.com/data?_=999", "GET")
```

#### `extract_response_body(response) -> bytes | str`

Static method that extracts the response body from a HAR response object. Handles base64-encoded content.

```python
body = URLMatcher.extract_response_body(entry["response"])
# Returns str for text content, bytes for base64-encoded binary content
```

---

## `stuntrpa.storage`

**File:** `src/stuntrpa/storage/__init__.py`

### `Scenario`

**File:** `src/stuntrpa/storage/scenario.py`

Main data class for managing recorded scenarios on disk.

```python
class Scenario:
    def __init__(self, name: str, path: Path)

    # Class methods
    @classmethod
    def create(cls, name: str, start_url: str, storage_path: Path | None = None) -> Scenario

    @classmethod
    def load(cls, name: str, storage_path: Path | None = None) -> Scenario

    @classmethod
    def list_all(cls, storage_path: Path | None = None) -> list[str]

    @classmethod
    def delete(cls, name: str, storage_path: Path | None = None) -> None

    # Instance methods
    def add_event(self, event_type: str, **details) -> None
    def increment_stat(self, key: str, amount: int = 1) -> None
    def save_snapshot(self, html: str, url: str) -> str
    def finalize(self, browser_version: str = "", playwright_version: str = "") -> None

    # Properties
    @property
    def start_url(self) -> str

    @property
    def stats(self) -> dict

    @property
    def created_at(self) -> str

    @property
    def events(self) -> list[dict]
```

#### Class Methods

##### `Scenario.create(name, start_url, storage_path=None)`

Creates a new scenario directory with `metadata.json` and `snapshots/` subdirectory. Writes initial metadata.

**Raises:** `FileExistsError` if a scenario with the same name already exists.

##### `Scenario.load(name, storage_path=None)`

Loads an existing scenario from disk. Reads and parses `metadata.json`.

**Raises:** `FileNotFoundError` if the scenario directory doesn't exist.

##### `Scenario.list_all(storage_path=None)`

Returns a sorted list of all scenario names in the storage directory. Only includes directories that contain a valid `metadata.json`.

##### `Scenario.delete(name, storage_path=None)`

Recursively deletes the scenario directory.

**Raises:** `FileNotFoundError` if the scenario doesn't exist.

#### Instance Methods

##### `add_event(event_type, **details)`

Appends a timestamped event to the scenario's event list and persists to `metadata.json`.

##### `increment_stat(key, amount=1)`

Increments a numeric stat in the metadata (in-memory only, call `_save_metadata` or `finalize` to persist).

##### `save_snapshot(html, url) -> str`

Saves an HTML snapshot to the `snapshots/` directory with sequential numbering (e.g., `0001.html`). Returns the filename. Increments `total_snapshots` stat and creates a `snapshot` event.

##### `finalize(browser_version="", playwright_version="")`

Calculates and records the session duration, saves browser/Playwright versions, and writes metadata to disk.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Scenario name |
| `path` | `Path` | Absolute path to scenario directory |
| `metadata_path` | `Path` | Path to `metadata.json` |
| `har_path` | `Path` | Path to `session.har` |
| `snapshots_dir` | `Path` | Path to `snapshots/` directory |
| `start_url` | `str` | The initial URL of the recorded session |
| `stats` | `dict` | Stats including `total_requests`, `total_snapshots`, `duration_seconds` |
| `created_at` | `str` | ISO 8601 creation timestamp |
| `events` | `list[dict]` | List of recorded events |

---

### Path Utilities

**File:** `src/stuntrpa/storage/paths.py`

```python
def get_storage_path(custom_path: Path | None = None) -> Path
def get_scenario_path(name: str, storage_path: Path | None = None) -> Path
def get_metadata_path(scenario_dir: Path) -> Path
def get_har_path(scenario_dir: Path) -> Path
def get_snapshots_dir(scenario_dir: Path) -> Path
```

| Function | Returns |
|----------|---------|
| `get_storage_path()` | `~/.stuntrpa/scenarios` (or custom path). Creates directory if it doesn't exist. |
| `get_scenario_path(name)` | `<storage_path>/<name>` |
| `get_metadata_path(dir)` | `<dir>/metadata.json` |
| `get_har_path(dir)` | `<dir>/session.har` |
| `get_snapshots_dir(dir)` | `<dir>/snapshots` |
