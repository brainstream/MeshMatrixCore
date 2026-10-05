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
from collections.abc import Awaitable, Callable
from inspect import isawaitable

from nio import AsyncClient, Event, RoomMessageText, SyncError
from nio import MatrixRoom as NioMatrixRoom

from .exceptions import MatrixException
from .message import MatrixMessage, MatrixRoom, MatrixUser

MessageListener = Callable[[MatrixMessage], Awaitable[None] | None]

logger = logging.getLogger(__name__)


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
        logger.info("Closing Matrix client")
        await self._client.close()

    async def send_text(self, room_id: str, text: str):
        logger.debug("Sending Matrix message to room %s", room_id)
        try:
            await self._client.room_send(
                room_id, "m.room.message", {"msgtype": "m.text", "body": text}
            )
        except Exception:
            logger.exception("Failed to send Matrix message to room %s", room_id)
            raise

    def add_message_listener(self, listener: MessageListener) -> None:
        self._message_listeners.append(listener)
        logger.debug("Registered Matrix message listener %r", listener)

    async def run(self):
        logger.info("Starting Matrix synchronization")
        try:
            first_sync_result = await self._client.sync(timeout=30000)
        except Exception:
            logger.exception("Initial Matrix sync request failed")
            raise
        if isinstance(first_sync_result, SyncError):
            logger.error("Initial Matrix sync failed: %s", first_sync_result)
            raise MatrixException(f"First sync error: {first_sync_result}")
        self._client.add_event_callback(self._handle_message, RoomMessageText)
        logger.info("Matrix sync initialized; waiting for messages")
        try:
            await self._client.sync_forever(
                timeout=30000, since=first_sync_result.next_batch
            )
        except Exception:
            logger.exception("Matrix sync stopped unexpectedly")
            raise

    async def _handle_message(self, room: NioMatrixRoom, event: Event) -> None:
        if not isinstance(event, RoomMessageText):
            return
        if not self._message_listeners:
            return
        message = self._map_message(room, event)
        logger.debug(
            "Received Matrix message in room %s from %s",
            message.room.id,
            message.sender.id,
        )
        for listener in self._message_listeners:
            try:
                result = listener(message)
                if isawaitable(result):
                    await result
            except Exception:
                logger.exception(
                    "Matrix message listener %r failed for room %s",
                    listener,
                    message.room.id,
                )
                raise

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
