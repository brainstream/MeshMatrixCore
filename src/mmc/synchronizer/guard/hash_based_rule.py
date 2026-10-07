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

from hashlib import md5
from typing import override

from cachetools import TTLCache

from mmc.message import MatrixMessage, MatrixMessageToSend

from .abstract_rule import IngoingMessage, MessageGuardRule, OutgoingMessage

_MAX_CACHE_SIZE = 100
_CACHE_TTL = 600

class HashBasedMessageGuardRule(MessageGuardRule):
    def __init__(self) -> None:
        self._matrix_hashes: TTLCache[str, bool] = TTLCache[str, bool](maxsize=_MAX_CACHE_SIZE, ttl=_CACHE_TTL)
        self._meshcore_hashes: TTLCache[str, bool] = TTLCache[str, bool](maxsize=_MAX_CACHE_SIZE, ttl=_CACHE_TTL)

    @override
    def store_outgoing_message(self, message: OutgoingMessage) -> None:
        if isinstance(message, MatrixMessageToSend):
            self._matrix_hashes[self._hash(message.text)] = True
        else:
            for chunk in message.chunks:
                self._meshcore_hashes[self._hash(chunk)] = True

    def _hash(self, message: str) -> str:
        return md5(message.encode("utf-8"), usedforsecurity=False).hexdigest()

    @override
    def can_process_ingoing_message(self, message: IngoingMessage) -> bool:
        hashes = self._matrix_hashes if isinstance(message, MatrixMessage) else self._meshcore_hashes
        return self._hash(message.text) not in hashes
