import pytest

from spritze.core.container import Container
from spritze.core.exceptions import DependencyNotFoundError, InvalidProviderError
from spritze.decorators import provide


class A:
    pass


class B:
    pass


def test_missing_provider():
    class Empty(Container):
        pass

    c = Empty()
    with pytest.raises(DependencyNotFoundError):
        c.resolve_sync(str)


def test_provider_exception():
    class Bad(Container):
        @provide()
        def fail(self) -> int:
            raise ValueError("fail")

    c = Bad()
    with pytest.raises(ValueError):
        c.resolve_sync(int)


def test_cyclic_dependency():
    class Cyclic(Container):
        @provide()
        def a(self, b: B) -> A:
            return A()

        @provide()
        def b(self, a: A) -> B:
            return B()

    c = Cyclic()
    with pytest.raises(RecursionError):
        c.resolve_sync(A)


def test_provider_missing_return_annotation():
    class MissingAnnotationContainer(Container):
        @provide()
        def provide_no_return_type(self):
            return 1

    with pytest.raises(InvalidProviderError):
        MissingAnnotationContainer()
