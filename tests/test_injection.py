import subprocess

from stuntrpa.recorder.injection import (
    MUTATION_OBSERVER_JS,
    OVERLAY_JS,
    REQUEST_COUNTER_UPDATE_JS,
)

DOM_MOCK = (
    "const _els = {};"
    "const window = { __stuntrpa_observer_active: false, location: { href: '' }, "
    "  stuntRpaOnSnapshot: () => {}, stuntRpaStopRecording: () => {} };"
    "class MutationObserver { constructor(cb) { this._cb = cb; } "
    "  observe() {} disconnect() {} };"
    "const document = {"
    "  readyState: 'complete',"
    "  documentElement: { outerHTML: '<html></html>' },"
    "  body: { appendChild: (el) => { if (el && el.id) _els[el.id] = el; } },"
    "  getElementById: (id) => _els[id] || { addEventListener: () => {}, textContent: '' },"
    "  createElement: (tag) => ({ innerHTML: '', id: '', appendChild: () => {}, "
    "    addEventListener: () => {}, style: {} }),"
    "  addEventListener: () => {},"
    "};"
)


class TestMutationObserverJS:
    def test_is_valid_js_syntax(self):
        result = subprocess.run(
            ["node", "-e", DOM_MOCK + MUTATION_OBSERVER_JS],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"JS error: {result.stderr}"

    def test_contains_mutation_observer(self):
        assert "MutationObserver" in MUTATION_OBSERVER_JS

    def test_calls_exposed_function(self):
        assert "stuntRpaOnSnapshot" in MUTATION_OBSERVER_JS

    def test_debounces(self):
        assert "setTimeout" in MUTATION_OBSERVER_JS
        assert "500" in MUTATION_OBSERVER_JS

    def test_guards_double_init(self):
        assert "__stuntrpa_observer_active" in MUTATION_OBSERVER_JS


class TestOverlayJS:
    def test_is_valid_js_syntax(self):
        result = subprocess.run(
            ["node", "-e", DOM_MOCK + OVERLAY_JS],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"JS error: {result.stderr}"

    def test_has_overlay_id(self):
        assert "stuntrpa-overlay" in OVERLAY_JS

    def test_has_stop_button(self):
        assert "stuntrpa-stop-btn" in OVERLAY_JS

    def test_calls_stop_function(self):
        assert "stuntRpaStopRecording" in OVERLAY_JS

    def test_has_counters(self):
        assert "stuntrpa-snapshot-count" in OVERLAY_JS
        assert "stuntrpa-request-count" in OVERLAY_JS


class TestRequestCounterJS:
    def test_is_valid_js_syntax(self):
        result = subprocess.run(
            ["node", "-e", DOM_MOCK + f"({REQUEST_COUNTER_UPDATE_JS})(5)"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"JS error: {result.stderr}"
