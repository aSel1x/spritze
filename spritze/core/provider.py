"""Provider implementation."""

import inspect
from abc import ABCMeta
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import NoReturn, get_type_hints

from spritze.internal.type_utils import get_function_dependencies, unwrap_type
from spritze.types import ProviderType, Scope

__all__ = ("Provider",)


@dataclass(init=False, repr=True, eq=True, frozen=True, slots=True)
class Provider:
    """Dependency provider with optimized analysis."""

    factory: Callable[..., object]
    scope: Scope
    provide_as: type
    provider_type: ProviderType
    _dependencies: dict[str, type] | None = None

    def __init__(self) -> NoReturn:
        raise TypeError("Use Provider.from_callable() instead")

    @classmethod
    def from_callable(
        cls,
        callable_obj: Callable[..., object],
        *,
        scope: Scope,
        provide_as: type | None = None,
    ) -> "Provider":
        """Create provider from callable."""
        if isinstance(callable_obj, staticmethod):
            callable_obj = callable_obj.__func__

        if inspect.isasyncgenfunction(callable_obj):
            factory = asynccontextmanager(callable_obj)
            provider_type = ProviderType.ASYNC_GEN
        elif inspect.isgeneratorfunction(callable_obj):
            factory = contextmanager(callable_obj)
            provider_type = ProviderType.SYNC_GEN
        elif inspect.iscoroutinefunction(callable_obj):
            factory = callable_obj
            provider_type = ProviderType.ASYNC
        else:
            factory = callable_obj
            provider_type = ProviderType.SYNC

        if provide_as is None:
            provide_as = cls._get_provide_as(callable_obj)

        if inspect.isclass(callable_obj):
            init_method = callable_obj.__init__
            if init_method is not object.__init__:
                init_sig = inspect.signature(init_method)
                new_params = [
                    param
                    for name, param in init_sig.parameters.items()
                    if name != "self"
                ]
                setattr(
                    factory, "__signature__", init_sig.replace(parameters=new_params)
                )

        self = object.__new__(cls)
        object.__setattr__(self, "factory", factory)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "provide_as", provide_as)
        object.__setattr__(self, "provider_type", provider_type)
        # Cache dependencies analysis
        deps = cls._analyze_dependencies(factory)
        object.__setattr__(self, "_dependencies", deps)

        return self

    @staticmethod
    @lru_cache(maxsize=256)
    def _analyze_dependencies(func: Callable[..., object]) -> dict[str, type]:
        """Analyze and cache function dependencies."""
        return get_function_dependencies(func, strict=False)

    @property
    def dependencies(self) -> dict[str, type]:
        """Get cached dependencies."""
        return self._dependencies or {}

    @classmethod
    def _get_provide_as(cls, callable_obj: Callable[..., object]) -> type[object]:
        """Determine what type this callable provides."""
        if inspect.isclass(callable_obj):
            return cls._find_abstract_type(callable_obj)

        return cls._extract_return_type(callable_obj)

    @staticmethod
    def _find_abstract_type(target: type) -> type:
        """Find abstract type for class."""
        if isinstance(target, ABCMeta) or getattr(target, "_is_protocol", False):
            return target

        for base in inspect.getmro(target)[1:]:
            if base is object:
                continue
            if isinstance(base, ABCMeta) or getattr(base, "_is_protocol", False):
                return base

        return target

    @staticmethod
    def _extract_return_type(func: Callable[..., object]) -> type:
        """Extract return type from callable."""
        try:
            hints = get_type_hints(func, include_extras=True)
        except Exception as e:
            raise TypeError(
                f"Failed to resolve type hints for {func.__name__}: {e}"
            ) from e

        rt_hint: object = hints.get("return", None)
        if rt_hint is None:
            raise TypeError(
                f"Provider {func.__name__} must have return type annotation"
            )

        final_type = unwrap_type(rt_hint)

        return final_type

    @property
    def is_context_manager(self) -> bool:
        """Whether this provider creates context managers."""
        return self.provider_type in (ProviderType.SYNC_GEN, ProviderType.ASYNC_GEN)

    @property
    def is_async(self) -> bool:
        """Whether this provider is asynchronous."""
        return self.provider_type in (ProviderType.ASYNC, ProviderType.ASYNC_GEN)
