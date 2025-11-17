from typing import (
    Callable,
    ParamSpec,
    TypeVar,
    cast,
    overload,
)

from spritze.core.container import PROVIDER_TAG
from spritze.core.provider import Provider
from spritze.exceptions import InvalidProvider
from spritze.types import Scope

__all__ = ("provider",)

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


@overload
def provider(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def provider(
    *,
    scope: Scope = ...,
    provide_as: type[object] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


@overload
def provider(
    target: type[T],
    *,
    scope: Scope = ...,
    provide_as: type[object] | None = None,
) -> Provider: ...


@overload
def provider(
    target: Callable[P, R],
    *,
    scope: Scope = ...,
    provide_as: type[object] | None = None,
) -> Provider: ...


def provider(  # pyright: ignore[reportInconsistentOverload]
    target: Callable[P, R] | type[T] | None = None,
    *,
    scope: Scope = Scope.APP,
    provide_as: type[object] | None = None,
) -> Provider | Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    """
    Provider decorator/factory supporting all modes:

    Mode 1 - Decorator for methods:
        @provider(scope=Scope.APP)
        def my_service(self, dep: Dependency) -> Service:
            return Service(dep)

    Mode 2 - Declarative for classes:
        my_service = provider(Service, scope=Scope.APP)
        my_service = provider(ServiceImpl, provide_as=ServiceInterface, scope=Scope.APP)

    Mode 3 - Declarative for functions:
        my_service = provider(build_service, scope=Scope.APP)
        my_service = provider(
            build_service, provide_as=ServiceInterface, scope=Scope.APP
        )
    """

    if target is None:

        def decorator(func: Callable[P, R]) -> Callable[P, R]:
            provider_instance = Provider.from_callable(
                callable_obj=cast(Callable[..., object], func),
                scope=scope,
                provide_as=provide_as,
            )
            setattr(func, PROVIDER_TAG, provider_instance)
            return func

        return decorator

    elif callable(target) and not isinstance(target, type):
        provider_instance = Provider.from_callable(
            callable_obj=cast(Callable[..., object], target),
            scope=scope,
            provide_as=provide_as,
        )
        static_method = staticmethod(target)

        setattr(static_method, PROVIDER_TAG, provider_instance)
        return static_method

    elif isinstance(target, type):  # pyright: ignore[reportUnnecessaryIsInstance]
        provider_instance = Provider.from_callable(
            callable_obj=target, scope=scope, provide_as=provide_as
        )
        setattr(target, PROVIDER_TAG, provider_instance)
        return provider_instance

    raise InvalidProvider("Invalid provider target")  # pyright: ignore[reportUnreachable]
