from dataclasses import dataclass


@dataclass
class MatrixMessage:
    text: str
    room: MatrixRoom
    sender: MatrixUser


@dataclass
class MatrixRoom:
    id: str
    name: str


@dataclass
class MatrixUser:
    id: str
    name: str
