import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    AsyncExitStack,
    ExitStack,
    suppress,
)
from contextvars import ContextVar
from functools import wraps
from types import MappingProxyType
from typing import ParamSpec, TypeVar, cast, get_args, get_origin, get_type_hints

from spritze.api.provider_descriptor import ProviderDescriptor
from spritze.core.provider import Provider
from spritze.core.resolution import ResolutionService
from spritze.exceptions import CyclicDependency, DependencyNotFound, InvalidProvider
from spritze.types import DependencyMarker, ProviderType, Scope

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")
TypeMap = dict[str, type[object]]


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
        self._async_mode: ContextVar[bool] = ContextVar(
            "spritze_async_mode", default=False
        )

        self._register_providers()

    def get_context_value(self, t: type[object]) -> object | None:
        return self._context_values.get(t)

    def set_context_value(self, t: type[object], value: object) -> None:
        self._context_values[t] = value

    def _register_providers(self) -> None:
        self._register_function_providers()
        self._register_descriptor_providers()

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

        provides_val = meta.get("provides")
        provides_type = provides_val if isinstance(provides_val, type) else ret_type

        bound_method = cast("Callable[..., object]", getattr(self, name))
        self._providers[provides_type] = Provider(
            func=bound_method, scope=scope_val, return_type=ret_type
        )

    def _extract_return_type(self, func_obj: object) -> type[object] | None:
        ann_map: dict[str, object] = get_type_hints(func_obj, include_extras=False)
        ret_obj = ann_map.get("return")

        if isinstance(ret_obj, type):
            return cast("type[object]", ret_obj)

        origin_obj = get_origin(ret_obj)
        if origin_obj is not None:
            if isinstance(origin_obj, type) and hasattr(origin_obj, "__qualname__"):
                origin_name: str = origin_obj.__qualname__
                if origin_name in (
                    Generator.__qualname__,
                    AsyncGenerator.__qualname__,
                ):
                    args = get_args(ret_obj)
                    if args and isinstance(args[0], type):
                        return cast("type[object]", args[0])
            return cast("type[object]", ret_obj)

        return None

    def _register_descriptor_providers(self) -> None:
        class_vars: MappingProxyType[str, object] = vars(self.__class__)
        for _name, attr in class_vars.items():
            if isinstance(attr, ProviderDescriptor):
                self._register_single_descriptor_provider(attr)

    def _register_single_descriptor_provider(
        self, descriptor_attr: ProviderDescriptor
    ) -> None:
        target = descriptor_attr.target
        provides = descriptor_attr.provides or target
        scope = descriptor_attr.scope

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

        self._providers[provides] = Provider(
            func=cast("Callable[..., object]", ctor_provider),
            scope=scope,
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

    def is_async_provider(self, dependency_type: type[object]) -> bool:
        """Check if a provider for the given type is async."""
        provider = self._providers.get(dependency_type)
        return provider is not None and provider.is_async

    def resolve(self, dependency_type: type[T]) -> T | Awaitable[T]:
        """Resolve a dependency by type. Returns instance or awaitable."""
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

            async def _resolve_deps_async() -> dict[str, object]:
                kwargs: dict[str, object] = {}
                deps = ResolutionService.get_deps_to_resolve(provider.func)
                for name, dep_t in deps.items():
                    resolved = self.resolve(dep_t)
                    if inspect.isawaitable(resolved):
                        kwargs[name] = await resolved
                    else:
                        kwargs[name] = resolved
                return kwargs

            async def _execute_async() -> T:
                kwargs = await _resolve_deps_async()

                if provider.is_context_manager:
                    is_async_gen = (
                        provider.is_async
                        and provider.provider_type == ProviderType.ASYNC_GEN
                    )
                    if is_async_gen:
                        exit_stack = self._async_exit_stack.get()
                        acm_raw = provider.func(**kwargs)
                        acm = cast(AbstractAsyncContextManager[object], acm_raw)
                        instance_obj = await exit_stack.enter_async_context(acm)
                    else:
                        exit_stack_sync = self._sync_exit_stack.get()
                        cm_raw = provider.func(**kwargs)
                        cm = cast(AbstractContextManager[object], cm_raw)
                        instance_obj = exit_stack_sync.enter_context(cm)
                elif provider.provider_type == ProviderType.ASYNC:
                    coro = cast("Callable[..., Awaitable[object]]", provider.func)
                    instance_obj = await coro(**kwargs)
                else:
                    instance_obj = provider.func(**kwargs)

                self._cache_instance(dependency_type, instance_obj, provider.scope)
                return cast(T, instance_obj)

            if provider.is_async or self._async_mode.get():
                return _execute_async()

            kwargs: dict[str, object] = {}
            deps = ResolutionService.get_deps_to_resolve(provider.func)
            for name, dep_t in deps.items():
                kwargs[name] = self.resolve(dep_t)

            if provider.is_context_manager:
                cm_raw = provider.func(**kwargs)
                cm = cast(AbstractContextManager[object], cm_raw)
                instance_obj = self._sync_exit_stack.get().enter_context(cm)
            else:
                instance_obj = provider.func(**kwargs)

            self._cache_instance(dependency_type, instance_obj, provider.scope)
            return cast(T, instance_obj)

        finally:
            self._resolution_stack.reset(token_r)

    def inject(self, func: Callable[P, R]) -> Callable[..., R]:
        """Inject dependencies into function parameters."""
        sig = inspect.signature(func)
        ann_map = get_type_hints(func, include_extras=True)
        deps = ResolutionService.extract_dependencies_from_signature(sig, ann_map)
        is_async_func = inspect.iscoroutinefunction(func)

        def _check_and_inject(
            bound: inspect.BoundArguments, resolved: object, name: str
        ) -> None:
            """Helper to inject resolved dependency into bound arguments."""
            if inspect.isawaitable(resolved):
                if inspect.iscoroutine(resolved):
                    resolved.close()
                raise InvalidProvider(
                    f"Cannot inject async dependency into sync function {func.__name__}"
                )
            bound.arguments[name] = resolved

        async def _inject_async(bound: inspect.BoundArguments) -> None:
            """Inject dependencies asynchronously."""
            for name, dep_type in deps.items():
                needs_inject = name not in bound.arguments or isinstance(
                    bound.arguments.get(name), DependencyMarker
                )
                if not needs_inject:
                    continue

                resolved = self.resolve(dep_type)
                if inspect.isawaitable(resolved):
                    bound.arguments[name] = await resolved
                else:
                    bound.arguments[name] = resolved

        new_params = [
            param for name, param in sig.parameters.items() if name not in deps
        ]
        new_sig = sig.replace(parameters=new_params)

        if is_async_func:

            @wraps(func)
            async def _awrapper(*args: object, **kwargs: object) -> object:
                async with AsyncExitStack() as stack:
                    token_s = self._async_exit_stack.set(stack)
                    token_c = self._request_scoped_instances.set({})
                    token_a = self._async_mode.set(True)
                    try:
                        bound = sig.bind_partial(*args, **kwargs)
                        await _inject_async(bound)
                        coro = cast("Callable[..., Awaitable[object]]", func)
                        result: object = await coro(**bound.arguments)
                        return result
                    finally:
                        self._async_exit_stack.reset(token_s)
                        self._request_scoped_instances.reset(token_c)
                        self._async_mode.reset(token_a)

            with suppress(AttributeError, TypeError):
                setattr(_awrapper, "__signature__", new_sig)
            return cast("Callable[..., R]", _awrapper)
        else:

            @wraps(func)
            def _swrapper(*args: object, **kwargs: object) -> object:
                with ExitStack() as stack:
                    token_s = self._sync_exit_stack.set(stack)
                    token_c = self._request_scoped_instances.set({})
                    try:
                        bound = sig.bind_partial(*args, **kwargs)
                        for name, dep_type in deps.items():
                            needs_inject = name not in bound.arguments or isinstance(
                                bound.arguments.get(name), DependencyMarker
                            )
                            if needs_inject:
                                resolved = self.resolve(dep_type)
                                _check_and_inject(bound, resolved, name)
                        f_callable = cast("Callable[..., object]", func)
                        return f_callable(**bound.arguments)
                    finally:
                        self._sync_exit_stack.reset(token_s)
                        self._request_scoped_instances.reset(token_c)

            with suppress(AttributeError, TypeError):
                setattr(_swrapper, "__signature__", new_sig)
            return cast("Callable[..., R]", _swrapper)


__all__ = ["Container", "Scope", "Provider"]
