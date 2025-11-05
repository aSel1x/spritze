from typing import TypeVar

from spritze.types import Scope

_C = TypeVar("_C")


class ProviderDescriptor:
    """Descriptor for declarative provider registration."""

    def __init__(
        self,
        target: type[object],
        *,
        provides: type[object] | None = None,
        scope: Scope = Scope.REQUEST,
    ) -> None:
        self.target: type[object] = target
        self.provides: type[object] = provides if provides is not None else target
        self.scope: Scope = scope
        self.attr_name: str | None = None

    def __set_name__(self, owner: type[_C], name: str) -> None:
        self.attr_name = name

    def __get__(
        self,
        instance: _C | None,
        owner: type[_C],
    ) -> type[object]:
        return self.provides


__all__ = ["ProviderDescriptor"]
