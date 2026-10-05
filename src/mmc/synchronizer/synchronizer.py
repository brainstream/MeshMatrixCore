import asyncio
from dataclasses import dataclass

from mmc.matrix import MatrixClient, MatrixMessage
from mmc.mesh.core import MeshCoreClient
from mmc.mesh.core.message import MeshCoreMessage


@dataclass
class SynchronizationRule:
    matrix_room_id: str
    matrix_user_id: str
    meshcore_channel_idx: int
    meshcore_user_id: str


class Synchronizer:
    def __init__(
        self,
        matrix: MatrixClient,
        meshcore: MeshCoreClient,
        rules: list[SynchronizationRule],
    ):
        self._matrix = matrix
        self._meshcore = meshcore
        self._rules = rules
        self._matrix.add_message_listener(self._on_matrix_message)
        self._meshcore.add_message_listener(self._on_meshcore_message)

    async def _on_matrix_message(self, message: MatrixMessage):
        for rule in self._rules:
            if rule.matrix_room_id != message.room.id:
                continue
            if rule.matrix_user_id == message.sender.id:
                return
            await self._meshcore.send_text(
                rule.meshcore_channel_idx,
                f"Message from Matrix\nAuthor: {message.sender.name}\n\n{message.text}",
            )
            return

    async def _on_meshcore_message(self, message: MeshCoreMessage):
        for rule in self._rules:
            if rule.meshcore_channel_idx != message.channel:
                continue
            if rule.meshcore_user_id == message.sender:
                return
            await self._matrix.send_text(
                rule.matrix_room_id,
                f"Message from MeshCore\nAuthor: {message.sender}\n\n{message.text}",
            )
            return

    async def run(self):
        await asyncio.gather(self._matrix.run(), self._meshcore.run())
