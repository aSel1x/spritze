"""Type stubs for spritze library.

Provides type hints for the Spritze dependency injection framework.
"""

from collections.abc import Callable, Sequence
from enum import Enum
from typing import ParamSpec, TypeVar, overload

from spritze.entities.transient import Transient as Transient
from spritze.infrastructure.context import ContextField as ContextField
from spritze.repositories.container_repository import Container as Container

__all__ = [
    "Container",
    "Scope",
    "Depends",
    "DependencyMarker",
    "Transient",
    "ContextField",
    "provider",
    "singleton",
    "transient",
    "init",
    "inject",
    "context",
]

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")

class Scope(str, Enum):
    """Dependency injection scopes.

    APP: Application-scoped (singleton) - one instance per application
    REQUEST: Request-scoped - new instance per request/operation
    """

    APP: Scope
    REQUEST: Scope

class DependencyMarker:
    """Runtime marker for dependency injection."""

    pass

class Depends:
    """Marker for dependency injection using Annotated type hints.

    Can be used as:
    - Depends[Type] in Annotated hints
    - Depends() as default parameter value
    """

    def __class_getitem__(cls, item: type[T]) -> type[T]: ...
    def __init__(self, dependency_type: type[T] | None = None) -> None: ...

class _ContextAccessor:
    """Context accessor for creating context fields."""

    def get(self, t: type[T]) -> ContextField[T]: ...

context: _ContextAccessor

@overload
def provider(
    func: Callable[P, R],
) -> Callable[P, R]: ...
@overload
def provider(
    *,
    scope: Scope | str = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
def singleton(func: Callable[P, R]) -> Callable[P, R]:
    """Shorthand for @provider(scope=Scope.APP).

    Creates an application-scoped (singleton) provider.
    """
    ...

def transient(target: type[T]) -> Transient:
    """Register a class as a transient (per-request) dependency.

    Unlike @provider, this works as a class attribute descriptor that
    automatically registers the class constructor as a provider.

    Example:
        class AppContainer(Container):
            user_service = transient(UserService)
    """
    ...

def init(container: Container | Sequence[Container]) -> None:
    """Initialize the global dependency injection container.

    Args:
        container: A single Container instance or sequence of containers.

    Raises:
        ValueError: If container sequence is empty.
    """

    ...

def inject(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator for automatic dependency injection.

    Injects dependencies based on function parameter type hints.
    Preserves original function signature for framework introspection.

    Args:
        func: Function to decorate with dependency injection.

    Returns:
        Decorated function with automatic dependency resolution.
    """

    ...
