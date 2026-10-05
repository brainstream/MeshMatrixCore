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
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from mmc.message import MatrixMessageToSend, MeshCoreMessageToSend
from mmc.synchronizer import Synchronizer


def test_registers_message_handlers_on_both_clients() -> None:
    matrix, meshcore, _ = make_synchronizer(rules=[])

    matrix.add_message_listener.assert_called_once()
    assert callable(matrix.add_message_listener.call_args.args[0])
    meshcore.add_message_listener.assert_called_once()
    assert callable(meshcore.add_message_listener.call_args.args[0])


def make_synchronizer(
    rules: list[Any] | None = None,
) -> tuple[Mock, Mock, Synchronizer]:
    matrix = Mock()
    matrix.add_message_listener = Mock()
    matrix.send_text = AsyncMock()
    matrix.run = AsyncMock()
    meshcore = Mock()
    meshcore.add_message_listener = Mock()
    meshcore.send_text = AsyncMock()
    meshcore.run = AsyncMock()

    synchronizer = Synchronizer(
        matrix, meshcore, rules if rules is not None else [make_rule()]
    )
    return matrix, meshcore, synchronizer


def make_rule(**overrides: object) -> Mock:
    rule = Mock()
    rule.matrix_room_id = "!room:example.org"
    rule.matrix_user_id = "@bridge:example.org"
    rule.meshcore_channel_idx = 7
    rule.meshcore_user_id = "bridge-node"
    for name, value in overrides.items():
        setattr(rule, name, value)
    return rule


def test_forwards_matrix_message_to_matching_meshcore_channel() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(matrix, make_matrix_message())

    meshcore.send_text.assert_awaited_once_with(
        MeshCoreMessageToSend(
            channel=7,
            chunks=["⚛ Alice\nHello from Matrix"],
        )
    )


def dispatch_registered_message(client: Mock, message: Mock) -> None:
    callback = client.add_message_listener.call_args.args[0]
    asyncio.run(callback(message))


def make_matrix_message(
    room_id: str = "!room:example.org", sender_id: str = "@alice:example.org"
) -> Mock:
    message = Mock()
    message.room.id = room_id
    message.sender.id = sender_id
    message.sender.name = "Alice"
    message.text = "Hello from Matrix"
    return message


def test_ignores_matrix_message_from_bridge_user() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(
        matrix, make_matrix_message(sender_id="@bridge:example.org")
    )

    meshcore.send_text.assert_not_awaited()


def test_ignores_matrix_message_without_matching_room() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(
        matrix, make_matrix_message(room_id="!other:example.org")
    )

    meshcore.send_text.assert_not_awaited()


def test_forwards_meshcore_message_to_matching_matrix_room() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(meshcore, make_meshcore_message())

    matrix.send_text.assert_awaited_once_with(
        MatrixMessageToSend(
            room="!room:example.org",
            sender="alice-node",
            text="Hello from MeshCore",
            html="<p><strong>📟 alice-node</strong></p>\n<p>Hello from MeshCore</p>",
        )
    )


def make_meshcore_message(
    channel: int = 7, sender: str | None = "alice-node"
) -> Mock:
    message = Mock()
    message.channel = channel
    message.sender = sender
    message.text = "Hello from MeshCore"
    return message


def test_ignores_meshcore_message_from_bridge_user() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(meshcore, make_meshcore_message(sender="bridge-node"))

    matrix.send_text.assert_not_awaited()


def test_ignores_meshcore_message_without_matching_channel() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_registered_message(meshcore, make_meshcore_message(channel=99))

    matrix.send_text.assert_not_awaited()


@pytest.mark.parametrize("direction", ["matrix", "meshcore"])
def test_forwarding_errors_propagate(direction: str) -> None:
    matrix, meshcore, _ = make_synchronizer()
    failure = RuntimeError("send failed")
    if direction == "matrix":
        meshcore.send_text.side_effect = failure
        callback = matrix.add_message_listener.call_args.args[0]
        coroutine: Coroutine[Any, Any, None] = callback(make_matrix_message())
    else:
        matrix.send_text.side_effect = failure
        callback = meshcore.add_message_listener.call_args.args[0]
        coroutine = callback(make_meshcore_message())

    with pytest.raises(RuntimeError, match="send failed"):
        asyncio.run(coroutine)


def test_run_starts_both_clients() -> None:
    matrix, meshcore, synchronizer = make_synchronizer(rules=[])

    asyncio.run(synchronizer.run())

    matrix.run.assert_awaited_once_with()
    meshcore.run.assert_awaited_once_with()


def test_run_propagates_client_failure() -> None:
    matrix, meshcore, synchronizer = make_synchronizer(rules=[])
    matrix.run.side_effect = RuntimeError("client failed")

    with pytest.raises(RuntimeError, match="client failed"):
        asyncio.run(synchronizer.run())

    matrix.run.assert_awaited_once_with()
    meshcore.run.assert_awaited_once_with()
