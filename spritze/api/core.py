from typing import TypeVar

from spritze.core.container import Container
from spritze.exceptions import NoContainerProvided
from spritze.internal.globals import get_global_container, set_global_container

__all__ = (
    "init",
    "resolve",
    "aresolve",
)

T = TypeVar("T")


def init(
    *containers: type[Container], context: dict[type, object] | None = None
) -> None:
    if not containers:
        raise NoContainerProvided()

    Container._allow_instantiation = True  # pyright: ignore[reportPrivateUsage]

    if len(containers) == 1:
        container_instance = containers[0]()
    else:
        MergedContainer = type("MergedContainer", containers, {})
        container_instance = MergedContainer()
    if context:
        container_instance._app_scoped_instances.update(context)  # pyright: ignore[reportPrivateUsage]

    set_global_container(container_instance)

    Container._allow_instantiation = False  # pyright: ignore[reportPrivateUsage]


def resolve(dependency_type: type[T]) -> T:
    """Synchronously resolve a dependency through the global container."""
    container = get_global_container()
    return container.resolve(dependency_type)


async def aresolve(dependency_type: type[T]) -> T:
    """Asynchronously resolve a dependency through the global container."""
    container = get_global_container()
    return await container.aresolve(dependency_type)
