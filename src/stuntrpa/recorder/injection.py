MUTATION_OBSERVER_JS = r"""
(() => {
    if (window.__stuntrpa_observer_active) return;
    window.__stuntrpa_observer_active = true;

    let debounceTimer = null;
    let snapshotCount = 0;

    function captureSnapshot() {
        snapshotCount++;
        const counter = document.getElementById('stuntrpa-snapshot-count');
        if (counter) counter.textContent = snapshotCount;

        if (typeof window.stuntRpaOnSnapshot === 'function') {
            window.stuntRpaOnSnapshot(JSON.stringify({
                html: document.documentElement.outerHTML,
                url: window.location.href,
                timestamp: Date.now(),
                count: snapshotCount,
            }));
        }
    }

    function setupObserver() {
        const target = document.documentElement;
        if (!target) return;

        new MutationObserver(() => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(captureSnapshot, 500);
        }).observe(target, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true,
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupObserver);
    } else {
        setupObserver();
    }
})();
"""

OVERLAY_JS = r"""
(() => {
    if (document.getElementById('stuntrpa-overlay')) return;
    if (!document.body) return;

    const container = document.createElement('div');
    container.id = 'stuntrpa-overlay';
    container.innerHTML = `
<div style="position:fixed; bottom:20px; right:20px; z-index:2147483647;
            background:rgba(15,15,15,0.92); color:#fff; padding:14px 18px;
            border-radius:10px; font-family:'Courier New',monospace; font-size:13px;
            box-shadow:0 4px 20px rgba(0,0,0,0.4); min-width:220px;
            border:1px solid rgba(255,68,68,0.3);">
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
        <div style="width:10px; height:10px; background:#ff4444; border-radius:50%;
                    animation: stuntrpa-pulse 1.5s ease-in-out infinite;"></div>
        <span style="font-weight:bold; letter-spacing:0.5px;">StuntRPA REC</span>
    </div>
    <div style="display:flex; flex-direction:column; gap:4px; font-size:11px; opacity:0.75;">
        <div>Snapshots: <span id="stuntrpa-snapshot-count">0</span></div>
        <div>Requests: <span id="stuntrpa-request-count">0</span></div>
    </div>
    <button id="stuntrpa-stop-btn"
            style="margin-top:10px; width:100%; padding:6px 0; background:#ff4444;
                   color:#fff; border:none; border-radius:5px; cursor:pointer;
                   font-size:12px; font-family:'Courier New',monospace;
                   font-weight:bold; letter-spacing:0.5px;">
        STOP RECORDING
    </button>
</div>
<style>
    @keyframes stuntrpa-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.85); }
    }
    #stuntrpa-stop-btn:hover { background: #cc2222; }
</style>`;
    document.body.appendChild(container);

    document.getElementById('stuntrpa-stop-btn').addEventListener('click', () => {
        if (typeof window.stuntRpaStopRecording === 'function') {
            window.stuntRpaStopRecording();
        }
    });
})();
"""

REQUEST_COUNTER_UPDATE_JS = """
((count) => {
    const el = document.getElementById('stuntrpa-request-count');
    if (el) el.textContent = count;
})
"""
