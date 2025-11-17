"""Type-safe mapping for dependency injection container."""

from collections.abc import Iterable, Iterator
from typing import Protocol, TypeVar, cast, final, override, runtime_checkable

__all__ = ("TypeMap",)

T = TypeVar("T")


@runtime_checkable
class TypeMapProto(Protocol):
    """Protocol for type-safe mapping interface."""

    def set(self, t: type[T], value: T) -> None: ...
    def get(self, t: type[T]) -> T | None: ...
    def pop(self, t: type[T]) -> T | None: ...
    def __contains__(self, t: type[object]) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[type[object]]: ...
    def items(self) -> Iterable[tuple[type[object], object]]: ...
    def clear(self) -> None: ...


@final
class TypeMap(TypeMapProto):
    """Type-safe mapping for storing instances by their type."""

    __slots__ = ("_store",)

    def __init__(self) -> None:
        self._store: dict[type, object] = {}

    @override
    def set(self, t: type[T], value: T) -> None:
        """Store a value for a given type."""
        self._store[t] = value

    @override
    def get(self, t: type[T]) -> T | None:
        """Retrieve a value for a given type."""
        v = self._store.get(t)
        if v is None:
            return None
        return cast(T, v)

    @override
    def pop(self, t: type[T]) -> T | None:
        """Remove and return a value for a given type."""
        v = self._store.pop(t, None)
        if v is None:
            return None
        return cast(T, v)

    @override
    def __contains__(self, t: type[object]) -> bool:
        """Check if a type is in the map."""
        return t in self._store

    @override
    def __len__(self) -> int:
        """Return the number of stored types."""
        return len(self._store)

    @override
    def __iter__(self) -> Iterator[type[object]]:
        """Iterate over stored types."""
        return iter(self._store)

    @override
    def items(self) -> Iterable[tuple[type[object], object]]:
        """Return all type-value pairs."""
        return self._store.items()

    def values(self) -> Iterable[object]:
        """Return all stored values."""
        return self._store.values()

    def keys(self) -> Iterable[type[object]]:
        """Return all stored types."""
        return self._store.keys()

    @override
    def clear(self) -> None:
        """Remove all stored types and values."""
        self._store.clear()

    def update(self, other: TypeMapProto | dict[type[object], object]) -> None:
        """Update the map with values from another map or dictionary."""
        for k, v in other.items():
            self._store[k] = v

    @override
    def __repr__(self) -> str:
        return f"TypeMap({self._store!r})"
