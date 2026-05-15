import os
import sys
import tomllib
from pathlib import Path

SERVICE_NAME = "api-gateway"
SYSTEM_CONFIG_PATH = Path(f"/etc/{SERVICE_NAME}/config.toml")
DEFAULT_CONFIG_PATH = Path("config.toml")

_config: dict = {}


def _load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Warning: failed to read {path}: {exc}", file=sys.stderr)
        return {}


def load_config(explicit_path: str | None = None) -> dict:
    merged: dict = {}

    if SYSTEM_CONFIG_PATH.is_file():
        merged.update(_load_toml(SYSTEM_CONFIG_PATH))

    config_path = Path(explicit_path) if explicit_path else Path(
        os.getenv("API_GATEWAY_CONFIG_FILE", DEFAULT_CONFIG_PATH)
    )
    if config_path.is_file():
        merged.update(_load_toml(config_path))

    return merged


def init(explicit_path: str | None = None) -> dict:
    global _config
    if _config:
        return _config
    _config = load_config(explicit_path)
    return _config


def _resolve_file_env(name: str):
    file_path = os.getenv(name)
    if not file_path:
        return None
    try:
        return Path(file_path).read_text(encoding="utf-8").strip()
    except Exception as exc:
        print(f"Warning: failed to read env file {name} at {file_path}: {exc}", file=sys.stderr)
        return None


def get(key: str, default=None):
    return _config.get(key, default)


def env_or_config(*env_names: str, config_key: str | None = None, default=None):
    for env_name in env_names:
        if env_name.endswith("_FILE"):
            value = _resolve_file_env(env_name)
        else:
            value = os.getenv(env_name)
        if value is not None:
            return value
    if config_key:
        config_value = get(config_key)
        if config_value is not None:
            return config_value
    return default


init()

DOMAIN = env_or_config("DOMAIN", "GATEWAY_DOMAIN", config_key="domain", default="deine-domain.de")
API_KEY = env_or_config("API_KEY", "GATEWAY_API_KEY", config_key="api_key", default="changeme")
