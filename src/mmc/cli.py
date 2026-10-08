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

import argparse
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from mmc.configuration import ConfigurationError, configure_logging, load_config
from mmc.exceptions import ExceptionBase
from mmc.matrix import MatrixClient
from mmc.mesh.core import MeshCoreClient
from mmc.sync import (
    SynchronizationRule,
    Synchronizer,
)

logger = logging.getLogger(__name__)


@dataclass
class _AppArgs(argparse.Namespace):
    config: Path = Path("config.toml")


class _AppArgumentParser:
    def __init__(self):
        self._parser: argparse.ArgumentParser = argparse.ArgumentParser()
        default = _AppArgs()
        _ = self._parser.add_argument(
            "-c",
            "--config",
            metavar="PATH",
            type=Path,
            help=f"Path to configuration file (default: '{default.config}')",
        )

    def get_args(self) -> _AppArgs:
        return self._parser.parse_args(namespace=_AppArgs())


def main() -> int:
    parser = _AppArgumentParser()
    args = parser.get_args()
    try:
        return asyncio.run(run(args.config))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130


async def run(config_path: Path) -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = await asyncio.to_thread(load_config, config_path)
    except ConfigurationError:
        logger.exception("Failed to load configuration")
        return 78

    log_level = config.get("logging", {}).get("level", "INFO")
    try:
        configure_logging(log_level)
    except ConfigurationError:
        logger.exception("Failed to configure logging")
        return 78
    logger.info("Logging configured at %s level", log_level.upper())

    matrix_config = config["matrix"]
    meshcore_config = config["meshcore"]
    rules = [
        SynchronizationRule(
            matrix_room_id=rule["matrix_room_id"],
            meshcore_channel_idx=rule["meshcore_channel_idx"],
        )
        for rule in config["sync"]
    ]

    logger.info("Loaded %d synchronization rule(s)", len(rules))

    async with (
        await MatrixClient.create(matrix_config["homeserver"], matrix_config["access_token"]) as matrix,
        await MeshCoreClient.create(meshcore_config["serial_port"]) as meshcore,
    ):
        synchronizer = Synchronizer(matrix, meshcore, rules)
        try:
            logger.info("Starting Matrix and MeshCore synchronization")
            await synchronizer.run()
        except ExceptionBase:
            logger.exception("Synchronization stopped because of an application error")
            return 1

    return 0
