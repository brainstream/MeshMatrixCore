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

import logging
import tomllib
from pathlib import Path
from typing import NotRequired, TypedDict, cast


class _MatrixConfig(TypedDict):
    homeserver: str
    access_token: str
    matrix_user_id: str


class _MeshCoreConfig(TypedDict):
    serial_port: str
    meshcore_user_id: str


class _SyncConfig(TypedDict):
    matrix_room_id: str
    meshcore_channel_idx: int


class Config(TypedDict):
    matrix: _MatrixConfig
    meshcore: _MeshCoreConfig
    sync: list[_SyncConfig]
    logging: NotRequired[dict[str, str]]


def load_config() -> Config:
    with Path("config.toml").open("rb") as config_file:
        return cast(Config, tomllib.load(config_file))


def configure_logging(level: str) -> None:
    levels = {
        name: getattr(logging, name)
        for name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    }
    numeric_level = levels.get(level.upper())
    if numeric_level is None:
        supported_levels = ", ".join(levels)
        raise ValueError(
            f"Invalid logging level {level!r}. Supported levels: {supported_levels}"
        )
    logging.getLogger().setLevel(numeric_level)
