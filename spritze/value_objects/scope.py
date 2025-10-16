from __future__ import annotations

from enum import Enum, auto


class Scope(Enum):
    APP = auto()
    REQUEST = auto()


__all__ = ["Scope"]
