from dataclasses import dataclass


@dataclass
class MeshCoreMessage:
    channel: int
    sender: str | None
    text: str
