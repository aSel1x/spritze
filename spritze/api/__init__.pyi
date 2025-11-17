"""Type stubs for spritze.api module."""

from spritze.api.core import aresolve, init, resolve
from spritze.api.injection import inject
from spritze.api.provider import provider

__all__ = (
    "init",
    "resolve",
    "aresolve",
    "inject",
    "provider",
)
