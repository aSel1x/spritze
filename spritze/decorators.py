from typing import Callable, ParamSpec, TypeVar

from spritze.core.entities import Scope

PROVIDER_TAG = "__spritze_provider__"

P = ParamSpec("P")
R = TypeVar("R")

__all__ = ["provide"]


def provide(scope: Scope = Scope.REQUEST) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator to mark a method inside a Container as a provider.

    The dependency type is inferred from the method's return type annotation.

    :param scope: The scope of the dependency (APP or REQUEST).
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        setattr(func, PROVIDER_TAG, {"scope": scope})
        return func

    return decorator
