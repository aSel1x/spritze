from __future__ import annotations

from collections.abc import Callable
from typing import Final, ParamSpec, TypeVar

from spritze.entities.transient import Transient
from spritze.value_objects.scope import Scope

P = ParamSpec("P")
R = TypeVar("R")

PROVIDER_TAG: Final[str] = "__spritze_provider__"


def provider(
    *, scope: Scope = Scope.REQUEST
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        setattr(func, PROVIDER_TAG, {"scope": scope})
        return func

    return decorator


def singleton(func: Callable[P, R]) -> Callable[P, R]:
    return provider(scope=Scope.APP)(func)


def transient(t: type[object]) -> object:
    return Transient(t)


__all__ = ["PROVIDER_TAG", "provider", "singleton", "transient"]
