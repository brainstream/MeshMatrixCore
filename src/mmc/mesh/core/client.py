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
import logging
from collections.abc import Awaitable, Callable, Coroutine
from inspect import isawaitable
from types import TracebackType
from typing import Self, cast

from meshcore import EventType, MeshCore
from meshcore.events import Event, Subscription

from mmc.message.message import MeshCoreMessage, MeshCoreMessageToSend

from .exceptions import MeshCoreException

MessageListener = Callable[[MeshCoreMessage], Awaitable[None] | None]
logger = logging.getLogger(__name__)


class MeshCoreClient:
    def __init__(self, client: MeshCore):
        self._client: MeshCore = client
        self._message_listeners: list[MessageListener] = []
        self._subscription: Subscription | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self.disconnect()

    @classmethod
    async def create(cls, serial_bus: str) -> MeshCoreClient:
        logger.info("Connecting to MeshCore device on %s", serial_bus)
        client = await cast(
            Callable[[str], Coroutine[object, object, MeshCore | None]],
            MeshCore.create_serial,
        )(serial_bus)
        if client is None:
            raise MeshCoreException(f"Failed to create MeshCore client on {serial_bus}")
        return cls(client)

    async def disconnect(self):
        logger.info("Disconnecting MeshCore client")
        await self._client.disconnect()

    async def send_text(self, message: MeshCoreMessageToSend):
        logger.debug("Sending MeshCore message to channel %s", message.channel)
        try:
            for chunk in message.chunks:
                _ = await self._client.commands.send_chan_msg(message.channel, chunk)
        except Exception as err:
            raise MeshCoreException("Failed to send MeshCore message to channel %s", message.channel) from err

    def add_message_listener(self, listener: MessageListener) -> None:
        self._message_listeners.append(listener)
        logger.debug("Registered MeshCore message listener %r", listener)

    async def run(self):
        logger.info("Starting MeshCore message handling")
        subscribe = cast(
            Callable[
                [EventType, Callable[[Event], asyncio.Future[None] | None]],
                Subscription,
            ],
            self._client.subscribe,
        )
        self._subscription = subscribe(EventType.CHANNEL_MSG_RECV, self._handle_channel_msg)
        try:
            _ = await self._client.connect()
            _ = await self._client.start_auto_message_fetching()
        except Exception as err:
            raise MeshCoreException("Failed to start MeshCore message handling") from err
        logger.info("MeshCore connected; automatic message fetching started")

    def _handle_channel_msg(self, event: Event):
        raw_payload = cast(object, event.payload)
        if not isinstance(raw_payload, dict):
            return
        payload = cast(dict[str, object], raw_payload)
        if payload.get("type") != "CHAN":
            return
        message = self._map_message_from_event(event)
        logger.debug("Received MeshCore message on channel %s", message.channel)
        for listener in self._message_listeners:
            try:
                result = listener(message)
                if isawaitable(result):
                    task = asyncio.ensure_future(result)
                    task.add_done_callback(self._log_listener_result)
            except Exception as err:
                raise MeshCoreException(
                    "MeshCore message listener %r failed on channel %s",
                    listener,
                    message.channel,
                ) from err

    @staticmethod
    def _log_listener_result(task: asyncio.Future[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Asynchronous MeshCore message listener failed",
                exc_info=(type(error), error, error.__traceback__),
            )

    def _map_message_from_event(self, event: Event) -> MeshCoreMessage:
        raw_payload = cast(object, event.payload)
        if not isinstance(raw_payload, dict):
            raise MeshCoreException("MeshCore event payload must be a mapping")
        payload = cast(dict[str, object], raw_payload)
        text_value = payload.get("text")
        channel_value = payload.get("channel_idx")
        if not isinstance(text_value, str):
            raise MeshCoreException("MeshCore channel message is missing text")
        if not isinstance(channel_value, int):
            raise MeshCoreException("MeshCore channel message is missing channel_idx")
        text = text_value
        user: str | None = None
        delimiter_idx = text.find(":")
        if delimiter_idx != -1:
            user = text[:delimiter_idx].strip()
            text = text[delimiter_idx + 1 :].strip()
        channel = channel_value
        return MeshCoreMessage(channel=channel, sender=user, text=text)
