import inspect
from collections.abc import Callable
from typing import TypeVar, cast, get_args, get_origin, get_type_hints

from spritze.types import DependencyMarker, Depends

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
        if isinstance(cast("object", param.default), DependencyMarker):
            dm_def = cast("DependencyMarker[object]", param.default)
            if isinstance(ann_obj, type):
                return ann_obj
            if get_origin(ann_obj) is not None:
                return cast("type[object]", ann_obj)
            if isinstance(dm_def.dependency_type, type):
                return dm_def.dependency_type
            return None

        if getattr(ann_obj, "__origin__", None) is Depends:
            args = cast("tuple[object, ...]", get_args(ann_obj))
            if args:
                first_arg = args[0]
                if isinstance(first_arg, type):
                    return first_arg
                if get_origin(first_arg) is not None:
                    return cast("type[object]", first_arg)

        args_tuple = cast("tuple[object, ...]", get_args(ann_obj))
        if args_tuple and len(args_tuple) >= 2:
            base = args_tuple[0]
            meta = args_tuple[1:]
            dep_markers: list[DependencyMarker[object]] = [
                cast("DependencyMarker[object]", m)
                for m in meta
                if isinstance(m, DependencyMarker)
            ]
            if dep_markers:
                dm = dep_markers[0]
                if isinstance(dm.dependency_type, type):
                    return dm.dependency_type
                if isinstance(base, type):
                    return base
                if get_origin(base) is not None:
                    return cast("type[object]", base)

        return None

    @staticmethod
    def create_signature_without_dependencies(
        func: Callable[..., object],
    ) -> tuple[inspect.Signature, TypeMap]:
        """Extract dependencies and create new signature without them.

        Returns:
            Tuple of (new_signature, dependencies_dict)
        """
        sig = inspect.signature(func)
        ann_map = get_type_hints(func, include_extras=True)
        deps = ResolutionService.extract_dependencies_from_signature(sig, ann_map)
        new_params = [
            param for name, param in sig.parameters.items() if name not in deps
        ]
        new_sig = sig.replace(parameters=new_params)
        return new_sig, deps


__all__ = ["ResolutionService"]
