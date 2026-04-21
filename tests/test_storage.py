import json

import pytest

from stuntrpa.storage.paths import (
    get_har_path,
    get_metadata_path,
    get_scenario_path,
    get_snapshots_dir,
    get_storage_path,
)
from stuntrpa.storage.scenario import Scenario


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "test_scenarios"


@pytest.fixture
def scenario(storage_dir):
    return Scenario.create("test-scenario", "https://example.com/login", storage_dir)


class TestPaths:
    def test_get_storage_path_creates_dir(self, storage_dir):
        result = get_storage_path(storage_dir)
        assert result == storage_dir
        assert storage_dir.exists()

    def test_get_storage_path_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("stuntrpa.storage.paths.DEFAULT_STORAGE_PATH", tmp_path / "scenarios")
        result = get_storage_path()
        assert result == tmp_path / "scenarios"
        assert result.exists()

    def test_get_scenario_path(self, storage_dir):
        result = get_scenario_path("my-scen", storage_dir)
        assert result == storage_dir / "my-scen"

    def test_get_metadata_path(self, tmp_path):
        result = get_metadata_path(tmp_path)
        assert result == tmp_path / "metadata.json"

    def test_get_har_path(self, tmp_path):
        result = get_har_path(tmp_path)
        assert result == tmp_path / "session.har"

    def test_get_snapshots_dir(self, tmp_path):
        result = get_snapshots_dir(tmp_path)
        assert result == tmp_path / "snapshots"


class TestScenarioCreate:
    def test_creates_directory_structure(self, scenario, storage_dir):
        assert scenario.path.exists()
        assert (scenario.path / "snapshots").exists()
        assert (scenario.path / "metadata.json").exists()

    def test_writes_valid_metadata(self, scenario):
        with open(scenario.metadata_path) as f:
            data = json.load(f)
        assert data["name"] == "test-scenario"
        assert data["start_url"] == "https://example.com/login"
        assert "created_at" in data
        assert data["stats"]["total_requests"] == 0
        assert data["stats"]["total_snapshots"] == 0

    def test_rejects_duplicate_name(self, storage_dir):
        Scenario.create("dup", "https://example.com", storage_dir)
        with pytest.raises(FileExistsError):
            Scenario.create("dup", "https://example.com", storage_dir)

    def test_properties(self, scenario):
        assert scenario.name == "test-scenario"
        assert scenario.start_url == "https://example.com/login"
        assert scenario.stats["total_requests"] == 0
        assert scenario.created_at != ""


class TestScenarioLoad:
    def test_loads_existing(self, scenario, storage_dir):
        loaded = Scenario.load("test-scenario", storage_dir)
        assert loaded.name == scenario.name
        assert loaded.start_url == scenario.start_url

    def test_raises_on_missing(self, storage_dir):
        with pytest.raises(FileNotFoundError):
            Scenario.load("nonexistent", storage_dir)


class TestScenarioList:
    def test_lists_scenarios(self, storage_dir):
        Scenario.create("alpha", "https://a.com", storage_dir)
        Scenario.create("beta", "https://b.com", storage_dir)
        result = Scenario.list_all(storage_dir)
        assert result == ["alpha", "beta"]

    def test_returns_empty_for_empty_dir(self, storage_dir):
        assert Scenario.list_all(storage_dir) == []

    def test_ignores_incomplete_dirs(self, storage_dir):
        storage_dir.mkdir(parents=True, exist_ok=True)
        (storage_dir / "incomplete").mkdir()
        Scenario.create("valid", "https://v.com", storage_dir)
        result = Scenario.list_all(storage_dir)
        assert result == ["valid"]


class TestScenarioDelete:
    def test_deletes_scenario(self, storage_dir):
        Scenario.create("to-delete", "https://d.com", storage_dir)
        Scenario.delete("to-delete", storage_dir)
        assert not (storage_dir / "to-delete").exists()

    def test_raises_on_missing(self, storage_dir):
        with pytest.raises(FileNotFoundError):
            Scenario.delete("nonexistent", storage_dir)


class TestScenarioEvents:
    def test_add_event(self, scenario):
        scenario.add_event("navigation", url="https://example.com/page2")
        assert len(scenario.events) == 1
        assert scenario.events[0]["type"] == "navigation"
        assert scenario.events[0]["url"] == "https://example.com/page2"

    def test_events_persist_on_load(self, scenario, storage_dir):
        scenario.add_event("snapshot", file="0001.html")
        scenario.add_event("navigation", url="https://example.com/other")
        loaded = Scenario.load("test-scenario", storage_dir)
        assert len(loaded.events) == 2

    def test_increment_stat(self, scenario):
        scenario.increment_stat("total_requests")
        scenario.increment_stat("total_requests")
        assert scenario.stats["total_requests"] == 2


class TestScenarioSnapshots:
    def test_save_snapshot(self, scenario):
        filename = scenario.save_snapshot("<html><body>Hello</body></html>", "https://example.com")
        assert filename == "0001.html"
        assert (scenario.snapshots_dir / "0001.html").exists()
        content = (scenario.snapshots_dir / "0001.html").read_text()
        assert "Hello" in content

    def test_snapshot_sequential_numbering(self, scenario):
        f1 = scenario.save_snapshot("<p>1</p>", "https://example.com")
        f2 = scenario.save_snapshot("<p>2</p>", "https://example.com")
        f3 = scenario.save_snapshot("<p>3</p>", "https://example.com")
        assert f1 == "0001.html"
        assert f2 == "0002.html"
        assert f3 == "0003.html"
        assert scenario.stats["total_snapshots"] == 3

    def test_snapshot_creates_event(self, scenario):
        scenario.save_snapshot("<html></html>", "https://example.com")
        assert len(scenario.events) == 1
        assert scenario.events[0]["type"] == "snapshot"
        assert scenario.events[0]["file"] == "0001.html"


class TestScenarioFinalize:
    def test_finalize_sets_duration(self, scenario):
        scenario.finalize(browser_version="Chrome 120", playwright_version="1.42.0")
        assert scenario.stats["duration_seconds"] >= 0
        assert scenario._metadata["browser_version"] == "Chrome 120"
        assert scenario._metadata["playwright_version"] == "1.42.0"
