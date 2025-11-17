"""Type definitions for dependency injection."""

from enum import Enum, auto
from typing import TypeVar

__all__ = (
    "Scope",
    "ProviderType",
    "Depends",
)

T = TypeVar("T")


class Scope(Enum):
    APP = auto()
    REQUEST = auto()
    TRANSIENT = auto()


class ProviderType(Enum):
    SYNC = auto()
    ASYNC = auto()
    SYNC_GEN = auto()
    ASYNC_GEN = auto()


class Depends:
    """Marker for dependency injection using Annotated type hints.

    Can be used as:
    - Depends[Type] in Annotated hints
    - Depends() as default parameter value
    """

    def __init__(self, dependency_type: type[T] | None = None) -> None:
        self.dependency_type: type | None = dependency_type

    def __class_getitem__(cls, item: type[T]) -> type[T]:
        return item
