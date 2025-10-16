import pytest

from spritze import provider
from spritze.infrastructure.exceptions import (
    CyclicDependency,
    DependencyNotFound,
    InvalidProvider,
)
from spritze.repositories.container_repository import Container


class A:
    pass


class B:
    pass


def test_missing_provider():
    class Empty(Container):
        pass

    c = Empty()
    with pytest.raises(DependencyNotFound):
        _ = c.resolve(str)


def test_provider_exception():
    class Bad(Container):
        @provider()
        def fail(self) -> int:
            raise ValueError("fail")

    c = Bad()
    with pytest.raises(ValueError):
        _ = c.resolve(int)


def test_cyclic_dependency():
    class Cyclic(Container):
        @provider()
        def a(self, b: B) -> A:
            assert isinstance(b, B)
            return A()

        @provider()
        def b(self, a: A) -> B:
            assert isinstance(a, A)
            return B()

    c = Cyclic()

    with pytest.raises(CyclicDependency):
        _ = c.resolve(A)


def test_provider_missing_return_annotation():
    class MissingAnnotationContainer(Container):
        @provider()
        def no_return_type(self):
            return 1

    with pytest.raises(InvalidProvider):
        _ = MissingAnnotationContainer()
