from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
)
from contextvars import ContextVar
from functools import wraps
from types import MappingProxyType
from typing import (
    ParamSpec,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from spritze.entities.provider import Provider
from spritze.entities.transient import Transient
from spritze.infrastructure.context import ContextField
from spritze.infrastructure.exceptions import (
    CyclicDependency,
    DependencyNotFound,
    InvalidProvider,
)
from spritze.services.resolution_service import ResolutionService
from spritze.value_objects.dependency_marker import DependsMarker
from spritze.value_objects.provider_type import ProviderType
from spritze.value_objects.scope import Scope

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")
TypeMap = dict[str, type[object]]


class _BoundContext:
    def __init__(self, container: "Container") -> None:
        self._container: Container = container

    def update(self, **kwargs: object) -> None:
        declared: TypeMap = {}
        class_attrs: MappingProxyType[str, object] = vars(self._container.__class__)
        for name, attr in class_attrs.items():
            if isinstance(attr, ContextField):
                cf = cast("ContextField[object]", attr)
                declared[name] = cf.ctx_type
                declared[cf.ctx_type.__name__] = cf.ctx_type

        for key, value in kwargs.items():
            t = declared.get(key)
            if t is None:
                vt = type(value)
                if vt.__name__ in declared:
                    t = declared[vt.__name__]
            if t is None:
                raise InvalidProvider(f"Unknown context key: {key}")
            self._container.set_context_value(t, value)


class Container:
    def __init__(self) -> None:
        self._providers: dict[type[object], Provider] = {}
        self._app_scoped_instances: dict[type[object], object] = {}
        self._request_scoped_instances: ContextVar[
            dict[type[object], object] | None
        ] = ContextVar("spritze_request_instances", default=None)
        self._async_exit_stack: ContextVar[AsyncExitStack] = ContextVar(
            "spritze_async_exit_stack"
        )
        self._sync_exit_stack: ContextVar[ExitStack] = ContextVar(
            "spritze_sync_exit_stack"
        )
        self._context_values: dict[type[object], object] = {}
        self._resolution_stack: ContextVar[tuple[type[object], ...]] = ContextVar(
            "spritze_resolution_stack", default=()
        )

        self._register_providers()

    @property
    def context(self) -> _BoundContext:
        return _BoundContext(self)

    def get_context_value(self, t: type[object]) -> object | None:
        return self._context_values.get(t)

    def set_context_value(self, t: type[object], value: object) -> None:
        self._context_values[t] = value

    def _register_providers(self) -> None:
        self._register_function_providers()
        self._register_transient_providers()

    def _register_function_providers(self) -> None:
        for name, func_obj in inspect.getmembers(
            self.__class__, predicate=inspect.isfunction
        ):
            if hasattr(func_obj, "__spritze_provider__"):
                self._register_single_function_provider(name, func_obj)

    def _register_single_function_provider(self, name: str, func_obj: object) -> None:
        meta: dict[str, object] = cast(
            "dict[str, object]", getattr(func_obj, "__spritze_provider__")
        )
        scope_val = meta.get("scope")
        if not isinstance(scope_val, Scope):
            raise InvalidProvider("Invalid scope on provider")

        ret_type = self._extract_return_type(func_obj)
        if ret_type is None:
            raise InvalidProvider(
                "Provider must declare a concrete return type annotation"
            )

        bound_method = cast("Callable[..., object]", getattr(self, name))
        self._providers[ret_type] = Provider(
            func=bound_method, scope=scope_val, return_type=ret_type
        )

    def _extract_return_type(self, func_obj: object) -> type[object] | None:
        ann_map: dict[str, object] = get_type_hints(func_obj, include_extras=False)
        ret_obj = ann_map.get("return")

        if isinstance(ret_obj, type):
            return cast("type[object]", ret_obj)

        origin_obj = get_origin(ret_obj)
        origin_name = getattr(origin_obj, "__qualname__", "")
        if origin_name in (
            Generator.__qualname__,
            AsyncGenerator.__qualname__,
        ):
            args = get_args(ret_obj)
            if args and isinstance(args[0], type):
                return cast("type[object]", args[0])

        return None

    def _register_transient_providers(self) -> None:
        class_vars: MappingProxyType[str, object] = vars(self.__class__)
        for _name, attr in class_vars.items():
            if isinstance(attr, Transient):
                self._register_single_transient_provider(attr)

    def _register_single_transient_provider(self, transient_attr: Transient) -> None:
        target = transient_attr.target
        ann_map_ctor = cast(
            "dict[str, object]",
            get_type_hints(target.__init__, include_extras=False),
        )

        def ctor_provider(**kwargs: object) -> object:
            return target(**kwargs)

        func_annotations: dict[str, object] = {}
        for pname, ann_obj in ann_map_ctor.items():
            if pname == "self" or pname == "return":
                continue
            if isinstance(ann_obj, type):
                func_annotations[pname] = ann_obj
        func_annotations["return"] = target
        ctor_provider.__annotations__ = func_annotations

        self._providers[target] = Provider(
            func=cast("Callable[..., object]", ctor_provider),
            scope=Scope.REQUEST,
            return_type=target,
        )

    def _check_cache(self, dependency_type: type[T]) -> T | None:
        if dependency_type in self._app_scoped_instances:
            return cast("T", self._app_scoped_instances[dependency_type])
        if dependency_type in self._context_values:
            return cast("T", self._context_values[dependency_type])
        request_cache = self._request_scoped_instances.get()
        if request_cache is not None and dependency_type in request_cache:
            return cast("T", request_cache[dependency_type])
        return None

    def _cache_instance(
        self, dependency_type: type[object], instance: object, scope: Scope
    ) -> None:
        if scope == Scope.APP:
            self._app_scoped_instances[dependency_type] = instance
        elif scope == Scope.REQUEST:
            request_cache: dict[type[object], object] | None = (
                self._request_scoped_instances.get()
            )
            if request_cache is None:
                request_cache = {}
                _ = self._request_scoped_instances.set(request_cache)
            request_cache[dependency_type] = instance

    def _resolve_provider_dependencies_sync(
        self, provider: Provider
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {}
        deps = ResolutionService.get_deps_to_resolve(provider.func)
        for name, dep_t in deps.items():
            kwargs[name] = self.resolve(dep_t)
        return kwargs

    async def _resolve_provider_dependencies_async(
        self, provider: Provider
    ) -> dict[str, object]:
        kwargs: dict[str, object] = {}
        deps = ResolutionService.get_deps_to_resolve(provider.func)
        for name, dep_t in deps.items():
            kwargs[name] = await self.resolve_async(dep_t)
        return kwargs

    def _execute_provider(
        self, provider: Provider, kwargs: dict[str, object]
    ) -> object:
        if provider.is_context_manager:
            cm_raw = provider.func(**kwargs)
            cm = cast("AbstractContextManager[object]", cm_raw)
            return self._sync_exit_stack.get().enter_context(cm)
        else:
            return provider.func(**kwargs)

    async def _execute_provider_async(
        self, provider: Provider, kwargs: dict[str, object]
    ) -> object:
        if provider.is_context_manager:
            exit_stack = self._async_exit_stack.get()
            if provider.provider_type == ProviderType.ASYNC_GEN:
                acm_raw = provider.func(**kwargs)
                acm = cast("AbstractAsyncContextManager[object]", acm_raw)
                return await exit_stack.enter_async_context(acm)
            else:
                cm_raw = provider.func(**kwargs)
                cm = cast("AbstractContextManager[object]", cm_raw)
                return exit_stack.enter_context(cm)
        elif provider.provider_type == ProviderType.ASYNC:
            coro = cast("Callable[..., Awaitable[object]]", provider.func)
            return await coro(**kwargs)
        else:
            return provider.func(**kwargs)

    def _resolve_with_cycle_check_sync(self, dependency_type: type[T]) -> T:
        cached = self._check_cache(dependency_type)
        if cached is not None:
            return cached

        stack = self._resolution_stack.get()
        if dependency_type in stack:
            raise CyclicDependency(stack + (dependency_type,))

        token_r = self._resolution_stack.set(stack + (dependency_type,))
        try:
            provider = self._providers.get(dependency_type)
            if provider is None:
                raise DependencyNotFound(dependency_type)

            if provider.is_async:
                raise InvalidProvider(
                    "Cannot resolve async provider for "
                    + f"{dependency_type.__name__} in sync context"
                )

            kwargs = self._resolve_provider_dependencies_sync(provider)
            instance_obj = self._execute_provider(provider, kwargs)

            self._cache_instance(dependency_type, instance_obj, provider.scope)
            return cast("T", instance_obj)
        finally:
            self._resolution_stack.reset(token_r)

    async def _resolve_with_cycle_check_async(self, dependency_type: type[T]) -> T:
        cached = self._check_cache(dependency_type)
        if cached is not None:
            return cached

        stack = self._resolution_stack.get()
        if dependency_type in stack:
            raise CyclicDependency(stack + (dependency_type,))

        token_r = self._resolution_stack.set(stack + (dependency_type,))
        try:
            provider = self._providers.get(dependency_type)
            if provider is None:
                raise DependencyNotFound(dependency_type)

            kwargs = await self._resolve_provider_dependencies_async(provider)
            instance_obj = await self._execute_provider_async(provider, kwargs)

            self._cache_instance(dependency_type, instance_obj, provider.scope)
            return cast("T", instance_obj)
        finally:
            self._resolution_stack.reset(token_r)

    def resolve(self, dependency_type: type[T]) -> T:
        return self._resolve_with_cycle_check_sync(dependency_type)

    async def resolve_async(self, dependency_type: type[T]) -> T:
        return await self._resolve_with_cycle_check_async(dependency_type)

    def injector(self) -> Callable[[Callable[P, R]], Callable[..., R]]:
        def decorator(func: Callable[P, R]) -> Callable[..., R]:
            sig = inspect.signature(func)
            ann_map = get_type_hints(func, include_extras=True)
            deps = ResolutionService.extract_dependencies_from_signature(sig, ann_map)

            def _inject_dependencies_sync(bound: inspect.BoundArguments) -> None:
                for name, t in deps.items():
                    needs_inject = name not in bound.arguments or isinstance(
                        bound.arguments.get(name), DependsMarker
                    )
                    if needs_inject:
                        bound.arguments[name] = self.resolve(t)

            async def _inject_dependencies_async(bound: inspect.BoundArguments) -> None:
                for name, t in deps.items():
                    needs_inject = name not in bound.arguments or isinstance(
                        bound.arguments.get(name), DependsMarker
                    )
                    if needs_inject:
                        bound.arguments[name] = await self.resolve_async(t)

            if inspect.iscoroutinefunction(func):

                @wraps(func)
                async def _awrapper(*args: object, **kwargs: object) -> object:
                    async with AsyncExitStack() as stack:
                        token_s = self._async_exit_stack.set(stack)
                        token_c = self._request_scoped_instances.set({})
                        try:
                            bound = sig.bind_partial(*args, **kwargs)
                            await _inject_dependencies_async(bound)
                            coro = cast("Callable[..., Awaitable[object]]", func)
                            result: object = await coro(**bound.arguments)
                            return result
                        finally:
                            self._async_exit_stack.reset(token_s)
                            self._request_scoped_instances.reset(token_c)

                from contextlib import suppress

                with suppress(Exception):
                    setattr(_awrapper, "__signature__", sig.replace(parameters=()))
                return cast("Callable[..., R]", _awrapper)
            else:

                @wraps(func)
                def _swrapper(*args: object, **kwargs: object) -> object:
                    with ExitStack() as stack:
                        token_s = self._sync_exit_stack.set(stack)
                        token_c = self._request_scoped_instances.set({})
                        try:
                            bound = sig.bind_partial(*args, **kwargs)
                            _inject_dependencies_sync(bound)
                            f_callable = cast("Callable[..., object]", func)
                            return f_callable(**bound.arguments)
                        finally:
                            self._sync_exit_stack.reset(token_s)
                            self._request_scoped_instances.reset(token_c)

                from contextlib import suppress

                with suppress(Exception):
                    setattr(_swrapper, "__signature__", sig.replace(parameters=()))
                return cast("Callable[..., R]", _swrapper)

        return cast("Callable[[Callable[P, R]], Callable[..., R]]", decorator)


__all__ = ["Container", "Scope", "Transient", "Provider"]
