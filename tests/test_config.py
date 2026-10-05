import logging

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from mmc.config import configure_logging, load_config


def test_load_config_reads_config_toml_from_current_directory(
    fs: FakeFilesystem,
) -> None:
    fs.create_file(
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
            + 'meshcore_channel_idx = 3\n'
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
