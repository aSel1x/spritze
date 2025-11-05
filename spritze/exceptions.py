class SpritzeError(Exception):
    pass


class DependencyNotFound(SpritzeError):
    dependency_type: type[object]

    def __init__(self, dependency_type: type[object]) -> None:
        super().__init__(
            f"Dependency '{dependency_type.__name__}' not found. "
            + "Ensure it's registered as a provider."
        )
        self.dependency_type = dependency_type


class InvalidProvider(SpritzeError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid provider configuration: {message}")


class CyclicDependency(SpritzeError):
    stack: tuple[type[object], ...]

    def __init__(self, stack: tuple[type[object], ...]) -> None:
        path = " -> ".join(t.__name__ for t in stack)
        super().__init__(f"Cyclic dependency: {path}")
        self.stack = stack


class AsyncSyncMismatch(SpritzeError):
    def __init__(self, dependency_type: type[object], context: str) -> None:
        super().__init__(
            "Cannot resolve async provider "
            + f"'{dependency_type.__name__}' in {context} context."
        )


__all__ = [
    "AsyncSyncMismatch",
    "CyclicDependency",
    "DependencyNotFound",
    "InvalidProvider",
    "SpritzeError",
]
