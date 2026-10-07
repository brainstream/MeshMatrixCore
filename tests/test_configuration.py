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
from pathlib import Path
from typing import Protocol, cast

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from mmc.configuration import ConfigurationError, configure_logging, load_config


class _FakeFilesystem(Protocol):
    def create_file(self, file_path: str, *, contents: str) -> object: ...


_VALID_MATRIX = (
    "[matrix]\n"
    + 'homeserver = "https://matrix.example.org"\n'
    + 'access_token = "token"\n'
    + 'matrix_user_id = "@bot:example.org"\n'
)
_VALID_MESHCORE = "[meshcore]\n" + 'serial_port = "/dev/ttyUSB0"\n' + 'meshcore_user_id = "bridge"\n'
_VALID_SYNC = "[[sync]]\n" + 'matrix_room_id = "!room:example.org"\n' + "meshcore_channel_idx = 3\n"


def _write_config_file(fs: FakeFilesystem, contents: str) -> None:
    fake_filesystem = cast(_FakeFilesystem, fs)
    _ = fake_filesystem.create_file("config.toml", contents=contents)


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

    assert load_config(Path("config.toml")) == {
        "logging": {"level": "DEBUG"},
        "matrix": {
            "homeserver": "https://matrix.example.org",
            "access_token": "token",
            "matrix_user_id": "@bot:example.org",
        },
        "meshcore": {"serial_port": "/dev/ttyUSB0", "meshcore_user_id": "bridge"},
        "sync": [{"matrix_room_id": "!room:example.org", "meshcore_channel_idx": 3}],
    }


def test_load_config_raises_when_required_table_is_missing(fs: FakeFilesystem) -> None:
    _write_config_file(fs, _VALID_MESHCORE + _VALID_SYNC)

    with pytest.raises(ConfigurationError, match=r"Configuration table 'matrix' is missing"):
        _ = load_config(Path("config.toml"))


def test_load_config_raises_when_required_key_is_missing(fs: FakeFilesystem) -> None:
    matrix_without_homeserver = "[matrix]\n" + 'access_token = "token"\n' + 'matrix_user_id = "@bot:example.org"\n'
    _write_config_file(fs, matrix_without_homeserver + _VALID_MESHCORE + _VALID_SYNC)

    with pytest.raises(ConfigurationError, match=r"Configuration key 'matrix\.homeserver' is missing"):
        _ = load_config(Path("config.toml"))


def test_load_config_raises_when_sync_array_is_missing(fs: FakeFilesystem) -> None:
    _write_config_file(fs, _VALID_MATRIX + _VALID_MESHCORE)

    with pytest.raises(ConfigurationError, match=r"Configuration array 'sync' is missing"):
        _ = load_config(Path("config.toml"))


def test_load_config_raises_when_channel_index_is_not_an_integer(fs: FakeFilesystem) -> None:
    invalid_sync = "[[sync]]\n" + 'matrix_room_id = "!room:example.org"\n' + 'meshcore_channel_idx = "three"\n'
    _write_config_file(fs, _VALID_MATRIX + _VALID_MESHCORE + invalid_sync)

    with pytest.raises(ConfigurationError, match=r"'sync\[0\]\.meshcore_channel_idx'"):
        _ = load_config(Path("config.toml"))


def test_load_config_raises_when_sync_entry_is_not_a_table(fs: FakeFilesystem) -> None:
    _write_config_file(fs, "sync = [1]\n" + _VALID_MATRIX + _VALID_MESHCORE)

    with pytest.raises(ConfigurationError, match=r"Configuration entry sync\[0\] is not a table"):
        _ = load_config(Path("config.toml"))


def test_load_config_allows_omitting_optional_logging_section(fs: FakeFilesystem) -> None:
    _write_config_file(fs, _VALID_MATRIX + _VALID_MESHCORE + _VALID_SYNC)

    assert load_config(Path("config.toml")) == {
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
        ConfigurationError,
        match="Invalid logging level 'TRACE'.*DEBUG, INFO, WARNING, ERROR, CRITICAL",
    ):
        configure_logging("TRACE")
