from collections.abc import Callable
from typing import Final, ParamSpec, TypeVar, overload

from spritze.api.provider_descriptor import ProviderDescriptor
from spritze.types import Scope

P = ParamSpec("P")
R = TypeVar("R")

PROVIDER_TAG: Final[str] = "__spritze_provider__"


@overload
def provider(
    target: type[object],
    *,
    provides: type[object] | None = None,
    scope: Scope = Scope.REQUEST,
) -> ProviderDescriptor: ...


@overload
def provider(
    *, provides: type[object] | None = None, scope: Scope = Scope.REQUEST
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def provider(
    target: type[object] | None = None,
    *,
    provides: type[object] | None = None,
    scope: Scope = Scope.REQUEST,
) -> ProviderDescriptor | Callable[[Callable[P, R]], Callable[P, R]]:
    """Provider decorator/descriptor with dual mode.

    Mode 1 - Decorator for methods:
        @provider(scope=Scope.APP)
        def my_service(self, dep: Dependency) -> Service:
            return Service(dep)

    Mode 2 - Declarative for classes:
        my_service = provider(Service, scope=Scope.APP)
        my_service = provider(ServiceImpl, provides=ServiceInterface, scope=Scope.APP)
    """
    if target is not None:
        return ProviderDescriptor(target, provides=provides, scope=scope)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        setattr(func, PROVIDER_TAG, {"provides": provides, "scope": scope})
        return func

    return decorator


__all__ = ["PROVIDER_TAG", "provider"]
