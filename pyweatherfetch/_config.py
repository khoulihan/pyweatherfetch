from ctypes import ArgumentError
import os
from pathlib import Path
from decimal import Decimal
from typing import Optional, Any, Tuple

from tomlkit import document, table, dumps, loads
from tomlkit.toml_document import TOMLDocument


_config: Optional[TOMLDocument] = None

valid_units = ['standard', 'metric', 'imperial']


def _get_xdg_dir(envvar: str, default: str) -> Path:
    try:
        xdg_dir = Path(os.environ[envvar])
    except KeyError:
        xdg_dir = Path(default).expanduser()
    return xdg_dir


# TODO: Check XDG_CONFIG_DIRS as well
# Configuration files
def get_config_directory() -> Path:
    p = _get_xdg_dir('XDG_CONFIG_HOME', '~/.config') / 'pyweatherfetch'
    if not p.exists():
        p.mkdir()
    return p


# TODO: Check XDG_DATA_DIRS as well
# Important data files
def get_data_directory() -> Path:
    p = _get_xdg_dir('XDG_DATA_HOME', '~/.local/share') / 'pyweatherfetch'
    if not p.exists():
        p.mkdir()
    return p


# Cache, obviously
def get_cache_directory() -> Path:
    p = _get_xdg_dir('XDG_CACHE_HOME', '~/.cache') / 'pyweatherfetch'
    if not p.exists():
        p.mkdir()
    return p


# State data that could persist between application restarts
def get_state_directory() -> Path:
    p = _get_xdg_dir('XDG_STATE_HOME', '~/.local/state') / 'pyweatherfetch'
    if not p.exists():
        p.mkdir()
    return p


# Communication and synchronization
def get_runtime_directory() -> Path:
    p = _get_xdg_dir('XDG_RUNTIME_DIR', '~/.local/state') / 'pyweatherfetch'
    if not p.exists():
        p.mkdir()
    return p


def get_config_file(args) -> Path:
    if args != None:
        if args.config_file:
            return Path(args.config_file)
    return get_config_directory() / 'config.toml'


def _load_config() -> TOMLDocument:
    global _config
    if _config != None:
        return _config
    p = get_config_file(None)
    try:
        _config = loads(open(p).read())
    except IOError:
        _config = document()
    return _config


def _save_config() -> None:
    config = _load_config()
    p = get_config_file(None)
    with open(p, 'w') as f:
        f.write(dumps(config))


def _get_config_variable(section: str, key: str, default: Any) -> Any:
    config = _load_config()
    t = config.get(section)
    if t == None:
        return default
    return t.get(key, default)


def _set_config_variable(section: str, key: str, value: Any) -> None:
    config = _load_config()
    t = config.get(section)
    if t == None:
        t = table()
        config[section] = t
    t[key] = value


def _delete_config_variable(section: str, key: str) -> None:
    config = _load_config()
    t = config.get(section)
    if t == None:
        raise ArgumentError("Specified section does not exist")
    del t[key]


def get_cache_duration() -> int:
    # Minutes
    return _get_config_variable('general', 'cache_duration', 30)


def set_cache_duration(value: int) -> None:
    _set_config_variable('general', 'cache_duration', value)
    _save_config()


def get_units() -> str:
    return _get_config_variable('general', 'units', 'metric')


def set_units(value: str):
    if value not in valid_units:
        raise ValueError("Invalid units")
    _set_config_variable('general', 'units', value)
    _save_config()


def get_api_key() -> str:
    return _get_config_variable('general', 'api_key', None)


def set_api_key(value: str) -> None:
    _set_config_variable('general', 'api_key', value)
    _save_config()


def save_named_location(name: str, latitude: Decimal, longitude: Decimal) -> None:
    _set_config_variable(
        'locations',
        name,
        { 'latitude': latitude, 'longitude': longitude }
    )
    _save_config()


def get_named_location(name: str) -> Tuple[Decimal, Decimal]:
    d = _get_config_variable('locations', name, None)
    if d == None:
        raise ArgumentError("Named location not found.")
    return (d['latitude'], d['longitude'])


def set_default_location(name: str) -> None:
    _set_config_variable('general', 'default_location', name)
    _save_config()


def get_default_location() -> str:
    return _get_config_variable('general', 'default_location', None)


def delete_location(name: str) -> None:
    d = get_default_location()
    if d == name:
        _delete_config_variable('general', 'default_location')
    _delete_config_variable('locations', name)
    _save_config()


def save_template(name: str, template: str) -> None:
    # TODO: Do we need to ensure template is escaped?
    _set_config_variable('templates', name, template)
    _save_config()


def get_template(name: str) -> str:
    # TODO: And do we need to un-escape here?
    return _get_config_variable('templates', name, None)


def delete_template(name: str) -> None:
    d = get_default_template()
    if d == name:
        _delete_config_variable('general', 'default_template')
    _delete_config_variable('templates', name)
    _save_config()


def set_default_template(name: str) -> None:
    _set_config_variable('general', 'default_template', name)
    _save_config()


def get_default_template() -> str:
    return _get_config_variable('general', 'default_template', None)

