from collections.abc import AsyncGenerator
from functools import partial
from typing import Annotated, Generic, TypeVar

import pytest

from spritze import Container, Depends, Scope, aresolve, init, inject, provider, resolve

T = TypeVar("T")


class A(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value: T = value


class B(A[int]):
    pass


class C(A[str]):
    pass


def test_provide_generic():
    """Test providers with generic types."""

    def b_factory() -> A[int]:
        return B(100)

    class ContainerFixture(Container):
        b_provider: object = provider(b_factory, provide_as=A[int])

        c_str: object = provider(partial(C, "c"), provide_as=A[str])

    init(ContainerFixture)

    @inject
    def func_b(b: Annotated[A[int], Depends()]) -> None:
        assert b.value == 100

    func_b()

    b = resolve(A[int])
    assert b.value == 100

    @inject
    def func_c(c: Annotated[A[str], Depends()]) -> None:
        assert c.value == "c"

    func_c()

    c = resolve(A[str])
    assert c.value == "c"


@pytest.mark.asyncio
async def test_provide_generic_async():
    """Test async providers with generic types."""

    async def async_b_factory() -> A[int]:
        return B(200)

    async def async_c_factory() -> A[str]:
        return C("c")

    class ContainerFixture(Container):
        b_async: object = provider(async_b_factory, provide_as=A[int])
        c_str: object = provider(async_c_factory, provide_as=A[str])

    init(ContainerFixture)

    @inject
    async def func_b_async(b: Annotated[A[int], Depends()]) -> None:
        assert b.value == 200

    await func_b_async()

    b_async = await aresolve(A[int])
    assert b_async.value == 200

    @inject
    async def func_c_async(c: Annotated[A[str], Depends()]) -> None:
        assert c.value == "c"

    await func_c_async()

    c_async = await aresolve(A[str])
    assert c_async.value == "c"


class GenericFactory(Generic[T]):
    """Generic factory class similar to async_sessionmaker."""

    def __init__(self, value: T) -> None:
        self.value: T = value

    def create(self) -> T:
        return self.value


class Resource:
    def __init__(self, id: int) -> None:
        self.id: int = id


def test_generic_type_as_provider_parameter():
    """Test that generic types work as provider function parameters."""

    class TestContainer(Container):
        @provider(scope=Scope.APP)
        def factory(self) -> GenericFactory[int]:
            return GenericFactory[int](42)

        @provider(scope=Scope.REQUEST)
        def use_factory(self, factory: GenericFactory[int]) -> int:
            return factory.create()

    init(TestContainer)

    result = resolve(int)
    assert result == 42


@pytest.mark.asyncio
async def test_generic_type_with_context_manager():
    """Test generic types in context manager providers."""

    class TestContainer(Container):
        @provider(scope=Scope.APP)
        def factory(self) -> GenericFactory[Resource]:
            return GenericFactory[Resource](Resource(id=100))

        @provider(scope=Scope.REQUEST)
        async def resource(
            self, factory: GenericFactory[Resource]
        ) -> AsyncGenerator[Resource, None]:
            res = factory.create()
            try:
                yield res
            finally:
                pass  # cleanup if needed

    init(TestContainer)

    # Test that generic type parameter works in provider
    resource = await aresolve(Resource)
    assert resource.id == 100


def test_multiple_generic_parameters():
    """Test multiple generic type parameters."""

    class TestContainer(Container):
        @provider(scope=Scope.APP)
        def int_factory(self) -> GenericFactory[int]:
            return GenericFactory[int](10)

        @provider(scope=Scope.APP)
        def str_factory(self) -> GenericFactory[str]:
            return GenericFactory[str]("test")

        @provider(scope=Scope.REQUEST)
        def combine(
            self,
            int_factory: GenericFactory[int],
            str_factory: GenericFactory[str],
        ) -> str:
            return f"{int_factory.create()}-{str_factory.create()}"

    init(TestContainer)

    result = resolve(str)
    assert result == "10-test"


@pytest.mark.asyncio
async def test_async_generic_parameter():
    """Test async provider with generic type parameter."""

    class TestContainer(Container):
        @provider(scope=Scope.APP)
        async def factory(self) -> GenericFactory[int]:
            return GenericFactory[int](200)

        @provider(scope=Scope.REQUEST)
        async def use_factory(self, factory: GenericFactory[int]) -> int:
            return factory.create()

    init(TestContainer)

    result = await aresolve(int)
    assert result == 200
