# Architecture

> 🇧🇷 [Versão em português](architecture.pt-BR.md)

This document describes the internal architecture, data flow, and design decisions of StuntRPA.

## Overview

StuntRPA implements a **Record-Replay** pattern for web applications. It consists of two main pipelines:

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Recorder   │──────▶  │   Storage   │◀──────▶  │   Replayer  │
│  (capture)   │         │ (scenario)  │         │   (engine)  │
└─────────────┘         └─────────────┘         └─────────────┘
      │                       │                       │
  Playwright            HAR + JSON + HTML         Playwright
  + JS Injection        (filesystem)             + Route Interception
```

## Module Architecture

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
     │    Recorder      │              │    Replayer      │
     │                  │              │                  │
     │  capture.py      │              │  engine.py       │
     │  snapshot.py     │              │  matcher.py      │
     │  injection.py    │              │                  │
     └────────┬────────┘              └────────┬────────┘
              │                                 │
              ▼                                 ▼
     ┌─────────────────────────────────────────────────┐
     │                Storage                          │
     │                                                 │
     │  scenario.py  (CRUD + metadata + events)        │
     │  paths.py     (filesystem path resolution)      │
     └─────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  File System      │
              │  ~/.stuntrpa/     │
              │    scenarios/     │
              │      <name>/      │
              │        metadata   │
              │        session    │
              │        snapshots  │
              └──────────────────┘
```

## Recording Pipeline

The recording pipeline captures three types of data simultaneously:

### Step-by-step flow

```
  Browser                  Python (capture.py)           Storage (scenario.py)
    │                           │                              │
    │  1. Launch browser        │                              │
    │  with HAR recording       │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  2. Inject JS             │                              │
    │  (MutationObserver)       │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  3. Navigate to URL       │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  4. DOM changes           │                              │
    │────────────────────────▶  │                              │
    │  (stuntRpaOnSnapshot)     │  5. Parse JSON               │
    │                           │─────────────────────────────▶│
    │                           │  save_snapshot(html, url)     │
    │                           │                              │
    │  6. HTTP requests         │                              │
    │  (auto-captured by HAR)   │  7. increment_stat           │
    │                           │─────────────────────────────▶│
    │                           │                              │
    │  8. User clicks STOP      │                              │
    │  (stuntRpaStopRecording)  │                              │
    │────────────────────────▶  │                              │
    │                           │  9. finalize()               │
    │                           │─────────────────────────────▶│
    │                           │  (duration, versions, etc.)  │
    │                           │                              │
```

### JavaScript Injection

Three JavaScript snippets are injected into the browser:

1. **`MUTATION_OBSERVER_JS`** - Injected via `page.add_init_script()` so it runs on every page load:
   - Creates a `MutationObserver` on `document.documentElement`
   - Watches: `childList`, `subtree`, `attributes`, `characterData`
   - Debounces for 500ms before capturing
   - Sends `document.documentElement.outerHTML` to Python via `window.stuntRpaOnSnapshot()`
   - Guards against re-initialization with `window.__stuntrpa_observer_active`

2. **`OVERLAY_JS`** - Injected on every `domcontentloaded` and `load` event:
   - Creates a fixed-position overlay (z-index: 2147483647)
   - Shows live snapshot and request counters
   - Provides a STOP button that calls `window.stuntRpaStopRecording()`

3. **`REQUEST_COUNTER_UPDATE_JS`** - Called from Python on every request:
   - Updates the request counter in the overlay

### Communication Bridge

Playwright's `page.expose_function()` is used to create a JavaScript-to-Python bridge:

| JS Function | Python Handler | Purpose |
|-------------|---------------|---------|
| `stuntRpaOnSnapshot(data)` | `SnapshotManager.create_handler()` | Receives DOM snapshots |
| `stuntRpaStopRecording()` | `handle_stop()` in capture.py | Signals recording end |

## Replay Pipeline

The replay pipeline intercepts all network traffic and serves responses from the recorded HAR file.

### Step-by-step flow

```
  Browser                  Python (engine.py)           Storage (scenario.py)
    │                           │                              │
    │  1. Load scenario         │                              │
    │                           │◀─────────────────────────────│
    │                           │  Scenario.load()             │
    │                           │                              │
    │  2. Load HAR entries      │                              │
    │                           │◀─────────────────────────────│
    │                           │  _load_har_entries()         │
    │                           │                              │
    │  3. Launch browser        │                              │
    │  + setup route("**")      │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  4. Navigate to start_url │                              │
    │◀──────────────────────────│                              │
    │                           │                              │
    │  5. Request: GET /api/data│                              │
    │────────────────────────▶  │                              │
    │                           │  6. URLMatcher.find_best_match()
    │                           │     ├── exact match          │
    │                           │     ├── normalized match     │
    │                           │     └── base URL fallback    │
    │                           │                              │
    │  7. route.fulfill()       │                              │
    │◀──────────────────────────│                              │
    │  (served from HAR)        │                              │
    │                           │                              │
    │  8. Page closes           │                              │
    │────────────────────────▶  │                              │
    │                           │  9. Cleanup                  │
    │                           │                              │
```

### URL Matching Strategy

The `URLMatcher` implements a 3-tier matching strategy with priority ordering:

