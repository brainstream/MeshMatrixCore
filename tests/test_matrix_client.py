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
from collections.abc import Awaitable, Callable
from typing import cast

import pytest
from nio import AsyncClient, Event, RoomMessageText, SyncError
from nio import MatrixRoom as NioMatrixRoom
from nio.responses import RoomSendError

from mmc.matrix.client import MatrixClient
from mmc.matrix.exceptions import MatrixException
from mmc.message import MatrixMessage, MatrixMessageToSend, MatrixRoom, MatrixUser

EventCallback = Callable[[NioMatrixRoom, Event], Awaitable[None]]


class AsyncClientStub:
    def __init__(self) -> None:
        self.access_token: str | None = None
        self.close_count: int = 0
        self.send_call: tuple[str, str, dict[str, str]] | None = None
        self.send_result: object = object()
        self.send_error: Exception | None = None
        self.sync_result: object = type("SyncResult", (), {"next_batch": "batch-1"})()
        self.sync_error: Exception | None = None
        self.sync_forever_error: Exception | None = None
        self.sync_call: dict[str, int] | None = None
        self.sync_forever_call: dict[str, int | str] | None = None
        self.event_callback: EventCallback | None = None
        self.event_type: type[Event] | None = None

    async def close(self) -> None:
        self.close_count += 1

    async def room_send(self, room: str, event_type: str, content: dict[str, str]) -> object:
        self.send_call = (room, event_type, content)
        if self.send_error is not None:
            raise self.send_error
        return self.send_result

    async def sync(self, *, timeout: int) -> object:
        self.sync_call = {"timeout": timeout}
        if self.sync_error is not None:
            raise self.sync_error
        return self.sync_result

    def add_event_callback(self, callback: EventCallback, event_type: type[Event]) -> None:
        self.event_callback = callback
        self.event_type = event_type

    async def sync_forever(self, *, timeout: int, since: str) -> None:
        self.sync_forever_call = {"timeout": timeout, "since": since}
        if self.sync_forever_error is not None:
            raise self.sync_forever_error


class MatrixClientHarness:
    def __init__(self) -> None:
        self.nio: AsyncClientStub = AsyncClientStub()
        self.client: MatrixClient = MatrixClient(cast(AsyncClient, cast(object, self.nio)), "access-token")

    async def start(self) -> None:
        await self.client.run()

    async def dispatch(self, room: NioMatrixRoom, event: Event) -> None:
        if self.nio.event_callback is None:
            await self.start()
        assert self.nio.event_callback is not None
        await self.nio.event_callback(room, event)


def make_harness() -> MatrixClientHarness:
    return MatrixClientHarness()


def make_room(
    *,
    room_id: str = "!room:example.org",
    name: str = "Example Room",
    user_name: str | None = "Alice",
) -> NioMatrixRoom:
    class RoomStub:
        room_id: str
        display_name: str

        def __init__(self) -> None:
            self.room_id = room_id
            self.display_name = name

        def user_name(self, _user_id: str) -> str | None:
            return user_name

    return cast(NioMatrixRoom, cast(object, RoomStub()))


def make_event(*, sender: str = "@alice:example.org", body: str = "hello") -> RoomMessageText:
    return RoomMessageText(
        source={
            "event_id": "$event:example.org",
            "sender": sender,
            "origin_server_ts": 0,
            "type": "m.room.message",
            "content": {"msgtype": "m.text", "body": body},
        },
        body=body,
        formatted_body=None,
        format=None,
    )


def test_init_sets_access_token() -> None:
    harness = make_harness()

    assert harness.nio.access_token == "access-token"


def test_create_wraps_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    nio = AsyncClientStub()

    def make_async_client(homeserver: str) -> AsyncClient:
        assert homeserver == "https://matrix.example.org"
        return cast(AsyncClient, cast(object, nio))

    monkeypatch.setattr("mmc.matrix.client.AsyncClient", make_async_client)

    client = asyncio.run(MatrixClient.create("https://matrix.example.org", "access-token"))

    assert isinstance(client, MatrixClient)
    assert nio.access_token == "access-token"


def test_close_calls_underlying_client() -> None:
    harness = make_harness()

    asyncio.run(harness.client.close())

    assert harness.nio.close_count == 1


def test_context_manager_closes_underlying_client() -> None:
    harness = make_harness()

    async def use_client() -> None:
        async with harness.client:
            pass

    asyncio.run(use_client())

    assert harness.nio.close_count == 1


def test_send_text_sends_formatted_matrix_message() -> None:
    harness = make_harness()
    message = MatrixMessageToSend(
        room="!room:example.org",
        sender="alice",
        text="Hello from MeshCore",
        html="<p>Hello from MeshCore</p>",
    )

    asyncio.run(harness.client.send_text(message))

    assert harness.nio.send_call == (
        "!room:example.org",
        "m.room.message",
        {
            "msgtype": "m.text",
            "body": "Hello from MeshCore",
            "format": "org.matrix.custom.html",
            "formatted_body": "<p>Hello from MeshCore</p>",
        },
    )


