"""Dependency injection API: init, inject, resolve, aresolve, get_context."""

import inspect
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from spritze.core.container import Container
from spritze.core.resolution import ResolutionService
from spritze.exceptions import AsyncSyncMismatch

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

_default_container: Container | None = None


class _MainContainer(Container):
    """Main container that merges providers from multiple containers."""

    def __init__(self, *children: Container) -> None:
        super().__init__()
        for child in children:
            self._providers.update(child._providers)


def init(
    *containers: Container,
    context: dict[type[object], object] | None = None,
) -> None:
    global _default_container

    if not containers:
        raise ValueError("At least one container must be provided")

    _default_container = _MainContainer(*containers)

    if context:
        for ctx_type, ctx_value in context.items():
            _default_container.set_context_value(ctx_type, ctx_value)


def _get_container() -> Container:
    container = _default_container
    if container is None:
        raise RuntimeError(
            "No global container is set. Call spritze.init(container) first."
        )
    return container


def resolve(dependency_type: type[T]) -> T:
    """Resolve a sync dependency by type.

    Use this for synchronous providers only.
    For async providers, use aresolve().

    Args:
        dependency_type: The type of dependency to resolve.

    Returns:
        Resolved instance.

    Raises:
        AsyncSyncMismatch: If provider is async (use aresolve instead).
    """
    container = _get_container()
    if container.is_async_provider(dependency_type):
        raise AsyncSyncMismatch(dependency_type, "sync")
    result = container.resolve(dependency_type)
    assert not inspect.isawaitable(result)
    return result


async def aresolve(dependency_type: type[T]) -> T:
    """Resolve a dependency by type in async context.

    Works with both sync and async providers.

    Args:
        dependency_type: The type of dependency to resolve.

    Returns:
        Resolved instance.
    """
    result = _get_container().resolve(dependency_type)
    if inspect.isawaitable(result):
        return await result
    return result


def inject(func: Callable[P, R]) -> Callable[..., R]:
    """Inject dependencies into function parameters.

    Container resolution is deferred until first function call,
    allowing @inject to be used at import time.
    """
    _injected: Callable[..., R] | None = None

    def _get_injected() -> Callable[..., R]:
        nonlocal _injected
        if _injected is None:
            _injected = _get_container().inject(func)
        return _injected

    new_sig, _deps = ResolutionService.create_signature_without_dependencies(func)

    original_func: Callable[..., object] = func
    while hasattr(original_func, "__wrapped__"):
        wrapped = cast(Callable[..., object], getattr(original_func, "__wrapped__"))
        original_func = wrapped

    if inspect.iscoroutinefunction(original_func):

        @wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> R:
            injected_func = _get_injected()
            result = injected_func(*args, **kwargs)
            return await cast(Awaitable[R], result)

        with suppress(AttributeError, TypeError):
            setattr(async_wrapper, "__signature__", new_sig)
        return cast(Callable[..., R], async_wrapper)

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> R:
        return _get_injected()(*args, **kwargs)

    with suppress(AttributeError, TypeError):
        setattr(wrapper, "__signature__", new_sig)
    return wrapper


class _GlobalContext:
    def set(self, **kwargs: object) -> None:
        """Set context values as Type=value kwargs."""
        if _default_container is None:
            raise RuntimeError(
                "Cannot set context before initialization. Call init() first."
            )

        for _key, value in kwargs.items():
            _default_container.set_context_value(type(value), value)


def get_context() -> _GlobalContext:
    """Get global context accessor."""
    if _default_container is None:
        raise RuntimeError(
            "Cannot access context before initialization. Call init() first."
        )
    return _GlobalContext()


__all__ = ["init", "inject", "resolve", "aresolve", "get_context"]
