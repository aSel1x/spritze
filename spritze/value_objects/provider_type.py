from __future__ import annotations

from enum import Enum, auto


class ProviderType(Enum):
    SIMPLE = auto()
    ASYNC = auto()
    GEN = auto()
    ASYNC_GEN = auto()


__all__ = ["ProviderType"]
