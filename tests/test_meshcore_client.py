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
from collections.abc import Callable
from typing import cast

import pytest
from meshcore import EventType, MeshCore
from meshcore.events import Event, Subscription

from mmc.mesh.core.client import MeshCoreClient
from mmc.mesh.core.exceptions import MeshCoreException
from mmc.message import MeshCoreMessage, MeshCoreMessageToSend

EventCallback = Callable[[Event], asyncio.Future[None] | None]


class CommandsStub:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []
        self.error: Exception | None = None

    async def send_chan_msg(self, channel: int, text: str) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((channel, text))


class MeshCoreStub:
    def __init__(self) -> None:
        self.callbacks: list[EventCallback] = []
        self.commands: CommandsStub = CommandsStub()
        self.connect_error: Exception | None = None
        self.fetch_error: Exception | None = None
        self.disconnect_count: int = 0
        self.connect_count: int = 0
        self.fetch_count: int = 0

    def subscribe(self, event_type: EventType, callback: EventCallback) -> Subscription:
        assert event_type == EventType.CHANNEL_MSG_RECV
        self.callbacks.append(callback)
        return Subscription(None, event_type, callback)

    async def connect(self) -> None:
        self.connect_count += 1
        if self.connect_error is not None:
            raise self.connect_error

    async def start_auto_message_fetching(self) -> None:
        self.fetch_count += 1
        if self.fetch_error is not None:
            raise self.fetch_error

    async def disconnect(self) -> None:
        self.disconnect_count += 1


class MeshCoreClientHarness:
    def __init__(self) -> None:
        self.meshcore: MeshCoreStub = MeshCoreStub()
        self.client: MeshCoreClient = MeshCoreClient(cast(MeshCore, cast(object, self.meshcore)))

    async def start(self) -> None:
        await self.client.run()

    def dispatch(self, text: str, *, channel: int = 2, event_type: str = "CHAN") -> None:
        callback = self.meshcore.callbacks[0]
        _ = callback(
            Event(
                type=EventType.CHANNEL_MSG_RECV,
                payload={"type": event_type, "channel_idx": channel, "text": text},
            )
        )


def make_harness() -> MeshCoreClientHarness:
    return MeshCoreClientHarness()


def test_create_wraps_serial_client(monkeypatch: pytest.MonkeyPatch) -> None:
    meshcore = MeshCoreStub()

    async def create_serial(serial_bus: str) -> MeshCore:
        assert serial_bus == "/dev/ttyUSB0"
        return cast(MeshCore, cast(object, meshcore))

    monkeypatch.setattr(MeshCore, "create_serial", create_serial)

    _client = asyncio.run(MeshCoreClient.create("/dev/ttyUSB0"))


def test_create_raises_when_serial_client_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def create_serial(_serial_bus: str) -> None:
        return None

    monkeypatch.setattr(MeshCore, "create_serial", create_serial)

    with pytest.raises(MeshCoreException, match="Failed to create MeshCore client"):
        _ = asyncio.run(MeshCoreClient.create("/dev/ttyUSB0"))


def test_run_subscribes_and_starts_fetching_without_extra_connect() -> None:
    harness = make_harness()

    asyncio.run(harness.start())

    assert len(harness.meshcore.callbacks) == 1
    assert harness.meshcore.connect_count == 0
    assert harness.meshcore.fetch_count == 1


def test_run_does_not_fail_on_unused_connection_error() -> None:
    harness = make_harness()
    harness.meshcore.connect_error = RuntimeError("connection failed")

    asyncio.run(harness.start())

    assert harness.meshcore.connect_count == 0
    assert harness.meshcore.fetch_count == 1


def test_run_wraps_message_fetch_failure() -> None:
    harness = make_harness()
    harness.meshcore.fetch_error = RuntimeError("fetch failed")

    with pytest.raises(MeshCoreException, match="Failed to start MeshCore message handling") as error:
        asyncio.run(harness.start())

    assert isinstance(error.value.__cause__, RuntimeError)
    assert harness.meshcore.connect_count == 0
    assert harness.meshcore.fetch_count == 1


def test_disconnect_calls_underlying_client() -> None:
    harness = make_harness()

    asyncio.run(harness.client.disconnect())

    assert harness.meshcore.disconnect_count == 1


def test_context_manager_disconnects_underlying_client() -> None:
    harness = make_harness()

    async def use_client() -> None:
        async with harness.client:
            pass

    asyncio.run(use_client())

    assert harness.meshcore.disconnect_count == 1


