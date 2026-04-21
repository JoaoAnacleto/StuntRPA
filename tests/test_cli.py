
import pytest

from stuntrpa.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "cli_scenarios"


class TestVersion:
    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestListCommand:
    def test_list_empty(self, storage_dir):
        result = runner.invoke(app, ["list", "--storage", str(storage_dir)])
        assert result.exit_code == 0
        assert "No scenarios found" in result.stdout

    def test_list_with_scenarios(self, storage_dir):
        from stuntrpa.storage.scenario import Scenario
        Scenario.create("scen-a", "https://a.com", storage_dir)
        Scenario.create("scen-b", "https://b.com", storage_dir)

        result = runner.invoke(app, ["list", "--storage", str(storage_dir)])
        assert result.exit_code == 0
        assert "scen-a" in result.stdout
        assert "scen-b" in result.stdout


class TestInfoCommand:
    def test_info_existing(self, storage_dir):
        from stuntrpa.storage.scenario import Scenario
        Scenario.create("my-info", "https://info.com", storage_dir)

        result = runner.invoke(app, ["info", "my-info", "--storage", str(storage_dir)])
        assert result.exit_code == 0
        assert "my-info" in result.stdout
        assert "https://info.com" in result.stdout

    def test_info_nonexistent(self, storage_dir):
        result = runner.invoke(app, ["info", "nope", "--storage", str(storage_dir)])
        assert result.exit_code == 1


class TestDeleteCommand:
    def test_delete_with_confirm(self, storage_dir):
        from stuntrpa.storage.scenario import Scenario
        Scenario.create("to-delete", "https://del.com", storage_dir)

        result = runner.invoke(app, ["delete", "to-delete", "--storage", str(storage_dir), "--yes"])
        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        assert "to-delete" not in Scenario.list_all(storage_dir)

    def test_delete_nonexistent(self, storage_dir):
        result = runner.invoke(app, ["delete", "ghost", "--storage", str(storage_dir), "--yes"])
        assert result.exit_code == 1


class TestRecordCommand:
    def test_record_rejects_duplicate(self, storage_dir):
        from stuntrpa.storage.scenario import Scenario
        Scenario.create("existing", "https://e.com", storage_dir)

        result = runner.invoke(app, ["record", "https://e.com", "existing", "--storage", str(storage_dir)])
        assert result.exit_code == 1


class TestReplayCommand:
    def test_replay_nonexistent_scenario(self, storage_dir):
        result = runner.invoke(app, ["replay", "ghost", "--storage", str(storage_dir)])
        assert result.exit_code == 1
