"""Type stubs for spritze types."""

from enum import Enum
from typing import TypeVar

T = TypeVar("T")

class Scope(Enum):
    """Dependency scope."""

    APP: Scope
    REQUEST: Scope
    TRANSIENT: Scope

class ProviderType(Enum):
    """Provider type."""

    SYNC: ProviderType
    ASYNC: ProviderType
    SYNC_GEN: ProviderType
    ASYNC_GEN: ProviderType

class Depends:
    """Marker for dependency injection using Annotated type hints."""

    dependency_type: type | None

    def __init__(self, dependency_type: type[T] | None = None) -> None: ...
    def __class_getitem__(cls, item: type[T]) -> type[T]: ...
