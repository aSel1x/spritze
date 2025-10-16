from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Generic, TypeVar, override

T = TypeVar("T")


class DependencyMarker(Generic[T]):
    def __init__(self, dependency_type: type[T] | None = None) -> None:
        self.dependency_type: type[T] | None = dependency_type


DependsMarker = DependencyMarker


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

        def __getitem__(
            cls, item: type[T]
        ) -> Annotated[type[T], DependencyMarker[T]]: ...

else:

    def _create_depends_annotation(
        t: type[T],
    ) -> Annotated[type[T], DependencyMarker[T]]:
        return Annotated[t, DependencyMarker(t)]

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

        def __getitem__(cls, item: type[T]) -> Annotated[type[T], DependencyMarker[T]]:
            return _create_depends_annotation(item)


class Depends(Generic[T], metaclass=_DependsMeta):
    pass


__all__ = ["DependencyMarker", "Depends", "DependsMarker"]
