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

import asyncio
import logging
import sys
import tomllib
from pathlib import Path
from typing import NotRequired, TypedDict, cast

from mmc.matrix import MatrixClient
from mmc.mesh.core import MeshCoreClient
from mmc.synchronizer import SynchronizationRule, Synchronizer

from .exceptions import ExceptionBase

logger = logging.getLogger(__name__)


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


class _Config(TypedDict):
    matrix: _MatrixConfig
    meshcore: _MeshCoreConfig
    sync: list[_SyncConfig]
    logging: NotRequired[dict[str, str]]


async def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = await asyncio.to_thread(_load_config)
    except Exception:
        logger.exception("Failed to load configuration")
        raise

    log_level = config.get("logging", {}).get("level", "INFO")
    try:
        _configure_logging(log_level)
    except TypeError, ValueError:
        logger.exception("Failed to configure logging")
        raise
    logger.info("Logging configured at %s level", log_level.upper())

    matrix_config = config["matrix"]
    meshcore_config = config["meshcore"]
    rules = [
        SynchronizationRule(
            matrix_room_id=rule["matrix_room_id"],
            matrix_user_id=matrix_config["matrix_user_id"],
            meshcore_channel_idx=rule["meshcore_channel_idx"],
            meshcore_user_id=meshcore_config["meshcore_user_id"],
        )
        for rule in config["sync"]
    ]

    logger.info("Loaded %d synchronization rule(s)", len(rules))

    async with (
        MatrixClient(
            matrix_config["homeserver"], matrix_config["access_token"]
        ) as matrix,
        await MeshCoreClient.create(meshcore_config["serial_port"]) as meshcore,
    ):
        synchronizer = Synchronizer(matrix, meshcore, rules)
        try:
            logger.info("Starting Matrix and MeshCore synchronization")
            await synchronizer.run()
        except ExceptionBase as e:
            logger.exception("Synchronization stopped because of an application error")
            print(e, file=sys.stderr)


def _load_config() -> _Config:
    with Path("config.toml").open("rb") as config_file:
        return cast(_Config, tomllib.load(config_file))


def _configure_logging(level: str) -> None:
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


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
