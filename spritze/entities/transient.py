from __future__ import annotations

from typing import TypeVar

_C = TypeVar("_C")


class Transient:
    def __init__(self, target: type[object]) -> None:
        self.target: type[object] = target
        self.attr_name: str | None = None

    def __set_name__(self, owner: type[_C], name: str) -> None:
        self.attr_name = name

    def __get__(
        self,
        instance: _C | None,
        owner: type[_C],
    ) -> type[object]:
        return self.target


__all__ = ["Transient"]