def test_send_text_wraps_send_failure() -> None:
    harness = make_harness()
    failure = RuntimeError("send failed")
    harness.nio.send_error = failure

    with pytest.raises(MatrixException, match="Failed to send Matrix message") as error:
        asyncio.run(
            harness.client.send_text(
                MatrixMessageToSend(room="!room:example.org", sender="alice", text="hello", html="<p>hello</p>")
            )
        )

    assert error.value.__cause__ is failure


def test_send_text_raises_when_server_returns_send_error() -> None:
    harness = make_harness()
    harness.nio.send_result = RoomSendError("Forbidden", status_code="M_FORBIDDEN")

    with pytest.raises(MatrixException, match="Failed to send Matrix message: RoomSendError: M_FORBIDDEN Forbidden"):
        asyncio.run(
            harness.client.send_text(
                MatrixMessageToSend(room="!room:example.org", sender="alice", text="hello", html="<p>hello</p>")
            )
        )


def test_run_syncs_registers_callback_and_continues_from_initial_batch() -> None:
    harness = make_harness()

    asyncio.run(harness.start())

    assert harness.nio.sync_call == {"timeout": 30000}
    assert harness.nio.event_callback is not None
    assert harness.nio.event_type is RoomMessageText
    assert harness.nio.sync_forever_call == {"timeout": 30000, "since": "batch-1"}


def test_run_wraps_initial_sync_exception() -> None:
    harness = make_harness()
    failure = RuntimeError("connection failed")
    harness.nio.sync_error = failure

    with pytest.raises(MatrixException, match="Initial Matrix sync request failed") as error:
        asyncio.run(harness.start())

    assert error.value.__cause__ is failure
    assert harness.nio.event_callback is None


def test_run_raises_for_initial_sync_error_response() -> None:
    harness = make_harness()
    harness.nio.sync_result = SyncError("M_UNKNOWN: sync failed")

    with pytest.raises(MatrixException, match="First sync error: SyncError: M_UNKNOWN: sync failed"):
        asyncio.run(harness.start())

    assert harness.nio.event_callback is None
    assert harness.nio.sync_forever_call is None


def test_run_wraps_sync_forever_exception() -> None:
    harness = make_harness()
    failure = RuntimeError("sync stopped")
    harness.nio.sync_forever_error = failure

    with pytest.raises(MatrixException, match="Matrix sync stopped unexpectedly") as error:
        asyncio.run(harness.start())

    assert error.value.__cause__ is failure
    assert harness.nio.event_callback is not None


def test_dispatches_message_to_registered_listener() -> None:
    harness = make_harness()
    received: list[MatrixMessage] = []
    harness.client.add_message_listener(received.append)

    asyncio.run(harness.dispatch(make_room(), make_event()))

    assert received == [
        MatrixMessage(
            text="hello",
            room=MatrixRoom(id="!room:example.org", name="Example Room"),
            sender=MatrixUser(id="@alice:example.org", name="Alice"),
        )
    ]


def test_sender_id_is_used_when_room_has_no_display_name_for_sender() -> None:
    harness = make_harness()
    received: list[MatrixMessage] = []
    harness.client.add_message_listener(received.append)

    asyncio.run(harness.dispatch(make_room(user_name=None), make_event()))

    assert len(received) == 1
    assert received[0].sender == MatrixUser(id="@alice:example.org", name="@alice:example.org")


def test_ignores_non_text_event() -> None:
    harness = make_harness()
    received: list[MatrixMessage] = []
    harness.client.add_message_listener(received.append)

    asyncio.run(harness.dispatch(make_room(), cast(Event, object())))

    assert received == []


def test_ignores_text_event_when_there_are_no_listeners() -> None:
    harness = make_harness()

    asyncio.run(harness.dispatch(make_room(), make_event()))


def test_dispatches_message_to_multiple_listeners_in_registration_order() -> None:
    harness = make_harness()
    received: list[str] = []
    harness.client.add_message_listener(lambda message: received.append(f"first:{message.text}"))
    harness.client.add_message_listener(lambda message: received.append(f"second:{message.text}"))

    asyncio.run(harness.dispatch(make_room(), make_event(body="hello")))

    assert received == ["first:hello", "second:hello"]


def test_dispatches_async_listener() -> None:
    harness = make_harness()
    received: list[MatrixMessage] = []

    async def listener(message: MatrixMessage) -> None:
        received.append(message)

    async def dispatch() -> None:
        harness.client.add_message_listener(listener)
        await harness.dispatch(make_room(), make_event())

    asyncio.run(dispatch())

    assert len(received) == 1
    assert received[0].text == "hello"


def test_logs_listener_failure_and_continues_to_next_listener(caplog: pytest.LogCaptureFixture) -> None:
    harness = make_harness()
    received: list[MatrixMessage] = []

    def broken_listener(_message: MatrixMessage) -> None:
        raise RuntimeError("listener failed")

    harness.client.add_message_listener(broken_listener)
    harness.client.add_message_listener(received.append)

    asyncio.run(harness.dispatch(make_room(), make_event()))

    assert "Matrix message listener" in caplog.text
    assert "listener failed" in caplog.text
    assert len(received) == 1
    assert received[0].text == "hello"
