__all__ = (
    "AsyncSyncMismatch",
    "CyclicDependency",
    "DependsTypeMissingOrInvalid",
    "NoProviderFound",
    "ContainerNotInitialized",
    "NoContainerProvided",
    "SpritzeError",
)


class SpritzeError(Exception):
    pass


class ContainerNotInitialized(SpritzeError):
    def __init__(self) -> None:
        super().__init__(
            "Container not initialized. "
            + "Ensure to initialize Spritze with at least one container."
        )


class NoContainerProvided(ValueError, SpritzeError):
    def __init__(self) -> None:
        super().__init__(
            "No container provided. "
            + "Ensure to initialize Spritze with at least one container."
        )


class DependencyNotFound(SpritzeError):
    dependency_type: type

    def __init__(self, dependency_type: type) -> None:
        super().__init__(
            f"Dependency '{dependency_type.__name__}' not found. "
            + "Ensure it's registered as a provider."
        )
        self.dependency_type = dependency_type


class InvalidProvider(TypeError, SpritzeError):
    def __init__(self, message: str) -> None:
        super().__init__(f"Invalid provider configuration: {message}")


class DependsTypeMissingOrInvalid(TypeError, SpritzeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class CyclicDependency(RuntimeError, SpritzeError):
    stack: tuple[type, ...]

    def __init__(self, stack: tuple[type, ...]) -> None:
        path = " -> ".join(t.__name__ for t in stack)
        super().__init__(f"Cyclic dependency: {path}")
        self.stack = stack


class AsyncSyncMismatch(RuntimeError, SpritzeError):
    def __init__(self, dependency_type: type, context: str) -> None:
        super().__init__(
            f"Cannot resolve async provider '{dependency_type.__name__}' "
            + f"in {context} context."
        )


class ContextValueNotFound(LookupError, SpritzeError):
    def __init__(self, context_key_type: type) -> None:
        super().__init__(f"Context value for '{context_key_type.__name__}' not found.")


class NoProviderFound(RuntimeError, SpritzeError):
    def __init__(self, dependency_type: type) -> None:
        super().__init__(f"No provider found for '{dependency_type.__name__}'.")
