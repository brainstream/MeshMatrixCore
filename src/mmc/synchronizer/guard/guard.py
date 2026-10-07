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

from .abstract_rule import IngoingMessage, MessageGuardRule, OutgoingMessage


class MessageGuard:
    def __init__(self) -> None:
        self._rules: list[MessageGuardRule] = []

    def add_rule(self, rule: MessageGuardRule) -> None:
        self._rules.append(rule)

    def store_outgoing_message(self, message: OutgoingMessage) -> None:
        for rule in self._rules:
            rule.store_outgoing_message(message)

    def can_process_ingoing_message(self, message: IngoingMessage) -> bool:
        for rule in self._rules:
            if not rule.can_process_ingoing_message(message):
                return False
        return True
