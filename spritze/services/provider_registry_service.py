from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, TypeVar, cast, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

from spritze.entities.provider import Provider
from spritze.entities.transient import Transient
from spritze.infrastructure.exceptions import InvalidProvider
from spritze.value_objects.scope import Scope

T = TypeVar("T")


class ProviderRegistryService:
    @staticmethod
    def register_function_providers(
        container_instance: object, providers: dict[type[object], Provider]
    ) -> None:
        func_members: list[tuple[str, object]] = list(
            inspect.getmembers(
                container_instance.__class__, predicate=inspect.isfunction
            )
        )
        for name, func_obj in func_members:
            if hasattr(func_obj, "__spritze_provider__"):
                ProviderRegistryService._register_single_function_provider(
                    container_instance, name, func_obj, providers
                )

    @staticmethod
    def register_transient_providers(
        container_instance: object, providers: dict[type[object], Provider]
    ) -> None:
        class_items: list[tuple[str, object]] = list(
            vars(container_instance.__class__).items()
        )
        for _name, attr in class_items:
            if isinstance(attr, Transient):
                ProviderRegistryService._register_single_transient_provider(
                    attr, providers
                )

    @staticmethod
    def _register_single_function_provider(
        container_instance: object,
        name: str,
        func_obj: object,
        providers: dict[type[object], Provider],
    ) -> None:
        meta_raw = getattr(func_obj, "__spritze_provider__", None)
        if meta_raw is None:
            return
        meta: dict[str, object] = cast("dict[str, object]", meta_raw)
        scope_val = meta.get("scope")
        if not isinstance(scope_val, Scope):
            raise InvalidProvider("Invalid scope on provider")

        ret_type = ProviderRegistryService._extract_return_type(func_obj)
        if ret_type is None:
            raise InvalidProvider(
                "Provider must declare a concrete return type annotation"
            )

        bound_method = cast("Callable[..., object]", getattr(container_instance, name))
        providers[ret_type] = Provider(
            func=bound_method, scope=scope_val, return_type=ret_type
        )

    @staticmethod
    def _register_single_transient_provider(
        transient_attr: Transient, providers: dict[type[object], Provider]
    ) -> None:
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

        providers[target] = Provider(
            func=cast("Callable[..., object]", ctor_provider),
            scope=Scope.REQUEST,
            return_type=target,
        )

    @staticmethod
    def _extract_return_type(func_obj: object) -> type[object] | None:
        ann_map: dict[str, object] = get_type_hints(func_obj, include_extras=False)
        ret_obj = ann_map.get("return")

        if isinstance(ret_obj, type):
            return cast("type[object]", ret_obj)

        origin_obj = get_origin(ret_obj)
        origin_name = getattr(origin_obj, "__qualname__", "")
        if origin_name in ("Generator", "AsyncGenerator"):
            args = get_args(ret_obj)
            if args and isinstance(args[0], type):
                return cast("type[object]", args[0])

        return None


__all__ = ["ProviderRegistryService"]
