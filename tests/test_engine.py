import asyncio
import json

import pytest

from stuntrpa.replayer.engine import _load_har_entries
from stuntrpa.recorder.snapshot import SnapshotManager
from stuntrpa.storage.scenario import Scenario


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "har_test"


@pytest.fixture
def scenario(storage_dir):
    return Scenario.create("har-test", "https://example.com", storage_dir)


@pytest.fixture
def sample_har(tmp_path):
    har_data = {
        "log": {
            "version": "1.2",
            "entries": [
                {
                    "request": {"method": "GET", "url": "https://example.com/"},
                    "response": {
                        "status": 200,
                        "headers": [{"name": "content-type", "value": "text/html"}],
                        "content": {"text": "<html>Hello</html>", "encoding": ""},
                    },
                    "time": 150,
                },
                {
                    "request": {"method": "GET", "url": "https://example.com/api/data?_=9999"},
                    "response": {
                        "status": 200,
                        "headers": [{"name": "content-type", "value": "application/json"}],
                        "content": {"text": '{"items": []}', "encoding": ""},
                    },
                    "time": 50,
                },
                {
                    "request": {"method": "POST", "url": "https://example.com/api/submit"},
                    "response": {
                        "status": 201,
                        "headers": [{"name": "content-type", "value": "application/json"}],
                        "content": {"text": '{"ok": true}', "encoding": ""},
                    },
                    "time": 200,
                },
            ],
        }
    }
    har_path = tmp_path / "test.har"
    har_path.write_text(json.dumps(har_data))
    return har_path


class TestLoadHAREntries:
    def test_loads_entries(self, sample_har):
        entries = _load_har_entries(sample_har)
        assert len(entries) == 3

    def test_entry_structure(self, sample_har):
        entries = _load_har_entries(sample_har)
        entry = entries[0]
        assert entry["request"]["method"] == "GET"
        assert entry["response"]["status"] == 200

    def test_empty_har(self, tmp_path):
        har_path = tmp_path / "empty.har"
        har_path.write_text(json.dumps({"log": {"entries": []}}))
        entries = _load_har_entries(har_path)
        assert entries == []

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _load_har_entries(tmp_path / "nonexistent.har")


class TestSnapshotManager:
    def test_handler_saves_snapshot(self, scenario):
        manager = SnapshotManager(scenario)
        data = json.dumps({
            "html": "<html><body>Test</body></html>",
            "url": "https://example.com",
            "count": 1,
        })
        handler = manager.create_handler()
        asyncio.run(handler(data))
        assert scenario.stats["total_snapshots"] == 1
        assert (scenario.snapshots_dir / "0001.html").exists()

    def test_handler_handles_bad_json(self, scenario):
        manager = SnapshotManager(scenario)
        handler = manager.create_handler()
        asyncio.run(handler("not json"))
        assert scenario.stats["total_snapshots"] == 0
