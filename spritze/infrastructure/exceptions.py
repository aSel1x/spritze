from __future__ import annotations


class SpritzeError(Exception):
    pass


class DependencyNotFound(SpritzeError):
    dependency_type: type[object]

    def __init__(self, dependency_type: type[object]) -> None:
        super().__init__(
            f"Dependency of type '{dependency_type.__name__}' not found. "
            + "Make sure it's registered as a provider or transient dependency."
        )
        self.dependency_type = dependency_type


class InvalidProvider(SpritzeError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid provider configuration: {message}")


class CyclicDependency(SpritzeError):
    stack: tuple[type[object], ...]

    def __init__(self, stack: tuple[type[object], ...]) -> None:
        path = " -> ".join(t.__name__ for t in stack)
        super().__init__(
            f"Cyclic dependency detected: {path}. "
            + "Review your dependency graph to break the cycle."
        )
        self.stack = stack


class AsyncSyncMismatch(SpritzeError):
    def __init__(self, dependency_type: type[object], context: str) -> None:
        super().__init__(
            f"Cannot resolve async provider for '{dependency_type.__name__}' "
            + f"in {context} context. Use resolve_async() for async dependencies."
        )


__all__ = [
    "AsyncSyncMismatch",
    "CyclicDependency",
    "DependencyNotFound",
    "InvalidProvider",
    "SpritzeError",
]
