import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from stuntrpa.storage.paths import (
    get_scenario_path,
    get_snapshots_dir,
    get_storage_path,
    get_metadata_path,
    get_har_path,
)


class Scenario:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.metadata_path = get_metadata_path(path)
        self.har_path = get_har_path(path)
        self.snapshots_dir = get_snapshots_dir(path)
        self._metadata: dict = {}
        self._events: list[dict] = []
        self._start_time: datetime | None = None

    @classmethod
    def create(cls, name: str, start_url: str, storage_path: Path | None = None) -> "Scenario":
        scenario_dir = get_scenario_path(name, storage_path)
        if scenario_dir.exists():
            raise FileExistsError(f"Scenario '{name}' already exists at {scenario_dir}")
        scenario_dir.mkdir(parents=True, exist_ok=True)

        snapshots_dir = get_snapshots_dir(scenario_dir)
        snapshots_dir.mkdir(exist_ok=True)

        instance = cls(name, scenario_dir)
        instance._start_time = datetime.now(timezone.utc)
        instance._metadata = {
            "name": name,
            "start_url": start_url,
            "created_at": instance._start_time.isoformat(),
            "browser_version": "",
            "playwright_version": "",
            "events": [],
            "stats": {
                "total_requests": 0,
                "total_snapshots": 0,
                "duration_seconds": 0,
            },
        }
        instance._save_metadata()
        return instance

    @classmethod
    def load(cls, name: str, storage_path: Path | None = None) -> "Scenario":
        scenario_dir = get_scenario_path(name, storage_path)
        if not scenario_dir.exists():
            raise FileNotFoundError(f"Scenario '{name}' not found at {scenario_dir}")

        instance = cls(name, scenario_dir)
        with open(instance.metadata_path, "r", encoding="utf-8") as f:
            instance._metadata = json.load(f)
        instance._events = list(instance._metadata.get("events", []))
        instance._start_time = datetime.fromisoformat(instance._metadata["created_at"])
        return instance

    @classmethod
    def list_all(cls, storage_path: Path | None = None) -> list[str]:
        base = get_storage_path(storage_path)
        if not base.exists():
            return []
        return sorted(
            d.name
            for d in base.iterdir()
            if d.is_dir() and get_metadata_path(d).exists()
        )

    @classmethod
    def delete(cls, name: str, storage_path: Path | None = None) -> None:
        scenario_dir = get_scenario_path(name, storage_path)
        if not scenario_dir.exists():
            raise FileNotFoundError(f"Scenario '{name}' not found at {scenario_dir}")
        shutil.rmtree(scenario_dir)

    def add_event(self, event_type: str, **details) -> None:
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details,
        }
        self._events.append(event)
        self._metadata["events"] = self._events
        self._save_metadata()

    def increment_stat(self, key: str, amount: int = 1) -> None:
        if "stats" not in self._metadata:
            self._metadata["stats"] = {}
        self._metadata["stats"][key] = self._metadata["stats"].get(key, 0) + amount

    def save_snapshot(self, html: str, url: str) -> str:
        count = self._metadata["stats"].get("total_snapshots", 0) + 1
        filename = f"{count:04d}.html"
        filepath = self.snapshots_dir / filename
        filepath.write_text(html, encoding="utf-8")
        self.increment_stat("total_snapshots")
        self.add_event("snapshot", file=filename, url=url)
        return filename

    def finalize(self, browser_version: str = "", playwright_version: str = "") -> None:
        end_time = datetime.now(timezone.utc)
        self._metadata["browser_version"] = browser_version
        self._metadata["playwright_version"] = playwright_version
        if self._start_time:
            duration = (end_time - self._start_time).total_seconds()
            self._metadata["stats"]["duration_seconds"] = round(duration, 2)
        self._save_metadata()

    @property
    def start_url(self) -> str:
        return self._metadata.get("start_url", "")

    @property
    def stats(self) -> dict:
        return self._metadata.get("stats", {})

    @property
    def created_at(self) -> str:
        return self._metadata.get("created_at", "")

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def _save_metadata(self) -> None:
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2, ensure_ascii=False)
