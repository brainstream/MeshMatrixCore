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
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    #
# See the GNU General Public License for more details.                                         #
#                                                                                              #
# You should have received a copy of the GNU General Public License along with MeshMatrixCore. #
# If not, see <http://www.gnu.org/licenses/>.                                                  #
#                                                                                              #
################################################################################################

import asyncio
from collections.abc import Awaitable, Callable
from typing import cast

import pytest

from mmc.matrix import MatrixClient
from mmc.mesh.core import MeshCoreClient
from mmc.message import (
    MatrixMessage,
    MatrixMessageToSend,
    MatrixRoom,
    MatrixUser,
    MeshCoreMessage,
    MeshCoreMessageToSend,
)
from mmc.sync import SynchronizationRule, Synchronizer

MatrixListener = Callable[[MatrixMessage], Awaitable[None] | None]
MeshCoreListener = Callable[[MeshCoreMessage], Awaitable[None] | None]


class _MatrixClientStub:
    def __init__(self) -> None:
        self.listener: MatrixListener | None = None
        self.sent_messages: list[MatrixMessageToSend] = []
        self.send_error: Exception | None = None
        self.run_error: Exception | None = None
        self.run_count: int = 0

    def add_message_listener(self, listener: MatrixListener) -> None:
        self.listener = listener

    async def send_text(self, message: MatrixMessageToSend) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent_messages.append(message)

    async def run(self) -> None:
        self.run_count += 1
        if self.run_error is not None:
            raise self.run_error


class _MeshCoreClientStub:
    def __init__(self) -> None:
        self.listener: MeshCoreListener | None = None
        self.sent_messages: list[MeshCoreMessageToSend] = []
        self.send_error: Exception | None = None
        self.run_error: Exception | None = None
        self.run_count: int = 0

    def add_message_listener(self, listener: MeshCoreListener) -> None:
        self.listener = listener

    async def send_text(self, message: MeshCoreMessageToSend) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent_messages.append(message)

    async def run(self) -> None:
        self.run_count += 1
        if self.run_error is not None:
            raise self.run_error


def test_registers_message_handlers_on_both_clients() -> None:
    matrix, meshcore, _ = make_synchronizer(rules=[])

    assert matrix.listener is not None
    assert meshcore.listener is not None


def make_synchronizer(
    rules: list[SynchronizationRule] | None = None,
) -> tuple[_MatrixClientStub, _MeshCoreClientStub, Synchronizer]:
    matrix = _MatrixClientStub()
    meshcore = _MeshCoreClientStub()
    synchronizer = Synchronizer(
        cast(MatrixClient, cast(object, matrix)),
        cast(MeshCoreClient, cast(object, meshcore)),
        rules if rules is not None else [make_rule()],
    )
    return matrix, meshcore, synchronizer


def make_rule() -> SynchronizationRule:
    return SynchronizationRule(matrix_room_id="!room:example.org", meshcore_channel_idx=7)


def dispatch_matrix_message(client: _MatrixClientStub, message: MatrixMessage) -> None:
    assert client.listener is not None
    result = client.listener(message)
    if isinstance(result, Awaitable):
        asyncio.run(result)


def dispatch_meshcore_message(client: _MeshCoreClientStub, message: MeshCoreMessage) -> None:
    assert client.listener is not None
    result = client.listener(message)
    if isinstance(result, Awaitable):
        asyncio.run(result)


def make_matrix_message(
    room_id: str = "!room:example.org",
    sender_id: str = "@alice:example.org",
    text: str = "Hello from Matrix",
) -> MatrixMessage:
    return MatrixMessage(
        room=MatrixRoom(id=room_id, name="Example"),
        sender=MatrixUser(id=sender_id, name="Alice"),
        text=text,
    )


def make_meshcore_message(
    channel: int = 7,
    sender: str | None = "alice-node",
    text: str = "Hello from MeshCore",
) -> MeshCoreMessage:
    return MeshCoreMessage(channel=channel, sender=sender, text=text)


