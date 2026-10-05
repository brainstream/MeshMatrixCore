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
from dataclasses import dataclass

_MESHCORE_MAX_MESSAGE_LENGTH = 143
logger = logging.getLogger(__name__)


@dataclass
class MeshCoreMessage:
    channel: int
    sender: str | None
    text: str


def prepare_message_for_send(message: MeshCoreMessage) -> list[str]:
    matrix_icon = "⚛ "

    full_text = f"{matrix_icon}{message.sender}\n{message.text}"
    if len(full_text.encode("utf-8")) <= _MESHCORE_MAX_MESSAGE_LENGTH:
        return [full_text]

    sender_length = len(message.sender.encode("utf-8")) if message.sender else 0
    matrix_icon_length = 5
    chunk_index_length = 6  # " [x/x]"
    chunk_header_length = sender_length + chunk_index_length + matrix_icon_length + 1
    max_chunk_count = 9
    max_chunk_length = _MESHCORE_MAX_MESSAGE_LENGTH - chunk_header_length

    chunks = _split_by_max_bytes(message.text, max_chunk_length)
    chunk_count = min(len(chunks), max_chunk_count)
    if chunk_count < len(chunks):
        logger.info("Message truncated to %d chunks", chunk_count)
    return [
        f"{matrix_icon}[{i + 1}/{chunk_count}] {message.sender}\n{chunk}"
        for i, chunk in enumerate(chunks[:chunk_count])
    ]


def _split_by_max_bytes(text: str, max_bytes: int) -> list[str]:
    encoding = "utf-8"
    chunks = []
    current_text = text
    while current_text:
        encoded = current_text.encode(encoding)
        if len(encoded) <= max_bytes:
            chunks.append(current_text)
            break
        byte_slice = encoded[:max_bytes]
        candidate = byte_slice.decode(encoding, errors="ignore")
        last_space = candidate.rfind(" ")
        if last_space != -1:
            chunks.append(candidate[: last_space + 1])
            current_text = current_text[last_space + 1 :]
        else:
            if not candidate:
                break
            chunks.append(candidate)
            current_text = current_text[len(candidate) :]
    return chunks
