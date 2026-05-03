# StuntRPA

**Digital Twin ecosystem for RPA - Record & Replay web sessions.**

StuntRPA captures complete web sessions (network traffic, DOM snapshots, navigation events) and replays them as self-contained "digital twins" of the original web application. This enables deterministic, offline-capable RPA testing and automation without relying on live servers.

## Features

- **Session Recording** - Captures all HTTP requests/responses via HAR, DOM mutations via MutationObserver, and navigation events
- **Session Replay** - Replays recorded sessions by intercepting all network requests and serving responses from the captured HAR file
- **Smart URL Matching** - Intelligent URL normalization that strips ephemeral query parameters (`_`, `timestamp`, `nonce`, cache busters, trace IDs, etc.) for reliable matching during replay
- **Latency Simulation** - Optionally reproduces original network latency during replay (with configurable cap)
- **Live Overlay** - In-browser recording overlay showing snapshot/request counters with a stop button
- **Multiple Browser Support** - Chromium, Firefox, and WebKit via Playwright
- **CLI & Python API** - Use as a command-line tool or import as a library

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) (recommended package manager)
- [Playwright](https://playwright.dev/python/) >= 1.40.0
- Node.js (for running JavaScript validation tests)

## Installation

### Quick Use (uvx)

Run StuntRPA directly without installing it permanently:

```bash
# From PyPI (once published)
uvx stuntrpa --help
uvx stuntrpa record https://example.com my-scenario

# From a git repository
uvx --from git+https://github.com/JoaoAnacleto/StuntRPA stuntrpa --help

# Make sure Playwright browsers are available (first time only)
uvx --from git+https://github.com/JoaoAnacleto/StuntRPA playwright install
```

### Install with uv

```bash
# Clone the repository
git clone https://github.com/JoaoAnacleto/StuntRPA.git
cd StuntRPA

# Create virtual environment, resolve dependencies and install in editable mode
uv sync

# Install Playwright browsers
uv run playwright install
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| playwright | >= 1.40.0 | Browser automation and HAR recording |
| typer | >= 0.9.0 | CLI framework |
| rich | >= 13.0.0 | Terminal formatting and output |

## Quick Start

### Recording a Session

```bash
stuntrpa record https://example.com my-first-scenario
```

This opens a browser, navigates to the URL, and starts recording. A floating overlay appears in the bottom-right corner showing:
- Number of captured snapshots
- Number of captured requests
- A **STOP RECORDING** button

Interact with the page normally. When done, either:
- Click **STOP RECORDING** in the overlay
- Close the browser window
- Press `Ctrl+C` in the terminal

### Replaying a Session

```bash
stuntrpa replay my-first-scenario
```

This opens a browser that loads the recorded start URL. All network requests are intercepted and served from the captured HAR file, creating a fully offline, deterministic replay of the original session.

### Other Commands

```bash
# List all recorded scenarios
stuntrpa list

# Show detailed info about a scenario
stuntrpa info my-first-scenario

# Delete a scenario
stuntrpa delete my-first-scenario

# Show version
stuntrpa version
```

## CLI Reference

### `stuntrpa record`

Record a new web session scenario.

```
stuntrpa record [OPTIONS] URL NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `URL` | Initial URL to navigate to (required) |
| `NAME` | Scenario name (required, must be unique) |

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Custom storage directory |
| `--headless` | - | `False` | Run browser in headless mode |
| `--browser` | `-b` | `chromium` | Browser engine: `chromium`, `firefox`, `webkit` |
| `--verbose` | `-v` | `False` | Enable debug logging |

### `stuntrpa replay`

Replay a previously recorded scenario.

```
stuntrpa replay [OPTIONS] NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Scenario name to replay (required) |

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Custom storage directory |
| `--headless` | - | `False` | Run browser in headless mode |
| `--browser` | `-b` | `chromium` | Browser engine: `chromium`, `firefox`, `webkit` |
| `--simulate-latency` | `-l` | `False` | Simulate original network latency |
| `--verbose` | `-v` | `False` | Enable debug logging |

### `stuntrpa list`

List all recorded scenarios.

```
stuntrpa list [OPTIONS]
```

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Custom storage directory |

### `stuntrpa info`

Show detailed information about a scenario.

```
stuntrpa info [OPTIONS] NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Scenario name (required) |

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Custom storage directory |

### `stuntrpa delete`

Delete a recorded scenario.

```
stuntrpa delete [OPTIONS] NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Scenario name (required) |

**Options:**
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--storage` | `-s` | `~/.stuntrpa/scenarios` | Custom storage directory |
| `--yes` | `-y` | `False` | Skip confirmation prompt |

### `stuntrpa version`

Print the current version.

```
stuntrpa version
```

## Python API

StuntRPA can also be used programmatically as a Python library.

### Recording a Session

```python
import asyncio
from stuntrpa.recorder import record_session

scenario = asyncio.run(record_session(
    url="https://example.com",
    name="my-scenario",
    storage_path=None,       # uses default ~/.stuntrpa/scenarios
    headless=False,
    browser_type="chromium",
))

print(f"Recorded {scenario.stats['total_requests']} requests")
print(f"Saved {scenario.stats['total_snapshots']} snapshots")
print(f"Duration: {scenario.stats['duration_seconds']}s")
```

### Replaying a Session (Standalone)

```python
import asyncio
from stuntrpa.replayer import replay_session

asyncio.run(replay_session(
    scenario_name="my-scenario",
    storage_path=None,
    simulate_latency=True,
    headless=False,
    browser_type="chromium",
))
```

### Using `create_replay_context` (Programmatic Control)

For programmatic control over the replayed browser context (e.g., running assertions against replayed pages):

```python
import asyncio
from stuntrpa import create_replay_context

async def main():
    context, page = await create_replay_context(
        scenario_name="my-scenario",
        simulate_latency=False,
        headless=True,
        browser_type="chromium",
    )

    await page.goto("https://example.com")
    title = await page.title()
    print(f"Page title: {title}")

    # Interact with the replayed page...
    await context.close()

asyncio.run(main())
```

### Working with Scenarios

```python
from stuntrpa.storage import Scenario

# List all scenarios
names = Scenario.list_all()
print(names)  # ['my-scenario', 'another-scenario']

# Load a scenario
scenario = Scenario.load("my-scenario")
print(scenario.start_url)
print(scenario.created_at)
print(scenario.stats)
print(scenario.events)

# Delete a scenario
Scenario.delete("my-scenario")
```

### URL Matching

```python
from stuntrpa.replayer.matcher import URLMatcher

matcher = URLMatcher()

# Normalize a URL (strips ephemeral params)
normalized = matcher.normalize_url("https://api.example.com/data?_=12345&key=abc")
# => "https://api.example.com/data?key=abc"

# Custom ephemeral params
custom_matcher = URLMatcher(ephemeral_params={"session_id", "csrf_token"})

# Find best match in HAR entries
entry = matcher.find_best_match(har_entries, url="https://api.example.com/data", method="GET")
```

## Architecture

### Project Structure

```
src/stuntrpa/
  __init__.py              # Package entry point, exports create_replay_context
  constants.py             # Default paths, ephemeral params, debounce timing
  cli.py                   # Typer CLI with record, replay, list, info, delete, version
  recorder/
    __init__.py             # Exports record_session
    capture.py              # Main recording orchestrator (Playwright + HAR + snapshots)
    snapshot.py             # SnapshotManager - handles incoming DOM snapshots from JS
    injection.py            # JavaScript snippets: MutationObserver, overlay UI, counter updates
  replayer/
    __init__.py             # Exports create_replay_context, replay_session
    engine.py               # Replay engine - HAR loading, route interception, context creation
    matcher.py              # URLMatcher - URL normalization and matching strategies
  storage/
    __init__.py             # Exports Scenario
    scenario.py             # Scenario class - CRUD, metadata, snapshots, events
    paths.py                # Path resolution utilities
tests/
  test_cli.py               # CLI command tests
  test_engine.py            # HAR loading and SnapshotManager tests
  test_injection.py         # JavaScript syntax validation tests (run via Node.js)
  test_matcher.py           # URL normalization and matching tests
  test_storage.py           # Scenario CRUD, events, snapshots, and path tests
```

### How Recording Works

1. **Browser Launch** - Playwright launches a browser (Chromium/Firefox/WebKit) with HAR recording enabled
2. **JavaScript Injection** - A `MutationObserver` script is injected via `add_init_script` to watch for DOM changes
3. **Navigation** - The browser navigates to the target URL
4. **DOM Capture** - On every DOM mutation (debounced at 500ms), the full `document.documentElement.outerHTML` is serialized and sent to Python via `page.expose_function`
5. **Network Capture** - Playwright's built-in HAR recording captures all HTTP requests and responses
6. **Overlay** - A floating UI is injected into every page showing live counters and a stop button
7. **Finalization** - When recording stops, metadata (duration, browser version, stats) is written

### How Replay Works

1. **HAR Loading** - The recorded HAR file is loaded and parsed into entries
2. **Browser Launch** - A fresh Playwright browser context is created
3. **Route Interception** - All network requests (`**`) are intercepted via `context.route()`
4. **URL Matching** - For each request, the engine searches for a matching HAR entry using a 3-tier strategy:
   - **Exact match** - URL string is identical
   - **Normalized match** - URLs match after stripping ephemeral query parameters
   - **Base URL fallback** - URLs match ignoring all query parameters and fragments
5. **Response Serving** - The matched HAR entry's response is served via `route.fulfill()`
6. **Latency Simulation** - If enabled, `asyncio.sleep()` delays the response by the original request time (capped at 5s)

### Scenario Storage Format

Each scenario is stored as a directory:

```
~/.stuntrpa/scenarios/<scenario-name>/
  metadata.json       # Scenario metadata, events, and stats
  session.har         # Complete HAR archive of all network traffic
  snapshots/
    0001.html         # Sequential DOM snapshots
    0002.html
    ...
```

**metadata.json structure:**

```json
{
  "name": "my-scenario",
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

### Ephemeral Query Parameters

The following query parameters are automatically stripped during URL normalization for matching:

Cache-busting: `_`, `__`, `_t`, `_ts`, `timestamp`, `ts`, `time`, `t`, `cachebuster`, `cache_buster`, `bust`, `rand`, `random`

Tracing: `nonce`, `request_id`, `requestId`, `correlation_id`, `correlationId`, `x-request-id`, `trace_id`, `traceId`, `span_id`, `spanId`

These are defined in `src/stuntrpa/constants.py:EPHEMERAL_QUERY_PARAMS`.

## Testing

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_storage.py
pytest tests/test_matcher.py
pytest tests/test_cli.py
pytest tests/test_engine.py
pytest tests/test_injection.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=stuntrpa
```

### Test Structure

| File | What it tests |
|------|--------------|
| `test_storage.py` | Scenario CRUD, path resolution, event tracking, snapshot saving, metadata persistence |
| `test_matcher.py` | URL normalization, ephemeral param stripping, 3-tier matching strategy, base64 body extraction |
| `test_engine.py` | HAR file loading/parsing, SnapshotManager async handlers |
| `test_cli.py` | All CLI commands (version, list, info, delete, record, replay) via Typer test runner |
| `test_injection.py` | JavaScript syntax validation using Node.js subprocess |

## Development

### Setup

```bash
# Clone and enter the project
git clone https://github.com/JoaoAnacleto/StuntRPA.git
cd StuntRPA

# Create environment, install all dependencies
uv sync

# Install Playwright browsers
uv run playwright install
```

### Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting:

```bash
ruff check src/ tests/
```

Configuration is in `pyproject.toml`:
- Line length: 100
- Target: Python 3.10

### Build System

Built with [Hatchling](https://hatch.pypa.io/):

```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -e .
```

## License

MIT
