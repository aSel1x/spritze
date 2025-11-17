import inspect
from collections.abc import Awaitable
from functools import wraps
from typing import Callable, ParamSpec, TypeVar, cast

from spritze.internal.globals import get_global_container
from spritze.internal.type_utils import extract_dependency_from_param

__all__ = ("inject",)

P = ParamSpec("P")
R = TypeVar("R")


def inject(func: Callable[P, R]) -> Callable[..., R]:
    """
    Decorator for automatic dependency injection.

    Removes injected parameters from function signature and resolves them lazily.
    """
    sig = inspect.signature(func)

    params_to_inject: list[tuple[str, type[object]]] = []
    for name, param in sig.parameters.items():
        dependency_type = extract_dependency_from_param(param)
        if dependency_type is not None:
            params_to_inject.append((name, dependency_type))

    new_params = [
        param
        for param in sig.parameters.values()
        if param.name not in [name for name, _ in params_to_inject]
    ]
    new_sig = sig.replace(parameters=new_params)

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> R:
            container = get_global_container()

            resolved_kwargs = dict(kwargs)
            for name, dep_type in params_to_inject:
                if name not in resolved_kwargs:
                    resolved_kwargs[name] = await container.aresolve(dep_type)

            result = cast(Callable[..., Awaitable[R]], func)(*args, **resolved_kwargs)
            return await result

        wrapper = async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args: object, **kwargs: object) -> R:
            container = get_global_container()

            resolved_kwargs = dict(kwargs)
            for name, dep_type in params_to_inject:
                if name not in resolved_kwargs:
                    resolved_kwargs[name] = container.resolve(dep_type)

            result = cast(Callable[..., R], func)(*args, **resolved_kwargs)
            return result

        wrapper = sync_wrapper

    setattr(wrapper, "__signature__", new_sig)
    return cast(Callable[..., R], wrapper)
