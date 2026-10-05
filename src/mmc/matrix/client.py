from collections.abc import Awaitable, Callable
from inspect import isawaitable

from nio import AsyncClient, Event, RoomMessageText, SyncError
from nio import MatrixRoom as NioMatrixRoom

from .exceptions import MatrixException
from .message import MatrixMessage, MatrixRoom, MatrixUser

MessageListener = Callable[[MatrixMessage], Awaitable[None] | None]


class MatrixClient:
    def __init__(self, homeserver: str, token: str):
        self._client = AsyncClient(homeserver)
        self._client.access_token = token
        self._message_listeners: list[MessageListener] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self._client.close()

    async def send_text(self, room_id: str, text: str):
        await self._client.room_send(
            room_id, "m.room.message", {"msgtype": "m.text", "body": text}
        )

    def add_message_listener(self, listener: MessageListener) -> None:
        self._message_listeners.append(listener)

    async def run(self):
        first_sync_result = await self._client.sync(timeout=30000)
        if isinstance(first_sync_result, SyncError):
            raise MatrixException(f"First sync error: {first_sync_result}")
        self._client.add_event_callback(self._handle_message, RoomMessageText)
        await self._client.sync_forever(
            timeout=30000, since=first_sync_result.next_batch
        )

    async def _handle_message(self, room: NioMatrixRoom, event: Event) -> None:
        if not isinstance(event, RoomMessageText):
            return
        if not self._message_listeners:
            return
        message = self._map_message(room, event)
        for listener in self._message_listeners:
            result = listener(message)
            if isawaitable(result):
                await result

    def _map_message(
        self, room: NioMatrixRoom, event: RoomMessageText
    ) -> MatrixMessage:
        return MatrixMessage(
            text=event.body,
            room=MatrixRoom(id=room.room_id, name=room.display_name),
            sender=MatrixUser(
                id=event.sender,
                name=room.user_name(event.sender) or event.sender,
            ),
        )
