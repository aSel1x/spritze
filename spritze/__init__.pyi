"""Type stubs for spritze public API."""

from typing import Callable, ParamSpec, TypeVar, overload

from spritze.core.container import Container
from spritze.core.provider import Provider
from spritze.types import Depends, Scope

__all__ = (
    "Container",
    "Scope",
    "Depends",
    "provider",
    "inject",
    "resolve",
    "aresolve",
    "init",
)

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

def init(
    *containers: type[Container], context: dict[type, object] | None = None
) -> None: ...
def resolve(dependency_type: type[T]) -> T: ...
async def aresolve(dependency_type: type[T]) -> T: ...
def inject(func: Callable[P, R]) -> Callable[..., R]: ...
@overload
def provider(func: Callable[P, R]) -> Callable[P, R]: ...
@overload
def provider(
    *, scope: Scope = ..., provide_as: type | None = None
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...
@overload
def provider(
    target: type[T], *, scope: Scope = ..., provide_as: type | None = None
) -> Provider: ...
@overload
def provider(
    target: Callable[P, R], *, scope: Scope = ..., provide_as: type | None = None
) -> Provider: ...
def provider(
    target: Callable[P, R] | type[T] | None = None,
    *,
    scope: Scope = ...,
    provide_as: type | None = None,
) -> Provider | Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]: ...
