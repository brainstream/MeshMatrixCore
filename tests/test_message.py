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

from mmc.mesh.core.message import MeshCoreMessage, prepare_message_for_send


def test_prepare_short_message_for_send() -> None:
    message = MeshCoreMessage(channel=3, sender="Alice", text="Hello")

    assert prepare_message_for_send(message) == ["⚛ Alice\nHello"]


def test_prepare_long_utf8_message_for_send_splits_without_breaking_characters() -> None:
    text = "🙂" * 80
    message = MeshCoreMessage(channel=3, sender="A", text=text)

    chunks = prepare_message_for_send(message)

    assert len(chunks) > 1
    assert [chunk.split("\n", 1)[0] for chunk in chunks] == [
        f"⚛ [{index}/{len(chunks)}] A" for index in range(1, len(chunks) + 1)
    ]
    assert "".join(chunk.split("\n", 1)[1] for chunk in chunks) == text
    assert all(len(chunk.encode("utf-8")) <= 143 for chunk in chunks)


def test_prepare_long_message_preserves_full_text_across_chunks() -> None:
    text = "A message with spaces, punctuation, and words. " * 8
    message = MeshCoreMessage(channel=3, sender="Alice", text=text)

    chunks = prepare_message_for_send(message)

    assert len(chunks) > 1
    assert "".join(chunk.split("\n", 1)[1] for chunk in chunks) == text


    message = MeshCoreMessage(channel=3, sender="A", text="x" * 2_000)

    chunks = prepare_message_for_send(message)

    assert len(chunks) == 9
    assert chunks[0].startswith("⚛ [1/9] A\n")
    assert chunks[-1].startswith("⚛ [9/9] A\n")
    assert all(len(chunk.encode("utf-8")) <= 143 for chunk in chunks)
