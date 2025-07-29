import inspect
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Self, TypeVar

from spritze.core.entities import Scope, _Depends
from spritze.core.exceptions import (
    DependencyNotFoundError,
    InvalidProviderError,
    SpritzeException,
)
from spritze.decorators import PROVIDER_TAG


class ProviderType(Enum):
    SIMPLE = auto()
    GENERATOR = auto()
    ASYNC = auto()
    ASYNC_GENERATOR = auto()


@dataclass(kw_only=True)
class Provider:
    func: Callable[..., Any]
    scope: Scope
    provider_type: ProviderType = field(init=False)

    def __post_init__(self) -> None:
        match self.func:
            case f if inspect.isasyncgenfunction(f):
                self.provider_type = ProviderType.ASYNC_GENERATOR
                self.func = asynccontextmanager(self.func)
            case f if inspect.isgeneratorfunction(f):
                self.provider_type = ProviderType.GENERATOR
                self.func = contextmanager(self.func)
            case f if inspect.iscoroutinefunction(f):
                self.provider_type = ProviderType.ASYNC
            case _:
                self.provider_type = ProviderType.SIMPLE

    @property
    def is_context_manager(self) -> bool:
        return self.provider_type in (
            ProviderType.GENERATOR,
            ProviderType.ASYNC_GENERATOR,
        )

    @property
    def is_async(self) -> bool:
        return self.provider_type in (ProviderType.ASYNC, ProviderType.ASYNC_GENERATOR)


T = TypeVar("T")


