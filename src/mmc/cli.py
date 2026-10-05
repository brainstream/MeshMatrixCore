import asyncio
import sys
import tomllib
from pathlib import Path
from typing import TypedDict, cast

from mmc.matrix import MatrixClient
from mmc.mesh.core import MeshCoreClient
from mmc.synchronizer import SynchronizationRule, Synchronizer

from .exceptions import ExceptionBase


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


def _load_config() -> _Config:
    with Path("config.toml").open("rb") as config_file:
        return cast(_Config, tomllib.load(config_file))


async def main():
    config = await asyncio.to_thread(_load_config)
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

    async with (
        MatrixClient(
            matrix_config["homeserver"], matrix_config["access_token"]
        ) as matrix,
        await MeshCoreClient.create(meshcore_config["serial_port"]) as meshcore,
    ):
        synchronizer = Synchronizer(matrix, meshcore, rules)
        try:
            await synchronizer.run()
        except ExceptionBase as e:
            print(e, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
