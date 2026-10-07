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
from mmc.synchronizer.guard import HashBasedMessageGuardRule


def make_matrix_message(text: str) -> MatrixMessage:
    return MatrixMessage(
        sender=MatrixUser(id="@alice:example.org", name="Alice"),
        room=MatrixRoom(id="!room:example.org", name="Example"),
        text=text,
    )


def make_matrix_message_to_send(text: str) -> MatrixMessageToSend:
    return MatrixMessageToSend.from_meshcore_message(make_meshcore_message(text), "!room:example.org")


def make_meshcore_message(text: str) -> MeshCoreMessage:
    return MeshCoreMessage(channel=7, sender="alice-node", text=text)


def test_allows_unseen_messages() -> None:
    rule = HashBasedMessageGuardRule()

    assert rule.can_process_ingoing_message(make_matrix_message("Matrix text"))
    assert rule.can_process_ingoing_message(make_meshcore_message("MeshCore text"))


def test_rejects_matrix_echo_only_on_matrix() -> None:
    rule = HashBasedMessageGuardRule()
    outgoing_message = make_matrix_message_to_send("same text")
    rule.store_outgoing_message(outgoing_message)

    assert not rule.can_process_ingoing_message(make_matrix_message(outgoing_message.text))
    assert rule.can_process_ingoing_message(make_meshcore_message("same text"))


def test_allows_matrix_message_matching_forwarded_meshcore_payload() -> None:
    rule = HashBasedMessageGuardRule()
    outgoing_message = MatrixMessageToSend.from_meshcore_message(make_meshcore_message("ok"), "!room:example.org")
    rule.store_outgoing_message(outgoing_message)

    assert outgoing_message.text == "📟 alice-node\nok"
    assert rule.can_process_ingoing_message(make_matrix_message("ok"))


def test_rejects_each_meshcore_chunk_echo_only_on_meshcore() -> None:
    rule = HashBasedMessageGuardRule()
    rule.store_outgoing_message(MeshCoreMessageToSend(channel=7, chunks=["first chunk", "second chunk"]))

    assert not rule.can_process_ingoing_message(make_meshcore_message("first chunk"))
    assert not rule.can_process_ingoing_message(make_meshcore_message("second chunk"))
    assert rule.can_process_ingoing_message(make_matrix_message("first chunk"))


def test_matches_exact_unicode_text() -> None:
    rule = HashBasedMessageGuardRule()
    outgoing_message = make_matrix_message_to_send("Привет, 🌍")
    rule.store_outgoing_message(outgoing_message)

    assert not rule.can_process_ingoing_message(make_matrix_message(outgoing_message.text))
    assert rule.can_process_ingoing_message(make_matrix_message("Привет"))
    assert rule.can_process_ingoing_message(make_matrix_message("Привет, 🌍"))


def test_cache_evicts_oldest_entry_when_at_capacity() -> None:
    rule = HashBasedMessageGuardRule()
    first_text = "outgoing message 0"
    first_message = make_matrix_message_to_send(first_text)
    rule.store_outgoing_message(first_message)
    for index in range(1, 100):
        rule.store_outgoing_message(make_matrix_message_to_send(f"outgoing message {index}"))

    assert not rule.can_process_ingoing_message(make_matrix_message(first_message.text))

    last_message = make_matrix_message_to_send("outgoing message 100")
    rule.store_outgoing_message(last_message)

    assert rule.can_process_ingoing_message(make_matrix_message(first_message.text))
    assert not rule.can_process_ingoing_message(make_matrix_message(last_message.text))
