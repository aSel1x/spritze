"""Dependency injection API: init, inject, get_context."""

from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from spritze.core.container import Container

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


def resolve(dependency_type: type[T]) -> T | Awaitable[T]:
    """Resolve a dependency by type. Returns instance or awaitable."""
    return _get_container().resolve(dependency_type)


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


__all__ = ["init", "inject", "resolve", "get_context"]
