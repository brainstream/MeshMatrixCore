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
from typing import Protocol, cast

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from mmc.config import configure_logging, load_config


class _FakeFilesystem(Protocol):
    def create_file(self, file_path: str, *, contents: str) -> object: ...


def test_load_config_reads_config_toml_from_current_directory(
    fs: FakeFilesystem,
) -> None:
    fake_filesystem = cast(_FakeFilesystem, fs)
    _ = fake_filesystem.create_file(
        "config.toml",
        contents=(
            "[logging]\n"
            + 'level = "DEBUG"\n'
            + "[matrix]\n"
            + 'homeserver = "https://matrix.example.org"\n'
            + 'access_token = "token"\n'
            + 'matrix_user_id = "@bot:example.org"\n'
            + "[meshcore]\n"
            + 'serial_port = "/dev/ttyUSB0"\n'
            + 'meshcore_user_id = "bridge"\n'
            + "[[sync]]\n"
            + 'matrix_room_id = "!room:example.org"\n'
            + "meshcore_channel_idx = 3\n"
        ),
    )

    assert load_config() == {
        "logging": {"level": "DEBUG"},
        "matrix": {
            "homeserver": "https://matrix.example.org",
            "access_token": "token",
            "matrix_user_id": "@bot:example.org",
        },
        "meshcore": {"serial_port": "/dev/ttyUSB0", "meshcore_user_id": "bridge"},
        "sync": [{"matrix_room_id": "!room:example.org", "meshcore_channel_idx": 3}],
    }


@pytest.mark.parametrize(
    ("level", "numeric_level"),
    [
        ("DEBUG", logging.DEBUG),
        ("info", logging.INFO),
        ("WARNING", logging.WARNING),
        ("error", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
    ],
)
def test_configure_logging_sets_root_level(level: str, numeric_level: int) -> None:
    root_logger = logging.getLogger()
    original_level = root_logger.level
    try:
        configure_logging(level)
        assert root_logger.level == numeric_level
    finally:
        root_logger.setLevel(original_level)


def test_configure_logging_rejects_unsupported_level() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid logging level 'TRACE'.*DEBUG, INFO, WARNING, ERROR, CRITICAL",
    ):
        configure_logging("TRACE")
