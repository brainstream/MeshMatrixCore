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

import logging
from dataclasses import dataclass

from markdown import markdown

_MESHCORE_MAX_MESSAGE_LENGTH = 143
_MESHCORE_MAX_SENDER_NAME_LENGTH = 24
_MESHCORE_ICON_EMOJI = "📟"
_MATRIX_ICON_EMOJI = "⚛"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeshCoreMessage:
    channel: int
    sender: str | None
    text: str


@dataclass
class MeshCoreMessageToSend:
    channel: int
    chunks: list[str]

    @classmethod
    def from_matrix_message(cls, message: MatrixMessage, channel: int) -> MeshCoreMessageToSend:
        sender = cls._truncate_sender(message.sender.name)
        matrix_icon = _MATRIX_ICON_EMOJI + " "
        full_text = f"{matrix_icon}{sender}\n{message.text}"
        if len(_MeshCoreTextEncoder.encode(full_text)) <= _MESHCORE_MAX_MESSAGE_LENGTH:
            chunks = [full_text]
        else:
            sender_length = len(_MeshCoreTextEncoder.encode(sender))
            chunk_index_length = 6  # " [x/x]"
            matrix_icon_length = len(_MeshCoreTextEncoder.encode(matrix_icon))
            chunk_header_length = sender_length + chunk_index_length + matrix_icon_length + 1
            max_chunk_count = 9
            max_chunk_length = _MESHCORE_MAX_MESSAGE_LENGTH - chunk_header_length
            text_chunks = cls._split_by_max_bytes(message.text, max_chunk_length)
            chunk_count = min(len(text_chunks), max_chunk_count)
            if chunk_count < len(text_chunks):
                logger.info("Message truncated to %d chunks", chunk_count)
            chunks = [
                f"{matrix_icon}[{i + 1}/{chunk_count}] {sender}\n{chunk}"
                for i, chunk in enumerate(text_chunks[:chunk_count])
            ]
        return cls(channel=channel, chunks=chunks)

    @staticmethod
    def _truncate_sender(sender: str) -> str:
        encoded_sender = _MeshCoreTextEncoder.encode(sender)
        if len(encoded_sender) > _MESHCORE_MAX_SENDER_NAME_LENGTH:
            return _MeshCoreTextEncoder.decode(encoded_sender[:_MESHCORE_MAX_SENDER_NAME_LENGTH]) + "…"
        return sender

    @classmethod
    def _split_by_max_bytes(cls, text: str, max_bytes: int) -> list[str]:
        chunks: list[str] = []
        current_text = text
        while current_text:
            encoded = _MeshCoreTextEncoder.encode(current_text)
            if len(encoded) <= max_bytes:
                chunks.append(current_text)
                break
            byte_slice = encoded[:max_bytes]
            candidate = _MeshCoreTextEncoder.decode(byte_slice)
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


class _MeshCoreTextEncoder:
    _encoding: str = "utf-8"

    @classmethod
    def encode(cls, text: str) -> bytes:
        return text.encode(cls._encoding)

    @classmethod
    def decode(cls, bytes: bytes) -> str:
        return bytes.decode(cls._encoding, errors="ignore")


@dataclass(frozen=True)
class MatrixMessage:
    sender: MatrixUser
    room: MatrixRoom
    text: str


@dataclass(frozen=True)
class MatrixRoom:
    id: str
    name: str


@dataclass(frozen=True)
class MatrixUser:
    id: str
    name: str


@dataclass
class MatrixMessageToSend:
    room: str
    sender: str
    text: str
    html: str

    @classmethod
    def from_meshcore_message(cls, message: MeshCoreMessage, room: str) -> MatrixMessageToSend:
        sender = message.sender or "unknown"
        text = f"**{_MESHCORE_ICON_EMOJI} {sender}**\n\n{message.text}"
        return cls(
            room=room,
            sender=sender,
            text=text,
            html=markdown(text),
        )

    @classmethod
    def create_unsupported_mime_message(cls, room: str) -> MatrixMessageToSend:
        text = "> ⚠️ MeshCore supports text messages only"
        return cls(
            room=room,
            sender="",
            text=text,
            html=markdown(text),
        )
