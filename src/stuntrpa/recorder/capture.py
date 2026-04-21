import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright

from stuntrpa.constants import SNAPSHOT_DEBOUNCE_MS
from stuntrpa.recorder.injection import MUTATION_OBSERVER_JS, OVERLAY_JS, REQUEST_COUNTER_UPDATE_JS
from stuntrpa.recorder.snapshot import SnapshotManager
from stuntrpa.storage.scenario import Scenario

logger = logging.getLogger(__name__)

_PLAYWRIGHT_VERSION: str | None = None


async def _get_playwright_version() -> str:
    global _PLAYWRIGHT_VERSION
    if _PLAYWRIGHT_VERSION is None:
        try:
            import playwright as pw
            _PLAYWRIGHT_VERSION = getattr(pw, "__version__", "unknown")
        except Exception:
            _PLAYWRIGHT_VERSION = "unknown"
    return _PLAYWRIGHT_VERSION


async def record_session(
    url: str,
    name: str,
    storage_path: Path | None = None,
    headless: bool = False,
    browser_type: str = "chromium",
) -> Scenario:
    scenario = Scenario.create(name, url, storage_path)
    snapshot_manager = SnapshotManager(scenario)

    logger.info("Starting recording session '%s' -> %s", name, url)

    async with async_playwright() as pw:
        launcher = getattr(pw, browser_type, pw.chromium)
        browser = await launcher.launch(headless=headless)

        browser_version = browser.version
        pw_version = await _get_playwright_version()

        context = await browser.new_context(
            record_har_path=str(scenario.har_path),
            record_har_omit_content=False,
        )

        page = await context.new_page()

        await page.expose_function("stuntRpaOnSnapshot", snapshot_manager.create_handler())

        recording_active = True

        async def handle_stop() -> None:
            nonlocal recording_active
            recording_active = False

        await page.expose_function("stuntRpaStopRecording", handle_stop)

        await page.add_init_script(
            MUTATION_OBSERVER_JS.replace("__DEBOUNCE_MS__", str(SNAPSHOT_DEBOUNCE_MS))
        )

        async def inject_overlay() -> None:
            try:
                await page.evaluate(OVERLAY_JS)
            except Exception:
                logger.debug("Could not inject overlay (page may be closed)")

        async def on_domcontentloaded() -> None:
            scenario.add_event("navigation", url=page.url)
            await inject_overlay()

        page.on("domcontentloaded", lambda: asyncio.ensure_future(on_domcontentloaded()))

        request_count = 0

        async def on_request(request) -> None:
            nonlocal request_count
            request_count += 1
            scenario.increment_stat("total_requests")
            try:
                await page.evaluate(f"{REQUEST_COUNTER_UPDATE_JS}({request_count})")
            except Exception:
                pass

        page.on("request", lambda req: asyncio.ensure_future(on_request(req)))

        page.on("load", lambda: asyncio.ensure_future(inject_overlay()))

        await page.goto(url, wait_until="domcontentloaded")

        logger.info("Recording active. Close the browser or click STOP to end.")

        try:
            while recording_active:
                try:
                    await asyncio.sleep(0.5)
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, stopping recording...")
                    break
        finally:
            try:
                scenario.finalize(
                    browser_version=browser_version,
                    playwright_version=pw_version,
                )
                logger.info(
                    "Recording finalized: %d requests, %d snapshots, %.1fs",
                    scenario.stats.get("total_requests", 0),
                    scenario.stats.get("total_snapshots", 0),
                    scenario.stats.get("duration_seconds", 0),
                )
            except Exception:
                logger.exception("Error finalizing scenario")

            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass

    return scenario
