from __future__ import annotations

import inspect
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..value_objects.scope import Scope

from ..value_objects.provider_type import ProviderType


def _determine_provider_type(
    func: Callable[..., object],
) -> tuple[ProviderType, Callable[..., object]]:
    if inspect.isasyncgenfunction(func):
        return ProviderType.ASYNC_GEN, asynccontextmanager(func)
    elif inspect.isgeneratorfunction(func):
        return ProviderType.GEN, contextmanager(func)
    elif inspect.iscoroutinefunction(func):
        return ProviderType.ASYNC, func
    else:
        return ProviderType.SIMPLE, func


@dataclass(kw_only=True)
class Provider:
    func: Callable[..., object]
    scope: Scope
    return_type: type[object]
    provider_type: ProviderType = field(init=False)

    def __post_init__(self) -> None:
        self.provider_type, self.func = _determine_provider_type(self.func)

    @property
    def is_context_manager(self) -> bool:
        return self.provider_type in (ProviderType.GEN, ProviderType.ASYNC_GEN)

    @property
    def is_async(self) -> bool:
        return self.provider_type in (ProviderType.ASYNC, ProviderType.ASYNC_GEN)


__all__ = ["Provider"]
