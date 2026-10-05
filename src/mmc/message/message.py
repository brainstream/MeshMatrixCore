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

from dataclasses import dataclass


@dataclass
class MeshCoreMessage:
    channel: int
    sender: str | None
    text: str


@dataclass
class MeshCoreMessageToSend:
    channel: int
    chunks: list[str]


@dataclass
class MatrixMessage:
    sender: MatrixUser
    room: MatrixRoom
    text: str


@dataclass
class MatrixRoom:
    id: str
    name: str


@dataclass
class MatrixUser:
    id: str
    name: str


@dataclass
class MatrixMessageToSend:
    room: str
    sender: str
    text: str
    html: str
