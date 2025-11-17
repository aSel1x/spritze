"""Core container implementation."""

import inspect
from collections.abc import Callable, ItemsView, Iterator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    contextmanager,
)
from contextvars import ContextVar
from typing import Final, TypeVar, cast

from spritze.core.provider import Provider
from spritze.core.type_map import TypeMap
from spritze.exceptions import AsyncSyncMismatch, CyclicDependency, NoProviderFound
from spritze.internal.type_utils import get_function_dependencies
from spritze.types import Scope

__all__ = ("Container",)

PROVIDER_TAG: Final[str] = "__spritze_provider__"
T = TypeVar("T")


class Container:
    """Dependency injection container."""

    _allow_instantiation: bool = False

    def __init__(self) -> None:
        if not type(self)._allow_instantiation:
            raise TypeError(
                "Containers cannot be instantiated directly. "
                + "Please use spritze.init() to initialize your container."
            )

        self._providers: dict[type, Provider] = {}

        # Caching
        self._app_cache: TypeMap = TypeMap()
        self._request_cache: ContextVar[TypeMap] = ContextVar(
            "spritze_request_cache", default=TypeMap()
        )

        # Context managers
        self._app_sync_stack: ExitStack = ExitStack()
        self._app_async_stack: AsyncExitStack = AsyncExitStack()
        self._request_sync_stack: ContextVar[ExitStack] = ContextVar(
            "spritze_request_sync_stack", default=ExitStack()
        )
        self._request_async_stack: ContextVar[AsyncExitStack] = ContextVar(
            "spritze_request_async_stack", default=AsyncExitStack()
        )

        # Resolution tracking
        self._resolution_stack: ContextVar[tuple[type, ...]] = ContextVar(
            "spritze_resolution_stack", default=()
        )

        self._register_providers()

    def _register_providers(self) -> None:
        """Register providers from class definition."""
        providers: dict[type, Provider] = {}

        for base in reversed(self.__class__.mro()):
            items_view: ItemsView[str, object] = base.__dict__.items()
            for name, attr in items_view:
                if isinstance(attr, Provider):
                    providers[attr.provide_as] = attr
                    continue

                provider_info = getattr(attr, PROVIDER_TAG, None)
                if not isinstance(provider_info, Provider):
                    continue

                if inspect.isfunction(attr):
                    bound_method = getattr(self, name, None)
                    if callable(bound_method):
                        bound_provider = Provider.from_callable(
                            bound_method,
                            scope=provider_info.scope,
                            provide_as=provider_info.provide_as,
                        )
                        providers[bound_provider.provide_as] = bound_provider
                elif isinstance(attr, staticmethod):
                    providers[provider_info.provide_as] = provider_info
                else:
                    providers[provider_info.provide_as] = provider_info

        self._providers = providers

    @property
    def _app_scoped_instances(self) -> TypeMap:
        """Get APP-scoped instances for context initialization."""
        return self._app_cache

    def resolve(self, dependency_type: type[T]) -> T:
        """Resolve dependency synchronously."""
        result = self._resolve_impl(dependency_type, sync=True)
        if inspect.isawaitable(result):
            raise AsyncSyncMismatch(dependency_type, "synchronous")
        return cast(T, result)

    async def aresolve(self, dependency_type: type[T]) -> T:
        """Resolve dependency asynchronously."""
        result = await self._aresolve_impl(dependency_type)
        return cast(T, result)

    def _get_cached(self, dependency_type: type[T]) -> T | None:
        """Check all caches for existing instance."""
        if dependency_type in self._app_cache:
            return self._app_cache.get(dependency_type)

        request_cache = self._request_cache.get()
        if dependency_type in request_cache:
            return request_cache.get(dependency_type)

        return None

    def _cache_instance(
        self, dependency_type: type, instance: object, scope: Scope
    ) -> None:
        """Cache instance according to scope."""
        match scope:
            case Scope.APP:
                self._app_cache.set(dependency_type, instance)
            case Scope.REQUEST:
                self._request_cache.get().set(dependency_type, instance)
            case Scope.TRANSIENT:
                pass
            case _:
                pass

    @contextmanager
    def _track_resolution(self, dependency_type: type) -> Iterator[None]:
        """Track resolution to detect cycles."""
        stack = self._resolution_stack.get()
        if dependency_type in stack:
            raise CyclicDependency(stack + (dependency_type,))

        token = self._resolution_stack.set(stack + (dependency_type,))
        try:
            yield
        finally:
            self._resolution_stack.reset(token)

    def _get_provider(self, dependency_type: type) -> Provider:
        """Get provider for dependency type."""
        provider = self._providers.get(dependency_type)
        if not provider:
            raise NoProviderFound(dependency_type)
        return provider

    async def _aresolve_impl(self, dependency_type: type[T]) -> object:
        """Asynchronous dependency resolution."""
        cached = self._get_cached(dependency_type)
        if cached is not None:
            return cached

        with self._track_resolution(dependency_type):
            provider = self._get_provider(dependency_type)
            dependencies = await self._aresolve_dependencies(provider.factory)
            instance = await self._acreate_instance(provider, dependencies)

            if not inspect.isawaitable(instance):
                self._cache_instance(dependency_type, instance, provider.scope)

            return instance

    def _resolve_impl(self, dependency_type: type[T], sync: bool) -> object:
        """Synchronous dependency resolution."""
        cached = self._get_cached(dependency_type)
        if cached is not None:
            return cached

        with self._track_resolution(dependency_type):
            provider = self._get_provider(dependency_type)

            if sync and provider.is_async:
                raise AsyncSyncMismatch(dependency_type, "synchronous")

            dependencies = self._resolve_dependencies(provider.factory, sync)
            instance = self._create_instance(provider, dependencies, sync)

            if not inspect.isawaitable(instance):
                self._cache_instance(dependency_type, instance, provider.scope)

            return instance

    def _get_factory_dependencies(self, func: Callable[..., object]) -> dict[str, type]:
        """Get factory dependencies."""
        return get_function_dependencies(func, strict=True)

    async def _aresolve_dependencies(
        self, func: Callable[..., object]
    ) -> dict[str, object]:
        """Resolve dependencies asynchronously."""
        deps_to_resolve = self._get_factory_dependencies(func)
        dependencies: dict[str, object] = {}

        for name, dep_type in deps_to_resolve.items():
            dependencies[name] = await self.aresolve(dep_type)

        return dependencies

    def _resolve_dependencies(
        self, func: Callable[..., object], sync: bool
    ) -> dict[str, object]:
        """Resolve dependencies synchronously."""
        deps_to_resolve = self._get_factory_dependencies(func)
        dependencies: dict[str, object] = {}

        for name, dep_type in deps_to_resolve.items():
            dependency_result = self._resolve_impl(dep_type, sync)

            if sync and inspect.isawaitable(dependency_result):
                raise AsyncSyncMismatch(dep_type, "synchronous")

            dependencies[name] = dependency_result

        return dependencies

    def _get_stack(self, scope: Scope, is_async: bool) -> ExitStack | AsyncExitStack:
        """Get appropriate context manager stack."""
        match scope:
            case Scope.APP:
                return self._app_async_stack if is_async else self._app_sync_stack
            case Scope.REQUEST | Scope.TRANSIENT:
                return (
                    self._request_async_stack.get()
                    if is_async
                    else self._request_sync_stack.get()
                )
            case _:
                raise ValueError(f"Unknown scope: {scope}")

    def _create_sync_cm_instance(
        self, provider: Provider, dependencies: dict[str, object]
    ) -> object:
        """Create instance from sync context manager."""
        stack = cast(ExitStack, self._get_stack(provider.scope, False))
        raw_cm = provider.factory(**dependencies)
        cm = cast(AbstractContextManager[object], raw_cm)
        instance = stack.enter_context(cm)
        self._cache_instance(provider.provide_as, instance, provider.scope)
        return instance

    async def _acreate_async_cm_instance(
        self, provider: Provider, dependencies: dict[str, object]
    ) -> object:
        """Create instance from async context manager."""
        stack = cast(AsyncExitStack, self._get_stack(provider.scope, True))
        raw_acm = provider.factory(**dependencies)

        if inspect.iscoroutine(raw_acm):
            raw_acm = cast(AbstractAsyncContextManager[object], await raw_acm)

        acm = cast(AbstractAsyncContextManager[object], raw_acm)
        instance = await stack.enter_async_context(acm)
        self._cache_instance(provider.provide_as, instance, provider.scope)
        return instance

    async def _acreate_instance(
        self, provider: Provider, dependencies: dict[str, object]
    ) -> object:
        """Create instance asynchronously."""
        if not provider.is_context_manager:
            result = provider.factory(**dependencies)
            if inspect.iscoroutine(result):
                result = cast(object, await result)
            return result

        if provider.is_async:
            return await self._acreate_async_cm_instance(provider, dependencies)
        else:
            return self._create_sync_cm_instance(provider, dependencies)

    def _create_instance(
        self, provider: Provider, dependencies: dict[str, object], sync: bool
    ) -> object:
        """Create instance synchronously."""
        if not provider.is_context_manager:
            if dependencies:
                result = provider.factory(**dependencies)
            else:
                result = provider.factory()
            if sync and inspect.isawaitable(result):
                raise AsyncSyncMismatch(provider.provide_as, "synchronous")
            return result

        if provider.is_async:
            raise AsyncSyncMismatch(provider.provide_as, "synchronous")
        else:
            return self._create_sync_cm_instance(provider, dependencies)