def test_send_text_sends_every_chunk_to_target_channel() -> None:
    harness = make_harness()
    message = MeshCoreMessageToSend(channel=3, chunks=["first", "second"])

    asyncio.run(harness.client.send_text(message))

    assert harness.meshcore.commands.sent == [(3, "first"), (3, "second")]


def test_send_text_wraps_send_failure() -> None:
    harness = make_harness()
    failure = RuntimeError("send failed")
    harness.meshcore.commands.error = failure

    with pytest.raises(MeshCoreException, match="Failed to send MeshCore message") as error:
        asyncio.run(harness.client.send_text(MeshCoreMessageToSend(channel=3, chunks=["hello"])))

    assert error.value.__cause__ is failure


def test_dispatches_channel_message_to_registered_listener() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch("BSTM: Message from MeshCore", channel=4)

    assert received == [MeshCoreMessage(channel=4, sender="BSTM", text="Message from MeshCore")]


def test_extracts_unrestricted_unicode_sender() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    sender = "名" * 40 + "🙂"
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch(f"{sender}: hello")

    assert received == [MeshCoreMessage(channel=2, sender=sender, text="hello")]


@pytest.mark.parametrize("text", ["http://example.org/status", "12:30 meeting starts"])
def test_ignores_text_without_sender_delimiter(text: str) -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch(text)

    assert received == []


def test_strips_trailing_nul_bytes_from_message() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch("BSTM: Message from MeshCore\x00\x00")

    assert received == [MeshCoreMessage(channel=2, sender="BSTM", text="Message from MeshCore")]


def test_ignores_non_channel_event_payloads() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch("BSTM: hello", event_type="OTHER")

    assert received == []


def test_ignores_non_mapping_event_payload() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())
    callback = harness.meshcore.callbacks[0]

    _ = callback(Event(type=EventType.CHANNEL_MSG_RECV, payload="not a mapping"))

    assert received == []


@pytest.mark.parametrize(
    ("payload", "error_message"),
    [
        ({"type": "CHAN", "channel_idx": 2}, "missing text"),
        ({"type": "CHAN", "text": "BSTM: hello"}, "missing channel_idx"),
    ],
)
def test_rejects_channel_messages_missing_required_fields(payload: dict[str, object], error_message: str) -> None:
    harness = make_harness()
    asyncio.run(harness.start())
    callback = harness.meshcore.callbacks[0]

    with pytest.raises(MeshCoreException, match=error_message):
        _ = callback(Event(type=EventType.CHANNEL_MSG_RECV, payload=payload))


def test_ignores_message_without_sender_or_body() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch(": hello")
    harness.dispatch("BSTM: ")

    assert received == []


def test_logs_sync_listener_failure_and_continues(caplog: pytest.LogCaptureFixture) -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []

    def listener(_message: MeshCoreMessage) -> None:
        raise RuntimeError("listener failed")

    harness.client.add_message_listener(listener)
    harness.client.add_message_listener(received.append)
    asyncio.run(harness.start())

    harness.dispatch("BSTM: hello")

    assert "MeshCore message listener" in caplog.text
    assert received == [MeshCoreMessage(channel=2, sender="BSTM", text="hello")]


def test_dispatches_async_listener() -> None:
    harness = make_harness()
    received: list[MeshCoreMessage] = []

    async def listener(message: MeshCoreMessage) -> None:
        received.append(message)

    async def dispatch() -> None:
        harness.client.add_message_listener(listener)
        await harness.start()
        harness.dispatch("BSTM: hello")
        await asyncio.sleep(0)

    asyncio.run(dispatch())

    assert received == [MeshCoreMessage(channel=2, sender="BSTM", text="hello")]


def test_logs_invalid_channel_message(caplog: pytest.LogCaptureFixture) -> None:
    harness = make_harness()
    asyncio.run(harness.start())

    harness.dispatch("not a sender message")

    assert "Received invalid MeshCore message" in caplog.text


def test_add_message_listener_registers_multiple_listeners() -> None:
    harness = make_harness()
    received: list[str] = []
    harness.client.add_message_listener(lambda message: received.append(f"first:{message.text}"))
    harness.client.add_message_listener(lambda message: received.append(f"second:{message.text}"))
    asyncio.run(harness.start())

    harness.dispatch("BSTM: hello")

    assert received == ["first:hello", "second:hello"]
