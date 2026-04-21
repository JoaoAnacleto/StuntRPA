import json
import logging
from typing import Awaitable, Callable

from stuntrpa.storage.scenario import Scenario

logger = logging.getLogger(__name__)


class SnapshotManager:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self._pending_count = 0

    def create_handler(self) -> Callable[[str], Awaitable[None]]:
        async def handle_snapshot(data: str) -> None:
            try:
                payload = json.loads(data)
                html = payload.get("html", "")
                url = payload.get("url", "")
                self._pending_count += 1

                filename = self.scenario.save_snapshot(html, url)
                logger.info("Snapshot #%d saved: %s (url=%s)", self._pending_count, filename, url)
            except Exception:
                logger.exception("Failed to save snapshot")

        return handle_snapshot