```
Priority 1: Exact Match
  https://api.example.com/data?key=1  ==  https://api.example.com/data?key=1
  ✓ Return immediately

Priority 2: Normalized Match
  https://api.example.com/data?_=123&key=1  ≈  https://api.example.com/data?_=456&key=1
  (after stripping ephemeral params: https://api.example.com/data?key=1)

Priority 3: Base URL Fallback
  https://api.example.com/data?any=param  ~  https://api.example.com/data?other=param
  (ignoring all query params: https://api.example.com/data)

No match → abort request (or fallback to real network)
```

The normalization process:

```
Input URL:  https://api.example.com/data?_=12345&timestamp=999&key=abc&page=1
                         │
                         ▼
              Parse query parameters
                         │
                         ▼
         Filter out ephemeral params (_, timestamp)
                         │
                         ▼
         Remaining: key=abc&page=1
                         │
                         ▼
Normalized: https://api.example.com/data?key=abc&page=1
```

### Response Fulfillment

When a match is found, the response is constructed from the HAR entry:

1. Extract status code from `entry.response.status`
2. Extract headers from `entry.response.headers` (strip `content-encoding`, `content-length`, `transfer-encoding`)
3. Extract body via `URLMatcher.extract_response_body()`:
   - If `encoding == "base64"`: decode from base64, return `bytes`
   - Otherwise: return as `str`
4. If latency simulation is enabled: `asyncio.sleep(min(entry.time / 1000, 5.0))`
5. Serve via `route.fulfill(status, headers, body)`

## Storage Layer

### Scenario Directory Structure

```
~/.stuntrpa/scenarios/<name>/
├── metadata.json           # Scenario metadata, stats, events
├── session.har             # Complete HAR 1.2 archive
└── snapshots/
    ├── 0001.html           # Full DOM snapshot
    ├── 0002.html
    └── ...
```

### Scenario Lifecycle

```
  Scenario.create(name, url)
         │
         ▼
  [Active - recording in progress]
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
  [Persisted - ready for replay]
         │
         ├── Scenario.load(name)
         ├── Scenario.list_all()
         └── Scenario.delete(name)
```

### Metadata Schema

```json
{
  "name": "string",
  "start_url": "string",
  "created_at": "ISO 8601 datetime",
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
      "timestamp": "ISO 8601 datetime",
      "url": "string (navigation events)",
      "file": "string (snapshot events)"
    }
  ]
}
```

## Design Decisions

### Why HAR format?

Playwright has built-in HAR recording via `context.record_har_path`. Using the standard HAR 1.2 format:
- No custom serialization needed for network data
- Compatible with other tools (HAR viewers, analyzers)
- Supports binary content via base64 encoding

### Why MutationObserver for snapshots?

Rather than polling or capturing on a timer, `MutationObserver` provides:
- Event-driven: only captures when the DOM actually changes
- Complete coverage: captures all mutation types (elements, attributes, text)
- Debounced: the 500ms debounce prevents excessive snapshots during rapid changes

### Why 3-tier URL matching?

During replay, URLs may differ from the original due to:
- **Ephemeral parameters**: cache busters, timestamps change between sessions
- **Different parameter values**: session tokens, nonces differ
- **New parameters**: analytics or tracking params added by the browser

The 3-tier strategy provides graceful degradation from exact to fuzzy matching.

### Why `page.expose_function`?

Playwright's `expose_function` creates a direct JS-to-Python callback without polling. This is more efficient than:
- Polling for snapshots (adds latency)
- Writing to a file and watching (I/O overhead)
- Using WebSocket (extra infrastructure)

### Cleanup Strategy

Both recorder and replayer use `try/finally` blocks to ensure browser contexts are closed even on exceptions. The `create_replay_context` function attaches a `page.on("close")` handler that automatically cleans up the browser and Playwright instance.

## Configuration

### Constants (`src/stuntrpa/constants.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_STORAGE_PATH` | `~/.stuntrpa/scenarios` | Default scenario storage location |
| `EPHEMERAL_QUERY_PARAMS` | 18 cache/tracing params | Query params stripped during URL matching |
| `SNAPSHOT_DEBOUNCE_MS` | `500` | Debounce interval for DOM mutation snapshots |

### Build Configuration (`pyproject.toml`)

| Setting | Value |
|---------|-------|
| Build system | Hatchling |
| Python version | >= 3.10 |
| Line length (Ruff) | 100 |
| Ruff target | py310 |
| License | MIT |

## Error Handling

| Scenario | Module | Behavior |
|----------|--------|----------|
| Duplicate scenario name | `Scenario.create()` | Raises `FileExistsError` |
| Scenario not found | `Scenario.load()` | Raises `FileNotFoundError` |
| Invalid HAR file | `_load_har_entries()` | Raises `FileNotFoundError` or returns empty entries |
| No URL match during replay | `engine.py` | Aborts request (`route.abort()`) with warning log |
| Failed snapshot save | `SnapshotManager` | Logs exception, continues recording |
| Browser close during recording | `capture.py` | Finalizes scenario in `finally` block |
| Page closed during replay | `engine.py` | Catches exception, closes context in `finally` |
| Invalid JSON from JS | `SnapshotManager` | Logs exception, continues recording |
