"""Type definitions for dependency injection."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Annotated, Generic, TypeVar, override

T = TypeVar("T")


class Scope(Enum):
    APP = auto()
    REQUEST = auto()


class ProviderType(Enum):
    SIMPLE = auto()
    ASYNC = auto()
    GEN = auto()
    ASYNC_GEN = auto()


class DependencyMarker(Generic[T]):
    def __init__(self, dependency_type: type[T] | None = None) -> None:
        self.dependency_type: type[T] | None = dependency_type


if TYPE_CHECKING:

    class _DependsMeta(type):
        def __class_getitem__(
            cls,
            item: type[T],
        ) -> Annotated[type[T], DependencyMarker[T]]: ...

        @override
        def __call__(
            cls,
            dependency_type: type[T] | None = None,
        ) -> DependencyMarker[T]: ...

else:

    class _DependsMeta(type):
        def __class_getitem__(
            cls,
            item: type[T],
        ) -> type[T]:
            return item

        def __call__(
            cls,
            dependency_type: type[T] | None = None,
        ) -> DependencyMarker[T]:
            return DependencyMarker(dependency_type)


class Depends(Generic[T], metaclass=_DependsMeta):
    pass


__all__ = ["Scope", "ProviderType", "DependencyMarker", "Depends"]
