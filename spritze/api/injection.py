"""Dependency injection API: init, inject, get_context."""

from __future__ import annotations

import inspect
from contextlib import suppress
from typing import TYPE_CHECKING, ParamSpec, TypeVar, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

from spritze.core.container import Container
from spritze.core.resolution import ResolutionService

P = ParamSpec("P")
R = TypeVar("R")

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


def inject(func: Callable[P, R]) -> Callable[..., R]:
    _sig_cache: list[inspect.Signature | None] = [None]

    def _get_new_signature() -> inspect.Signature:
        if _sig_cache[0] is None:
            sig = inspect.signature(func)
            ann_map = get_type_hints(func, include_extras=True)
            deps = ResolutionService.extract_dependencies_from_signature(sig, ann_map)
            new_params = [
                param for name, param in sig.parameters.items() if name not in deps
            ]
            _sig_cache[0] = sig.replace(parameters=new_params)
        return _sig_cache[0]

    container = _get_container()
    wrapper = container.injector()(func)

    with suppress(AttributeError, TypeError):
        setattr(wrapper, "__signature__", _get_new_signature())

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


__all__ = ["init", "inject", "get_context"]
