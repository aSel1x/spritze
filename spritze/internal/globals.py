"""Global container management for dependency injection."""

from typing import TYPE_CHECKING

from spritze.exceptions import ContainerNotInitialized

if TYPE_CHECKING:
    from spritze.core.container import Container

__all__ = (
    "get_global_container",
    "set_global_container",
)

_global_container: "Container | None" = None


def get_global_container() -> "Container":
    """Get the global container instance."""
    container = _global_container
    if container is None:
        raise ContainerNotInitialized()
    return container


def set_global_container(container: "Container") -> None:
    """Set the global container instance."""
    global _global_container
    _global_container = container
