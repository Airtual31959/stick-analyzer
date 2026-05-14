"""应用路径规则。"""

from pathlib import Path
from typing import Mapping


def get_app_data_dir(home_dir: Path | str | None = None) -> Path:
    """返回应用私有数据目录，避免把录制文件混在程序目录。"""
    home = Path.home() if home_dir is None else Path(home_dir)
    return home / ".stickanalyzer"


def get_config_path(home_dir: Path | str | None = None) -> Path:
    return get_app_data_dir(home_dir) / "config.json"


def get_default_output_dir(home_dir: Path | str | None = None) -> Path:
    return get_app_data_dir(home_dir) / "data"


def resolve_output_dir(
    cfg: Mapping[str, object] | None,
    home_dir: Path | str | None = None,
) -> Path:
    raw = str((cfg or {}).get("out_dir") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return get_default_output_dir(home_dir)
