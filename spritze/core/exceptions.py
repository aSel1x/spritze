class SpritzeException(Exception):
    """Base exception for the Spritze framework."""

    pass


class DependencyNotFoundError(SpritzeException):
    """Raised when a dependency cannot be found."""

    def __init__(self, dependency_type: type) -> None:
        self.dependency_type: type = dependency_type
        super().__init__(f"Dependency of type '{dependency_type.__name__}' not found.")


class InvalidProviderError(SpritzeException):
    """Raised when a provider is defined incorrectly."""

    pass


__all__ = ["SpritzeException", "DependencyNotFoundError", "InvalidProviderError"]
