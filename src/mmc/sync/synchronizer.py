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
from dataclasses import dataclass

from mmc.matrix import MatrixClient
from mmc.mesh.core import MeshCoreClient
from mmc.message import MatrixMessage, MatrixMessageToSend, MeshCoreMessage, MeshCoreMessageToSend

logger = logging.getLogger(__name__)


@dataclass
class SynchronizationRule:
    matrix_room_id: str
    meshcore_channel_idx: int


class Synchronizer:
    def __init__(self, matrix: MatrixClient, meshcore: MeshCoreClient, rules: list[SynchronizationRule]):
        self._matrix: MatrixClient = matrix
        self._meshcore: MeshCoreClient = meshcore
        self._rules: list[SynchronizationRule] = rules
        self._matrix.add_message_listener(self._on_matrix_message)
        self._meshcore.add_message_listener(self._on_meshcore_message)

    async def _on_matrix_message(self, message: MatrixMessage):
        for rule in self._rules:
            if rule.matrix_room_id != message.room.id:
                continue

            logger.info(
                "Forwarding Matrix message from %s in room %s to MeshCore channel %s",
                message.sender.id,
                message.room.id,
                rule.meshcore_channel_idx,
            )
            try:
                outgoing_message = MeshCoreMessageToSend.from_matrix_message(message, rule.meshcore_channel_idx)
                await self._meshcore.send_text(outgoing_message)
            except Exception:
                logger.exception(
                    "Failed to forward Matrix message from room %s to MeshCore channel %s",
                    message.room.id,
                    rule.meshcore_channel_idx,
                )
                raise
            return

    async def _on_meshcore_message(self, message: MeshCoreMessage):
        for rule in self._rules:
            if rule.meshcore_channel_idx != message.channel:
                continue

            logger.info(
                "Forwarding MeshCore message from channel %s to Matrix room %s",
                message.channel,
                rule.matrix_room_id,
            )
            try:
                outgoing_message = MatrixMessageToSend.from_meshcore_message(message, rule.matrix_room_id)
                await self._matrix.send_text(outgoing_message)
            except Exception:
                logger.exception(
                    "Failed to forward MeshCore message from channel %s to Matrix room %s",
                    message.channel,
                    rule.matrix_room_id,
                )
                raise
            return

    async def run(self):
        logger.info("Running synchronizer with %d synchronization rule(s)", len(self._rules))
        try:
            _ = await asyncio.gather(self._matrix.run(), self._meshcore.run())
        except Exception:
            logger.exception("Synchronizer stopped after a service failure")
            raise
