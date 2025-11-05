"""Dependency injection API: init, inject, resolve, aresolve, get_context."""

import inspect
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from spritze.core.container import Container
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
    """Inject dependencies into function parameters."""
    return _get_container().inject(func)


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
