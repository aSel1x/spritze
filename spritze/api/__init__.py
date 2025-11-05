"""Public API for dependency injection."""

from spritze.api.decorators import provider
from spritze.api.injection import get_context, init, inject

__all__ = ["provider", "inject", "init", "get_context"]
