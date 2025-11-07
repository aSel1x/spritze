from collections.abc import Callable
from typing import TypeVar

from spritze.types import Scope

_C = TypeVar("_C")


class ProviderDescriptor:
    """Descriptor for declarative provider registration."""

    def __init__(
        self,
        target: type[object] | Callable[..., object],
        *,
        provides: type[object] | None = None,
        scope: Scope = Scope.REQUEST,
    ) -> None:
        self.target: type[object] | Callable[..., object] = target
        self.provides: type[object] | None = provides
        self.scope: Scope = scope
        self.attr_name: str | None = None

    def __set_name__(self, owner: type[_C], name: str) -> None:
        self.attr_name = name

    def __get__(
        self,
        instance: _C | None,
        owner: type[_C],
    ) -> type[object]:
        if self.provides is not None:
            return self.provides
        if isinstance(self.target, type):
            return self.target
        return object


__all__ = ["ProviderDescriptor"]
