"""Type stubs for spritze library.

Provides type hints for the Spritze dependency injection framework.
"""

from collections.abc import Callable
from enum import Enum
from typing import ParamSpec, TypeVar, overload

from spritze.api.provider_descriptor import ProviderDescriptor as ProviderDescriptor
from spritze.context import ContextField as ContextField
from spritze.core.container import Container as Container

__all__ = [
    "Container",
    "Scope",
    "Depends",
    "DependencyMarker",
    "provider",
    "inject",
    "resolve",
    "aresolve",
    "init",
    "get_context",
    "ContextField",
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

class _GlobalContext:
    """Global context accessor for setting context values."""

    def set(self, **kwargs: object) -> None:
        """Set context values using keyword arguments.

        Example:
            ctx = get_context()
            ctx.set(Config=config, DatabaseURL=db_url)
        """
        ...

@overload
def provider(
    func: Callable[P, R],
) -> Callable[P, R]: ...
@overload
def provider(
    *,
    scope: Scope | str = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
@overload
def provider(
    target: type[T],
    *,
    provides: type[object] | None = None,
    scope: Scope | str = ...,
) -> ProviderDescriptor: ...
def init(
    *containers: Container,
    context: dict[type[object], object] | None = None,
) -> None:
    """Initialize the global dependency injection container.

    Args:
        *containers: One or more Container instances to merge.
        context: Optional initial context values as {Type: value} mapping.

    Raises:
        ValueError: If no containers are provided.
    """

    ...

def get_context() -> _GlobalContext:
    """Get the global context accessor.

    Returns:
        Global context accessor for setting context values.

    Raises:
        RuntimeError: If init() has not been called yet.
    """

    ...

def inject(func: Callable[P, R]) -> Callable[..., R]:
    """Decorator for automatic dependency injection.

    Injects dependencies based on function parameter type hints.
    Parameters with Depends() are removed from signature and injected automatically.

    Args:
        func: Function to decorate with dependency injection.

    Returns:
        Decorated function with dependency parameters removed from signature.
    """

    ...

def resolve(dependency_type: type[T]) -> T:
    """Resolve a sync dependency by type.

    Use this for synchronous providers only.
    For async providers, use aresolve().

    Args:
        dependency_type: The type of the dependency to resolve.

    Returns:
        Resolved instance.

    Raises:
        DependencyNotFound: If no provider is registered for the type.
        CyclicDependency: If a circular dependency is detected.
        AsyncSyncMismatch: If provider is async (use aresolve instead).
        RuntimeError: If init() has not been called yet.
    """

    ...

async def aresolve(dependency_type: type[T]) -> T:
    """Resolve a dependency by type in async context.

    Works with both sync and async providers.

    Args:
        dependency_type: The type of the dependency to resolve.

    Returns:
        Resolved instance.

    Raises:
        DependencyNotFound: If no provider is registered for the type.
        CyclicDependency: If a circular dependency is detected.
        RuntimeError: If init() has not been called yet.
    """

    ...
