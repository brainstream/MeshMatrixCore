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

from mmc.message import MatrixMessage, MatrixRoom, MatrixUser, MeshCoreMessage
from mmc.synchronizer.guard import SenderBasedMessageGuardRule


def make_matrix_message(sender_id: str = "@alice:example.org") -> MatrixMessage:
    return MatrixMessage(
        sender=MatrixUser(id=sender_id, name="Alice"),
        room=MatrixRoom(id="!room:example.org", name="Example"),
        text="message",
    )


def make_meshcore_message(sender: str | None = "alice-node") -> MeshCoreMessage:
    return MeshCoreMessage(channel=7, sender=sender, text="message")


def test_allows_non_bridge_senders_on_both_protocols() -> None:
    rule = SenderBasedMessageGuardRule("@bridge:example.org", "bridge-node")

    assert rule.can_process_ingoing_message(make_matrix_message())
    assert rule.can_process_ingoing_message(make_meshcore_message())


def test_rejects_bridge_senders_on_both_protocols() -> None:
    rule = SenderBasedMessageGuardRule("@bridge:example.org", "bridge-node")

    assert not rule.can_process_ingoing_message(make_matrix_message(sender_id="@bridge:example.org"))
    assert not rule.can_process_ingoing_message(make_meshcore_message(sender="bridge-node"))


def test_allows_unknown_meshcore_sender() -> None:
    rule = SenderBasedMessageGuardRule("@bridge:example.org", "bridge-node")

    assert rule.can_process_ingoing_message(make_meshcore_message(sender=None))
