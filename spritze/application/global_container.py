from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, ParamSpec, TypeVar, cast, get_type_hints
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

from spritze.infrastructure.exceptions import DependencyNotFound, InvalidProvider
from spritze.repositories.container_repository import Container
from spritze.services.resolution_service import ResolutionService

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


def _try_resolve_sync(
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


async def _try_resolve_async(
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


def _normalize_containers(
    containers: Container | Sequence[Container],
) -> Sequence[Container]:
    return (
        containers
        if isinstance(containers, (list, tuple))
        else cast("Sequence[Container]", (containers,))
    )


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

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def _awrapper(*args: object, **kwargs: object) -> object:
            container_list = _normalize_containers(_get_container())
            return await _try_resolve_async(
                container_list, cast("Callable[..., object]", func), *args, **kwargs
            )

        wrapper = _awrapper
    else:

        @functools.wraps(func)
        def _swrapper(*args: object, **kwargs: object) -> object:
            container_list = _normalize_containers(_get_container())
            return _try_resolve_sync(
                container_list, cast("Callable[..., object]", func), *args, **kwargs
            )

        wrapper = _swrapper

    from contextlib import suppress

    with suppress(AttributeError, TypeError):
        setattr(wrapper, "__signature__", _get_new_signature())

    return cast("Callable[..., R]", wrapper)


__all__ = ["init", "inject"]
