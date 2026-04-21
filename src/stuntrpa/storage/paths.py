from pathlib import Path

from stuntrpa.constants import DEFAULT_STORAGE_PATH


def get_storage_path(custom_path: Path | None = None) -> Path:
    path = custom_path or DEFAULT_STORAGE_PATH
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_scenario_path(name: str, storage_path: Path | None = None) -> Path:
    base = get_storage_path(storage_path)
    return base / name


def get_metadata_path(scenario_dir: Path) -> Path:
    return scenario_dir / "metadata.json"


def get_har_path(scenario_dir: Path) -> Path:
    return scenario_dir / "session.har"


def get_snapshots_dir(scenario_dir: Path) -> Path:
    return scenario_dir / "snapshots"
