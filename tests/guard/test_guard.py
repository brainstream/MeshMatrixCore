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

from mmc.message import MatrixMessage, MatrixMessageToSend, MatrixRoom, MatrixUser
from mmc.synchronizer.guard import IngoingMessage, MessageGuard, MessageGuardRule, OutgoingMessage


def make_matrix_message(text: str = "message", sender_id: str = "@alice:example.org") -> MatrixMessage:
    return MatrixMessage(
        sender=MatrixUser(id=sender_id, name="Alice"),
        room=MatrixRoom(id="!room:example.org", name="Example"),
        text=text,
    )


def make_matrix_message_to_send(text: str = "message") -> MatrixMessageToSend:
    return MatrixMessageToSend(room="!room:example.org", sender="alice-node", text=text, html=text)


class StubMessageGuardRule(MessageGuardRule):
    def __init__(self) -> None:
        self.allowed_messages: set[IngoingMessage] = set()
        self.ignored_messages: set[IngoingMessage] = set()
        self.ingoing_messages: list[IngoingMessage] = []
        self.outgoing_messages: list[OutgoingMessage] = []

    @override
    def can_process_ingoing_message(self, message: IngoingMessage) -> bool:
        self.ingoing_messages.append(message)
        if message in self.ignored_messages:
            return False
        return message in self.allowed_messages

    @override
    def store_outgoing_message(self, message: OutgoingMessage) -> None:
        self.outgoing_messages.append(message)


def test_stores_and_checks_messages_through_rules() -> None:
    first_rule = StubMessageGuardRule()
    second_rule = StubMessageGuardRule()
    allowed_message = make_matrix_message("allowed")
    ignored_message = make_matrix_message(sender_id="@bridge:example.org")
    first_rule.allowed_messages.add(allowed_message)
    first_rule.ignored_messages.add(ignored_message)
    second_rule.allowed_messages.add(allowed_message)

    guard = MessageGuard()
    guard.add_rule(first_rule)
    guard.add_rule(second_rule)

    outgoing_message = make_matrix_message_to_send("echo")

    assert guard.can_process_ingoing_message(allowed_message)
    assert first_rule.ingoing_messages == [allowed_message]
    assert second_rule.ingoing_messages == [allowed_message]

    assert not guard.can_process_ingoing_message(ignored_message)
    assert first_rule.ingoing_messages == [allowed_message, ignored_message]
    assert second_rule.ingoing_messages == [allowed_message]

    guard.store_outgoing_message(outgoing_message)
    assert first_rule.outgoing_messages == [outgoing_message]
    assert second_rule.outgoing_messages == [outgoing_message]


def test_guard_with_no_rules_allows_messages() -> None:
    guard = MessageGuard()

    assert guard.can_process_ingoing_message(make_matrix_message())
    guard.store_outgoing_message(make_matrix_message_to_send())
