import asyncio
import json
import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

from stuntrpa.replayer.matcher import URLMatcher
from stuntrpa.storage.scenario import Scenario

logger = logging.getLogger(__name__)


def _load_har_entries(har_path: Path) -> list[dict]:
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    return har.get("log", {}).get("entries", [])


async def _create_routed_context(
    context: BrowserContext,
    har_entries: list[dict],
    matcher: URLMatcher,
    simulate_latency: bool = False,
    latency_cap: float = 5.0,
    not_found_action: str = "abort",
) -> None:
    async def handle_route(route):
        url = route.request.url
        method = route.request.method

        entry = matcher.find_best_match(har_entries, url, method)

        if entry is None:
            if not_found_action == "abort":
                logger.warning("No match for %s %s - aborting", method, url)
                await route.abort()
            else:
                logger.warning("No match for %s %s - continuing", method, url)
                await route.fallback()
            return

        response = entry.get("response", {})
        status = response.get("status", 200)
        headers_list = response.get("headers", [])
        headers = {h["name"]: h["value"] for h in headers_list if "name" in h and "value" in h}

        for header_name in ("content-encoding", "content-length", "transfer-encoding"):
            headers.pop(header_name, None)

        body = URLMatcher.extract_response_body(response)

        if simulate_latency:
            original_time = entry.get("time", 0)
            if isinstance(original_time, (int, float)):
                delay = min(original_time / 1000.0, latency_cap)
                await asyncio.sleep(delay)

        fulfill_kwargs = {
            "status": status,
            "headers": headers,
        }
        if isinstance(body, bytes):
            fulfill_kwargs["body"] = body
        else:
            fulfill_kwargs["body"] = body

        try:
            await route.fulfill(**fulfill_kwargs)
            logger.debug("Served: %s %s -> %d", method, url, status)
        except Exception:
            logger.debug("Failed to serve: %s %s", method, url)

    await context.route("**", handle_route)


async def create_replay_context(
    scenario_name: str,
    storage_path: Path | None = None,
    simulate_latency: bool = False,
    browser_type: str = "chromium",
    headless: bool = False,
    ephemeral_params: set[str] | None = None,
) -> tuple[BrowserContext, Page]:
    scenario = Scenario.load(scenario_name, storage_path)
    har_entries = _load_har_entries(scenario.har_path)
    matcher = URLMatcher(ephemeral_params)

    pw = await async_playwright().start()
    launcher = getattr(pw, browser_type, pw.chromium)
    browser = await launcher.launch(headless=headless)

    context = await browser.new_context()

    await _create_routed_context(
        context,
        har_entries,
        matcher,
        simulate_latency=simulate_latency,
    )

    page = await context.new_page()

    page.on("close", lambda: asyncio.ensure_future(_cleanup(browser, pw)))

    return context, page


async def _cleanup(browser, pw) -> None:
    try:
        await browser.close()
    except Exception:
        pass
    try:
        await pw.stop()
    except Exception:
        pass


async def replay_session(
    scenario_name: str,
    storage_path: Path | None = None,
    simulate_latency: bool = False,
    headless: bool = False,
    browser_type: str = "chromium",
) -> None:
    scenario = Scenario.load(scenario_name, storage_path)
    har_entries = _load_har_entries(scenario.har_path)

    logger.info(
        "Replaying scenario '%s': %s (%d HAR entries)",
        scenario_name,
        scenario.start_url,
        len(har_entries),
    )

    matcher = URLMatcher()

    async with async_playwright() as pw:
        launcher = getattr(pw, browser_type, pw.chromium)
        browser = await launcher.launch(headless=headless)

        context = await browser.new_context()

        await _create_routed_context(
            context,
            har_entries,
            matcher,
            simulate_latency=simulate_latency,
        )

        page = await context.new_page()

        await page.goto(scenario.start_url, wait_until="domcontentloaded")

        logger.info("Replay active. Close the browser to end.")

        try:
            await page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        finally:
            try:
                await context.close()
            except Exception:
                pass
            try:
                await browser.close()
            except Exception:
                pass

    logger.info("Replay session ended.")