def test_forwards_matrix_message_to_matching_meshcore_channel() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_matrix_message(matrix, make_matrix_message())

    assert meshcore.sent_messages == [MeshCoreMessageToSend(channel=7, chunks=["⚛ Alice\nHello from Matrix"])]


def test_forwards_matrix_message_from_bridge_user() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_matrix_message(matrix, make_matrix_message(sender_id="@bridge:example.org"))

    assert meshcore.sent_messages == [MeshCoreMessageToSend(channel=7, chunks=["⚛ Alice\nHello from Matrix"])]


def test_ignores_matrix_message_without_matching_room() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_matrix_message(matrix, make_matrix_message(room_id="!other:example.org"))

    assert meshcore.sent_messages == []


def test_matrix_message_echo_is_forwarded_to_matrix() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_matrix_message(matrix, make_matrix_message())
    dispatch_meshcore_message(
        meshcore,
        make_meshcore_message(text="⚛ Alice\nHello from Matrix", sender="mesh-peer"),
    )

    assert len(meshcore.sent_messages) == 1
    assert len(matrix.sent_messages) == 1


def test_forwards_meshcore_message_to_matching_matrix_room() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_meshcore_message(meshcore, make_meshcore_message())

    assert matrix.sent_messages == [
        MatrixMessageToSend(
            room="!room:example.org",
            sender="alice-node",
            text="**📟 alice-node**\n\nHello from MeshCore",
            html="<p><strong>📟 alice-node</strong></p>\n<p>Hello from MeshCore</p>",
        )
    ]


def test_forwards_meshcore_message_from_bridge_user() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_meshcore_message(meshcore, make_meshcore_message(sender="bridge-node"))

    assert len(matrix.sent_messages) == 1


def test_ignores_meshcore_message_without_matching_channel() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_meshcore_message(meshcore, make_meshcore_message(channel=99))

    assert matrix.sent_messages == []


def test_meshcore_message_echo_is_forwarded_to_meshcore() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_meshcore_message(meshcore, make_meshcore_message())
    dispatch_matrix_message(
        matrix,
        make_matrix_message(text=matrix.sent_messages[0].text, sender_id="@matrix-peer:example.org"),
    )

    assert len(matrix.sent_messages) == 1
    assert len(meshcore.sent_messages) == 1


def test_matrix_message_matching_forwarded_meshcore_payload_is_forwarded() -> None:
    matrix, meshcore, _ = make_synchronizer()

    dispatch_meshcore_message(meshcore, make_meshcore_message(text="ok"))
    dispatch_matrix_message(
        matrix,
        make_matrix_message(text="ok", sender_id="@matrix-peer:example.org"),
    )

    assert len(matrix.sent_messages) == 1
    assert meshcore.sent_messages == [MeshCoreMessageToSend(channel=7, chunks=["⚛ Alice\nok"])]


@pytest.mark.parametrize("direction", ["matrix", "meshcore"])
def test_forwarding_errors_propagate(direction: str) -> None:
    matrix, meshcore, _ = make_synchronizer()
    failure = RuntimeError("send failed")
    if direction == "matrix":
        meshcore.send_error = failure
        dispatch = lambda: dispatch_matrix_message(matrix, make_matrix_message())
    else:
        matrix.send_error = failure
        dispatch = lambda: dispatch_meshcore_message(meshcore, make_meshcore_message())

    with pytest.raises(RuntimeError, match="send failed"):
        dispatch()


def test_run_starts_both_clients() -> None:
    matrix, meshcore, synchronizer = make_synchronizer(rules=[])

    asyncio.run(synchronizer.run())

    assert matrix.run_count == 1
    assert meshcore.run_count == 1


def test_run_propagates_client_failure() -> None:
    matrix, meshcore, synchronizer = make_synchronizer(rules=[])
    matrix.run_error = RuntimeError("client failed")

    with pytest.raises(RuntimeError, match="client failed"):
        asyncio.run(synchronizer.run())

    assert matrix.run_count == 1
    assert meshcore.run_count == 1
