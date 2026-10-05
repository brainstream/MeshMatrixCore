import asyncio
from collections.abc import Awaitable, Callable
from inspect import isawaitable

from meshcore import EventType, MeshCore

from .message import MeshCoreMessage

MessageListener = Callable[[MeshCoreMessage], Awaitable[None] | None]


class MeshCoreClient:
    def __init__(self, client: MeshCore):
        self._client = client
        self._message_listeners: list[MessageListener] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    @classmethod
    async def create(cls, serial_bus: str) -> MeshCoreClient:
        client = await MeshCore.create_serial(serial_bus)
        return cls(client)

    async def disconnect(self):
        await self._client.disconnect()

    async def send_text(self, channel: int, text: str):
        await self._client.commands.send_chan_msg(channel, text)

    def add_message_listener(self, listener: MessageListener) -> None:
        self._message_listeners.append(listener)

    async def run(self):
        self._client.subscribe(EventType.CHANNEL_MSG_RECV, self._handle_channel_msg)
        await self._client.connect()
        await self._client.start_auto_message_fetching()

    def _handle_channel_msg(self, event):
        if event.payload["type"] != "CHAN":
            return
        message = self._map_message_from_event(event)
        for listener in self._message_listeners:
            result = listener(message)
            if isawaitable(result):
                asyncio.ensure_future(result)

    def _map_message_from_event(self, event) -> MeshCoreMessage:
        text: str = event.payload["text"]
        user: str | None = None
        delimiter_idx = text.find(":")
        if delimiter_idx != -1:
            user = text[:delimiter_idx].strip()
            text = text[delimiter_idx + 1 :].strip()
        channel: int = event.payload["channel_idx"]
        return MeshCoreMessage(channel=channel, sender=user, text=text)
