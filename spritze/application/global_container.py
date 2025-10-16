from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, ParamSpec, TypeVar, cast
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

from spritze.infrastructure.exceptions import DependencyNotFound, InvalidProvider
from spritze.repositories.container_repository import Container

P = ParamSpec("P")
R = TypeVar("R")

_default_container: Container | Sequence[Container] | None = None
_WRAPPER_CACHE: WeakKeyDictionary[
    Container, dict[Callable[..., object], Callable[..., object]]
] = WeakKeyDictionary()


def init(container: Container | Sequence[Container]) -> None:
    global _default_container

    if isinstance(container, (list, tuple)) and not container:
        raise ValueError("Container sequence cannot be empty")

    _default_container = container


def _get_container() -> Container | Sequence[Container]:
    container = _default_container
    if container is None:
        raise RuntimeError(
            "No global container is set. Call spritze.init(container) first."
        )
    return container


def _get_inner(
    container: Container, func: Callable[..., object]
) -> Callable[..., object]:
    mapping = _WRAPPER_CACHE.get(container)
    if mapping is None:
        mapping = {}
        _WRAPPER_CACHE[container] = mapping
    inner = mapping.get(func)
    if inner is None:
        inner = container.injector()(func)
        mapping[func] = inner
    return inner


def _try_containers(
    container_list: Sequence[Container],
    func: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> object:
    last_exc: Exception | None = None
    for container in container_list:
        inner = _get_inner(container, func)
        try:
            return inner(*args, **kwargs)
        except (DependencyNotFound, InvalidProvider) as e:
            last_exc = e
            continue
    if last_exc is not None:
        raise last_exc
    raise DependencyNotFound(object)


async def _try_containers_async(
    container_list: Sequence[Container],
    func: Callable[..., object],
    *args: object,
    **kwargs: object,
) -> object:
    last_exc: Exception | None = None
    for container in container_list:
        inner = _get_inner(container, func)
        try:
            inner_async = cast("Callable[..., Awaitable[object]]", inner)
            return await inner_async(*args, **kwargs)
        except (DependencyNotFound, InvalidProvider) as e:
            last_exc = e
            continue
    if last_exc is not None:
        raise last_exc
    raise DependencyNotFound(object)


def _create_wrapper(
    containers: Container | Sequence[Container],
    func: Callable[P, R],
    sig: inspect.Signature,
) -> Callable[..., R]:
    if not isinstance(containers, (list, tuple)):
        container_list = cast("Sequence[Container]", (containers,))
    else:
        container_list = containers

    if inspect.iscoroutinefunction(func):

        async def _awrapper(*args: object, **kwargs: object) -> object:
            return await _try_containers_async(
                container_list, cast("Callable[..., object]", func), *args, **kwargs
            )

        wrapper = _awrapper
    else:

        def _swrapper(*args: object, **kwargs: object) -> object:
            return _try_containers(
                container_list, cast("Callable[..., object]", func), *args, **kwargs
            )

        wrapper = _swrapper

    from contextlib import suppress

    with suppress(Exception):
        setattr(wrapper, "__signature__", sig.replace(parameters=()))
    return cast("Callable[..., R]", wrapper)


def inject(func: Callable[P, R]) -> Callable[..., R]:
    sig = inspect.signature(func)
    containers = _get_container()
    return _create_wrapper(containers, func, sig)


__all__ = ["init", "inject"]