class Container:
    """
    A dependency injection container that manages object creation and lifecycle.
    """

    def __init__(self: Self) -> None:
        self._providers: dict[type, Provider] = {}
        self._app_scoped_instances: dict[type, Any] = {}
        self._request_scoped_instances: ContextVar[dict[type, Any]] = ContextVar(
            "request_scoped_instances"
        )
        self._async_exit_stack: ContextVar[AsyncExitStack] = ContextVar(
            "async_exit_stack"
        )
        self._sync_exit_stack: ContextVar[ExitStack] = ContextVar("sync_exit_stack")
        self._register_providers()

    def _get_provider_parameters_to_resolve(
        self: Self, provider: Provider
    ) -> dict[str, type]:
        """Identifies provider function parameters to be resolved."""
        deps_to_resolve = {}
        sig_params = inspect.signature(provider.func).parameters
        for name, param in sig_params.items():
            if name == "self":
                continue
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            if isinstance(param.annotation, type):
                deps_to_resolve[name] = param.annotation
        return deps_to_resolve

    def _register_providers(self: Self) -> None:
        """Registers provider methods decorated with @provide."""
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, PROVIDER_TAG):
                provider_info = getattr(method, PROVIDER_TAG)
                sig = inspect.signature(method)
                dep_type = sig.return_annotation
                if dep_type is inspect.Signature.empty:
                    raise InvalidProviderError(
                        f"Provider '{name}' must have a return type annotation."
                    )
                bound_method = getattr(self, name)
                self._providers[dep_type] = Provider(
                    func=bound_method, scope=provider_info["scope"]
                )

    def resolve_sync(self: Self, dependency_type: type[T]) -> T:
        """Resolves a dependency synchronously."""
        if dependency_type in self._app_scoped_instances:
            return self._app_scoped_instances[dependency_type]

        request_cache = self._request_scoped_instances.get({})
        if dependency_type in request_cache:
            return request_cache[dependency_type]

        if dependency_type not in self._providers:
            raise DependencyNotFoundError(dependency_type)

        provider = self._providers[dependency_type]
        if provider.is_async:
            raise SpritzeException(
                f"Cannot resolve async provider "
                f"'{dependency_type.__name__}' in a sync context."
            )

        kwargs = {}
        deps_to_resolve = self._get_provider_parameters_to_resolve(provider)
        for name, dep_type in deps_to_resolve.items():
            kwargs[name] = self.resolve_sync(dep_type)

        if provider.is_context_manager:
            instance = self._sync_exit_stack.get().enter_context(
                provider.func(**kwargs)
            )
        else:
            instance = provider.func(**kwargs)

        if provider.scope == Scope.APP:
            self._app_scoped_instances[dependency_type] = instance
        elif provider.scope == Scope.REQUEST:
            request_cache[dependency_type] = instance

        return instance

    async def resolve_async(self: Self, dependency_type: type[T]) -> T:
        """Resolves a dependency asynchronously."""
        if dependency_type in self._app_scoped_instances:
            return self._app_scoped_instances[dependency_type]

        request_cache = self._request_scoped_instances.get({})
        if dependency_type in request_cache:
            return request_cache[dependency_type]

        if dependency_type not in self._providers:
            raise DependencyNotFoundError(dependency_type)

        provider = self._providers[dependency_type]

        kwargs = {}
        deps_to_resolve = self._get_provider_parameters_to_resolve(provider)
        for name, dep_type in deps_to_resolve.items():
            kwargs[name] = await self.resolve_async(dep_type)

        if provider.is_context_manager:
            exit_stack = self._async_exit_stack.get()
            match provider.provider_type:
                case ProviderType.ASYNC_GENERATOR:
                    instance = await exit_stack.enter_async_context(
                        provider.func(**kwargs)
                    )
                case _:
                    instance = exit_stack.enter_context(provider.func(**kwargs))
        elif provider.provider_type == ProviderType.ASYNC:
            instance = await provider.func(**kwargs)
        else:
            instance = provider.func(**kwargs)

        if provider.scope == Scope.APP:
            self._app_scoped_instances[dependency_type] = instance
        elif provider.scope == Scope.REQUEST:
            request_cache[dependency_type] = instance

        return instance

    def injector(self: Self) -> Callable:
        """Returns a decorator that enables dependency injection for a function."""

        def inject(func: Callable[..., Any]) -> Callable[..., Any]:
            is_async_func = inspect.iscoroutinefunction(func)

            original_sig = inspect.signature(func)
            new_params = [
                p
                for p in original_sig.parameters.values()
                if not isinstance(p.annotation, _Depends)
            ]
            deps_to_inject = {
                p.name: p.annotation.dependency_type
                for p in original_sig.parameters.values()
                if isinstance(p.annotation, _Depends)
            }
            new_sig = original_sig.replace(parameters=new_params)

            if is_async_func:

                @wraps(func)
                async def async_wrapper(*args, **kwargs) -> Any:
                    async with AsyncExitStack() as stack:
                        token_stack = self._async_exit_stack.set(stack)
                        token_cache = self._request_scoped_instances.set({})
                        try:
                            bound_args = original_sig.bind_partial(*args, **kwargs)
                            for name, dep_type in deps_to_inject.items():
                                if name not in bound_args.arguments:
                                    bound_args.arguments[
                                        name
                                    ] = await self.resolve_async(dep_type)
                            result = await func(*bound_args.args, **bound_args.kwargs)
                        finally:
                            self._async_exit_stack.reset(token_stack)
                            self._request_scoped_instances.reset(token_cache)
                    return result

                async_wrapper.__signature__ = new_sig
                return async_wrapper
            else:  # Sync function

                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with ExitStack() as stack:
                        token_stack = self._sync_exit_stack.set(stack)
                        token_cache = self._request_scoped_instances.set({})
                        try:
                            bound_args = original_sig.bind_partial(*args, **kwargs)
                            for name, dep_type in deps_to_inject.items():
                                if name not in bound_args.arguments:
                                    bound_args.arguments[name] = self.resolve_sync(
                                        dep_type
                                    )
                            result = func(*bound_args.args, **bound_args.kwargs)
                        finally:
                            self._sync_exit_stack.reset(token_stack)
                            self._request_scoped_instances.reset(token_cache)
                    return result

                sync_wrapper.__signature__ = new_sig
                return sync_wrapper

        return inject


__all__ = ["Container"]
