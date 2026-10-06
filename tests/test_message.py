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

from mmc.message import (
    MatrixMessage,
    MatrixMessageToSend,
    MatrixRoom,
    MatrixUser,
    MeshCoreMessage,
    MeshCoreMessageToSend,
)


def test_convert_short_matrix_message_for_send() -> None:
    converted = MeshCoreMessageToSend.from_matrix_message(make_matrix_message("Hello"), 3)

    assert converted == MeshCoreMessageToSend(
        channel=3,
        chunks=["⚛ Alice\nHello"],
    )


def make_matrix_message(text: str, sender: str = "Alice") -> MatrixMessage:
    return MatrixMessage(
        text=text,
        room=MatrixRoom(id="!room:example.org", name="Example"),
        sender=MatrixUser(id="@alice:example.org", name=sender),
    )


def test_convert_long_utf8_matrix_message_splits_without_breaking_characters() -> None:
    text = "🙂" * 80
    converted = MeshCoreMessageToSend.from_matrix_message(make_matrix_message(text, "A"), 3)

    assert len(converted.chunks) > 1
    assert [chunk.split("\n", 1)[0] for chunk in converted.chunks] == [
        f"⚛ [{index}/{len(converted.chunks)}] A" for index in range(1, len(converted.chunks) + 1)
    ]
    assert "".join(chunk.split("\n", 1)[1] for chunk in converted.chunks) == text
    assert all(len(chunk.encode("utf-8")) <= 143 for chunk in converted.chunks)


def test_convert_long_matrix_message_preserves_text_across_chunks() -> None:
    text = "A message with spaces, punctuation, and words. " * 8
    converted = MeshCoreMessageToSend.from_matrix_message(make_matrix_message(text), 3)

    assert len(converted.chunks) > 1
    assert "".join(chunk.split("\n", 1)[1] for chunk in converted.chunks) == text


def test_convert_long_matrix_message_is_limited_to_nine_chunks() -> None:
    converted = MeshCoreMessageToSend.from_matrix_message(make_matrix_message("x" * 2_000, "A"), 3)

    assert len(converted.chunks) == 9
    assert converted.chunks[0].startswith("⚛ [1/9] A\n")
    assert converted.chunks[-1].startswith("⚛ [9/9] A\n")
    assert all(len(chunk.encode("utf-8")) <= 143 for chunk in converted.chunks)


def test_convert_matrix_message_to_meshcore() -> None:
    message = MatrixMessage(
        text="Hello from Matrix",
        room=MatrixRoom(id="!room:example.org", name="Example"),
        sender=MatrixUser(id="@alice:example.org", name="Alice"),
    )

    assert MeshCoreMessageToSend.from_matrix_message(message, channel=7) == (
        MeshCoreMessageToSend(
            channel=7,
            chunks=["⚛ Alice\nHello from Matrix"],
        )
    )


def test_convert_meshcore_message_to_matrix() -> None:
    message = MeshCoreMessage(channel=7, sender="alice-node", text="Hello from MeshCore")

    assert MatrixMessageToSend.from_meshcore_message(message, room="!room:example.org") == MatrixMessageToSend(
        room="!room:example.org",
        sender="alice-node",
        text="Hello from MeshCore",
        html="<p><strong>📟 alice-node</strong></p>\n<p>Hello from MeshCore</p>",
    )


def test_convert_meshcore_message_to_matrix_renders_markdown() -> None:
    message = MeshCoreMessage(channel=7, sender="alice-node", text="Hello **bold**")

    converted = MatrixMessageToSend.from_meshcore_message(message, room="!room:example.org")

    assert converted.html == ("<p><strong>📟 alice-node</strong></p>\n<p>Hello <strong>bold</strong></p>")


def test_convert_meshcore_message_without_sender_to_matrix() -> None:
    message = MeshCoreMessage(channel=7, sender=None, text="Hello from MeshCore")

    assert MatrixMessageToSend.from_meshcore_message(message, room="!room:example.org") == (
        MatrixMessageToSend(
            room="!room:example.org",
            sender="unknown",
            text="Hello from MeshCore",
            html="<p><strong>📟 unknown</strong></p>\n<p>Hello from MeshCore</p>",
        )
    )
