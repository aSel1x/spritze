from __future__ import annotations

from typing import Generic, Protocol, TypeVar, cast

T = TypeVar("T")


class ContextProvider(Protocol):
    def get_context_value(self, t: type[object]) -> object | None: ...


class ContextField(Generic[T]):
    def __init__(self, ctx_type: type[T]) -> None:
        self.ctx_type: type[T] = ctx_type
        self.name: str | None = None

    def __set_name__(self, owner: type[object], name: str) -> None:
        self.name = name

    def __get__(
        self, instance: ContextProvider | None, owner: type[object]
    ) -> ContextField[T] | T:
        if instance is None:
            return self
        value = instance.get_context_value(self.ctx_type)
        if value is None:
            raise LookupError(f"Context value for {self.ctx_type.__name__} not found")
        return cast("T", value)


class _ContextAccessor:
    def get(self, t: type[T]) -> ContextField[T]:
        return ContextField(t)


context = _ContextAccessor()

__all__ = ["ContextField", "context"]
