from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast, get_args, get_type_hints

if TYPE_CHECKING:
    import inspect
    from collections.abc import Callable

T = TypeVar("T")
TypeMap = dict[str, type[object]]


class ResolutionService:
    @staticmethod
    def get_deps_to_resolve(func: Callable[..., object]) -> TypeMap:
        deps: dict[str, type[object]] = {}
        ann_map = cast("dict[str, object]", get_type_hints(func, include_extras=False))
        for name, ann_obj in ann_map.items():
            if name in ("self", "return"):
                continue
            if isinstance(ann_obj, type):
                deps[name] = ann_obj
        return deps

    @staticmethod
    def extract_dependencies_from_signature(
        sig: inspect.Signature, ann_map: dict[str, object]
    ) -> TypeMap:
        deps: dict[str, type[object]] = {}

        for p in sig.parameters.values():
            ann_obj: object | None = ann_map.get(p.name)
            dep_type = ResolutionService._extract_dependency_type(p, ann_obj)
            if dep_type is not None:
                deps[p.name] = dep_type

        return deps

    @staticmethod
    def _extract_dependency_type(
        param: inspect.Parameter, ann_obj: object | None
    ) -> type[object] | None:
        from spritze.value_objects.dependency_marker import Depends, DependsMarker

        if isinstance(cast("object", param.default), DependsMarker):
            dm_def = cast("DependsMarker[object]", param.default)
            if isinstance(ann_obj, type):
                return ann_obj
            if isinstance(dm_def.dependency_type, type):
                return dm_def.dependency_type
            return None

        if getattr(ann_obj, "__origin__", None) is Depends:
            args = cast("tuple[object, ...]", get_args(ann_obj))
            if args and isinstance(args[0], type):
                return cast("type[object]", args[0])

        args_tuple = cast("tuple[object, ...]", get_args(ann_obj))
        if args_tuple and len(args_tuple) >= 2:
            base = args_tuple[0]
            meta = args_tuple[1:]
            dep_markers: list[DependsMarker[object]] = [
                cast("DependsMarker[object]", m)
                for m in meta
                if isinstance(m, DependsMarker)
            ]
            if dep_markers:
                dm = dep_markers[0]
                if isinstance(dm.dependency_type, type):
                    return dm.dependency_type
                if isinstance(base, type):
                    return base

        return None


__all__ = ["ResolutionService"]
