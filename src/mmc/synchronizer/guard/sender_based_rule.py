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

from typing import override

from mmc.message import MatrixMessage, MeshCoreMessage

from .abstract_rule import IngoingMessage, MessageGuardRule, OutgoingMessage


class SenderBasedMessageGuardRule(MessageGuardRule):
    def __init__(self, matrix_sender_id: str, meshcore_sender_id: str) -> None:
        self._matrix_sender_id: str = matrix_sender_id
        self._meshcore_sender_id: str = meshcore_sender_id

    @override
    def can_process_ingoing_message(self, message: IngoingMessage) -> bool:
        return (
            self._can_process_ingoing_matrix_message(message)
            if isinstance(message, MatrixMessage)
            else self._can_process_ingoing_meshcore_message(message)
        )

    def _can_process_ingoing_matrix_message(self, message: MatrixMessage) -> bool:
        return message.sender.id != self._matrix_sender_id

    def _can_process_ingoing_meshcore_message(self, message: MeshCoreMessage) -> bool:
        return message.sender != self._meshcore_sender_id

    @override
    def store_outgoing_message(self, message: OutgoingMessage) -> None: ...
