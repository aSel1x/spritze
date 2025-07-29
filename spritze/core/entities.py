from enum import Enum, auto


class Scope(Enum):
    """
    Defines the lifecycle scope of a dependency.
    """

    APP = auto()
    """Singleton instance across the entire application lifecycle."""

    REQUEST = auto()
    """New instance created for each request (e.g., an HTTP request)."""


class _Depends:
    def __init__(self, dependency_type: type):
        self.dependency_type: type = dependency_type

    def __repr__(self) -> str:
        return f"Depends({self.dependency_type.__name__})"


class _DependsFactory:
    def __getitem__(self, item: type) -> _Depends:
        return _Depends(item)


Depends = _DependsFactory()
"""
A marker for dependency injection.

Use it in function signatures to indicate that a dependency should be injected.

Example:
    @inject
    def my_handler(service: Depends[MyService]):
        ...
"""

__all__ = ["Scope", "Depends"]
