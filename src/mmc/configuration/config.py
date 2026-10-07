################################################################################################
# Copyright © 2026 Sergey Smolyannikov aka brainstream                                         #
#                                                                                              #
# This file is part of the MeshMatrixCore project — a bridge between MeshCore and Matrix.      #
#                                                                                              #
# MeshMatrixCore is free software: you can redistribute it and/or modify it under the terms of #
# the GNU General Public License as published by the Free Software Foundation,                 #
# either version 3 of the License, or (at your option) any later version.                      #
#                                                                                              #
# MeshMatrixCore is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;  #
# without even the implied warranty of  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.   #
# See the GNU General Public License for more details.                                         #
#                                                                                              #
# You should have received a copy of the GNU General Public License along with MeshMatrixCore. #
# If not, see <http://www.gnu.org/licenses/>.                                                  #
#                                                                                              #
################################################################################################

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import NotRequired, TypedDict, TypeGuard, cast

from .exceptions import ConfigurationError

_SECTION_MATRIX = "matrix"
_SECTION_MESHCORE = "meshcore"
_SECTION_SYNC = "sync"
_SECTION_LOGGING = "logging"

_HOMESERVER = "homeserver"
_ACCESS_TOKEN = "access_token"
_SERIAL_PORT = "serial_port"
_MATRIX_ROOM_ID = "matrix_room_id"
_MESHCORE_CHANNEL_IDX = "meshcore_channel_idx"


class _MatrixConfig(TypedDict):
    homeserver: str
    access_token: str


class _MeshCoreConfig(TypedDict):
    serial_port: str


class _SyncConfig(TypedDict):
    matrix_room_id: str
    meshcore_channel_idx: int


class Config(TypedDict):
    matrix: _MatrixConfig
    meshcore: _MeshCoreConfig
    sync: list[_SyncConfig]
    logging: NotRequired[dict[str, str]]


def load_config(path: Path) -> Config:
    with path.open("rb") as config_file:
        return _parse_config(cast(Mapping[str, object], tomllib.load(config_file)))


def _parse_config(raw_config: Mapping[str, object]) -> Config:
    matrix = _require_table(raw_config, _SECTION_MATRIX)
    meshcore = _require_table(raw_config, _SECTION_MESHCORE)
    sync_entries = _require_array(raw_config, _SECTION_SYNC)

    config = Config(
        matrix=_MatrixConfig(
            homeserver=_require_str(matrix.get(_HOMESERVER), f"{_SECTION_MATRIX}.{_HOMESERVER}"),
            access_token=_require_str(matrix.get(_ACCESS_TOKEN), f"{_SECTION_MATRIX}.{_ACCESS_TOKEN}"),
        ),
        meshcore=_MeshCoreConfig(
            serial_port=_require_str(meshcore.get(_SERIAL_PORT), f"{_SECTION_MESHCORE}.{_SERIAL_PORT}"),
        ),
        sync=[_parse_sync_entry(index, entry) for index, entry in enumerate(sync_entries)],
    )

    logging_table = raw_config.get(_SECTION_LOGGING)
    if logging_table is not None:
        config[_SECTION_LOGGING] = _parse_logging(logging_table)
    return config


def _require_table(config: Mapping[str, object], name: str) -> Mapping[str, object]:
    table = config.get(name)
    if not _is_table(table):
        raise ConfigurationError(f"Configuration table {name!r} is missing or is not a table")
    return table


def _is_table(value: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(value, dict)


def _require_array(config: Mapping[str, object], name: str) -> list[object]:
    array = config.get(name)
    if not _is_array(array):
        raise ConfigurationError(f"Configuration array {name!r} is missing or is not an array")
    return array


def _is_array(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _require_str(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"Configuration key {path!r} is missing or is not a string")
    return value


def _parse_sync_entry(index: int, entry: object) -> _SyncConfig:
    entry_path = f"{_SECTION_SYNC}[{index}]"
    if not _is_table(entry):
        raise ConfigurationError(f"Configuration entry {entry_path} is not a table")
    return _SyncConfig(
        matrix_room_id=_require_str(entry.get(_MATRIX_ROOM_ID), f"{entry_path}.{_MATRIX_ROOM_ID}"),
        meshcore_channel_idx=_require_int(entry.get(_MESHCORE_CHANNEL_IDX), f"{entry_path}.{_MESHCORE_CHANNEL_IDX}"),
    )


def _require_int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"Configuration key {path!r} is missing or is not an integer")
    return value


def _parse_logging(table: object) -> dict[str, str]:
    if not _is_table(table):
        raise ConfigurationError(f"Configuration table {_SECTION_LOGGING!r} is not a table")
    return {key: _require_str(value, f"{_SECTION_LOGGING}.{key}") for key, value in table.items()}
