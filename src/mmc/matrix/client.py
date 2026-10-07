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
from types import TracebackType

from cachetools import TTLCache
from nio import AsyncClient, Event, RoomMessageText, SyncError
from nio import MatrixRoom as NioMatrixRoom
from nio.responses import RoomSendError

from mmc.message import MatrixMessage, MatrixMessageToSend, MatrixRoom, MatrixUser

from .exceptions import MatrixException

MessageListener = Callable[[MatrixMessage], Awaitable[None] | None]

logger = logging.getLogger(__name__)


class MatrixClient:
    def __init__(self, client: AsyncClient, access_token: str):
        self._client: AsyncClient = client
        self._client.access_token = access_token
        self._message_listeners: list[MessageListener] = []
        self._sent_events: TTLCache[str, bool] = TTLCache[str, bool](1000, ttl=6000)

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @classmethod
    async def create(cls, homeserver: str, access_token: str) -> MatrixClient:
        logger.info("Creating Matrix client for %s", homeserver)
        return cls(AsyncClient(homeserver), access_token)

    async def close(self):
        logger.info("Closing Matrix client")
        await self._client.close()

    async def send_text(self, message: MatrixMessageToSend):
        logger.debug("Sending Matrix message to room %s", message.room)
        try:
            result = await self._client.room_send(
                message.room,
                "m.room.message",
                {
                    "msgtype": "m.text",
                    "body": message.text,
                    "format": "org.matrix.custom.html",
                    "formatted_body": message.html,
                },
            )
        except Exception as err:
            raise MatrixException("Failed to send Matrix message") from err
        if isinstance(result, RoomSendError):
            raise MatrixException(f"Failed to send Matrix message: {result}")
        self._sent_events[result.event_id] = True

    def add_message_listener(self, listener: MessageListener) -> None:
        self._message_listeners.append(listener)
        logger.debug("Registered Matrix message listener %r", listener)

    async def run(self):
        logger.info("Starting Matrix synchronization")
        try:
            first_sync_result = await self._client.sync(timeout=30000)
        except Exception as err:
            raise MatrixException("Initial Matrix sync request failed") from err
        if isinstance(first_sync_result, SyncError):
            logger.error("Initial Matrix sync failed: %s", first_sync_result)
            raise MatrixException(f"First sync error: {first_sync_result}")
        self._client.add_event_callback(self._handle_message, RoomMessageText)
        logger.info("Matrix sync initialized; waiting for messages")
        try:
            await self._client.sync_forever(timeout=30000, since=first_sync_result.next_batch)
        except Exception as err:
            raise MatrixException("Matrix sync stopped unexpectedly") from err

    async def _handle_message(self, room: NioMatrixRoom, event: Event) -> None:
        if not isinstance(event, RoomMessageText):
            return
        if not self._message_listeners or event.event_id in self._sent_events:
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
            except Exception as err:
                logger.error(
                    "Matrix message listener %r failed for room %s",
                    listener,
                    message.room.id,
                    exc_info=err,
                )

    def _map_message(self, room: NioMatrixRoom, event: RoomMessageText) -> MatrixMessage:
        return MatrixMessage(
            text=event.body,
            room=MatrixRoom(id=room.room_id, name=room.display_name),
            sender=MatrixUser(
                id=event.sender,
                name=room.user_name(event.sender) or event.sender,
            ),
        )
