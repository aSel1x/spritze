"""Type annotation utilities."""

import inspect
from typing import Annotated, Callable, cast, get_args, get_origin

from spritze.exceptions import DependsTypeMissingOrInvalid
from spritze.types import Depends

__all__ = ("unwrap_type", "extract_dependency_from_param", "get_function_dependencies")


def unwrap_type(rt: object) -> type:
    """Unwrap complex type annotations to get the underlying type.

    Handles:
    - Annotated[Type, ...]
    - Generator[Type, None, None]
    - AsyncGenerator[Type, None]
    - ContextManager[Type]
    - AsyncContextManager[Type]
    """
    origin = get_origin(rt)
    args: tuple[type, ...] = get_args(rt)

    if origin is Annotated:
        return unwrap_type(args[0])

    if (
        origin is not None
        and hasattr(origin, "__name__")  # pyright: ignore[reportAny]
        and origin.__name__  # pyright: ignore[reportAny]
        in (
            "Generator",
            "AsyncGenerator",
            "ContextManager",
            "AsyncContextManager",
            "Iterable",
            "AsyncIterable",
        )
    ):
        if args:
            return unwrap_type(args[0])
        else:
            raise DependsTypeMissingOrInvalid(
                f"Cannot unwrap type, missing type argument: {rt!r}"
            )

    if isinstance(rt, type):
        return rt

    if get_origin(rt) is not None:
        return cast(type, rt)  # Return the generic type as-is

    raise DependsTypeMissingOrInvalid(f"Return type is not a type: {rt!r}")


def extract_dependency_from_param(param: inspect.Parameter) -> type | None:
    """Extract dependency type from function parameter if it uses Depends."""
    default = param.default  # pyright: ignore[reportAny]
    annotation = param.annotation  # pyright: ignore[reportAny]

    # Direct Depends() usage as default
    if isinstance(default, Depends):
        if default.dependency_type is not None:
            return default.dependency_type
        elif annotation is not inspect.Parameter.empty:
            return annotation  # pyright: ignore[reportAny]
        else:
            raise DependsTypeMissingOrInvalid(
                f"Parameter '{param.name}' missing dependency type"
            )

    # Annotated[Type, Depends()] usage
    if annotation is not inspect.Parameter.empty:
        origin = get_origin(annotation)  # pyright: ignore[reportAny]
        if origin is not None:
            origin_name = getattr(origin, "__name__", None)  # pyright: ignore[reportAny]
            if origin_name == "Annotated":
                args: tuple[type, ...] = get_args(annotation)
                if len(args) >= 2:
                    actual_type = args[0]
                    metadata = args[1:]
                    for meta in metadata:
                        if isinstance(meta, Depends):
                            if meta.dependency_type is not None:
                                return meta.dependency_type
                            else:
                                return actual_type

    return None


def get_function_dependencies(
    func: Callable[..., object], *, strict: bool = False
) -> dict[str, type]:
    """Extract dependencies from function signature.

    Args:
        func: Function to analyze
        strict: If True, raise error for parameters without type annotations

    Returns:
        Dict mapping parameter names to their types
    """
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        return {}

    deps: dict[str, type] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue

        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        if param.default is not inspect.Parameter.empty:  # pyright: ignore[reportAny]
            continue

        annotation = param.annotation  # pyright: ignore[reportAny]

        if annotation is inspect.Parameter.empty:
            if strict:
                from spritze.exceptions import DependsTypeMissingOrInvalid

                raise DependsTypeMissingOrInvalid(
                    f"Parameter '{name}' has invalid type annotation"
                )
            continue

        if (
            not isinstance(annotation, type) and get_origin(annotation) is None  # pyright: ignore[reportAny]
        ):
            if strict:
                from spritze.exceptions import DependsTypeMissingOrInvalid

                raise DependsTypeMissingOrInvalid(
                    f"Parameter '{name}' has invalid type annotation"
                )
            continue

        deps[name] = annotation

    return deps
