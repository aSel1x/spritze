"""Advanced tests for declarative providers."""

from collections.abc import AsyncGenerator, Generator

import pytest

from spritze import Container, Scope, aresolve, init, provider, resolve


class Resource:
    def __init__(self) -> None:
        self.id: int = id(self)
        self.closed: bool = False

    def close(self) -> None:
        self.closed = True


class AsyncResource:
    def __init__(self) -> None:
        self.id: int = id(self)
        self.closed: bool = False

    async def aclose(self) -> None:
        self.closed = True


class ServiceA:
    def __init__(self) -> None:
        self.value: str = "service_a"


class ServiceB:
    def __init__(self, service_a: ServiceA) -> None:
        self.service_a: ServiceA = service_a
        self.value: str = "service_b"


# Factory functions
def create_resource() -> Generator[Resource, None, None]:
    """Create resource with cleanup."""
    res = Resource()
    try:
        yield res
    finally:
        res.close()


async def create_async_resource() -> AsyncGenerator[AsyncResource, None]:
    """Create async resource with cleanup."""
    res = AsyncResource()
    try:
        yield res
    finally:
        await res.aclose()


def service_a_factory() -> ServiceA:
    """Factory for ServiceA."""
    return ServiceA()


class TestDeclarativeAdvanced:
    def test_declarative_generator_provider(self) -> None:
        """Test declarative provider with generator context manager."""

        class TestContainer(Container):
            resource: object = provider(create_resource, scope=Scope.REQUEST)

        init(TestContainer)

        resource1 = resolve(Resource)
        assert isinstance(resource1, Resource)
        assert not resource1.closed

        # Same request context - should be same instance
        resource2 = resolve(Resource)
        assert resource1 is resource2

    @pytest.mark.asyncio
    async def test_declarative_async_generator_provider(self) -> None:
        """Test declarative provider with async generator context manager."""

        class TestContainer(Container):
            async_resource: object = provider(
                create_async_resource, scope=Scope.REQUEST
            )

        init(TestContainer)

        resource1 = await aresolve(AsyncResource)
        assert isinstance(resource1, AsyncResource)
        assert not resource1.closed

        # Same request context - should be same instance
        resource2 = await aresolve(AsyncResource)
        assert resource1 is resource2

    def test_declarative_with_complex_dependencies(self) -> None:
        """Test declarative providers with dependency chains."""

        class TestContainer(Container):
            # Chain of declarative providers
            service_a: object = provider(service_a_factory, scope=Scope.APP)
            service_b: object = provider(ServiceB, scope=Scope.REQUEST)

        init(TestContainer)

        # Resolve the dependent service
        service_b = resolve(ServiceB)
        assert isinstance(service_b, ServiceB)
        assert isinstance(service_b.service_a, ServiceA)
        assert service_b.value == "service_b"
        assert service_b.service_a.value == "service_a"

        # ServiceA should be singleton (APP scope)
        service_a_direct = resolve(ServiceA)
        assert service_b.service_a is service_a_direct

    def test_multiple_scopes_declarative(self) -> None:
        """Test declarative providers with different scopes."""

        class SingletonService:
            def __init__(self) -> None:
                self.id: int = id(self)

        class RequestService:
            def __init__(self) -> None:
                self.id: int = id(self)

        class TransientService:
            def __init__(self) -> None:
                self.id: int = id(self)

        class TestContainer(Container):
            singleton: object = provider(SingletonService, scope=Scope.APP)
            request_svc: object = provider(RequestService, scope=Scope.REQUEST)
            transient: object = provider(TransientService, scope=Scope.TRANSIENT)

        init(TestContainer)

        # APP scope - singleton
        s1 = resolve(SingletonService)
        s2 = resolve(SingletonService)
        assert s1 is s2

        # REQUEST scope - same in request context
        r1 = resolve(RequestService)
        r2 = resolve(RequestService)
        assert r1 is r2

        # TRANSIENT scope - always new
        t1 = resolve(TransientService)
        t2 = resolve(TransientService)
        assert t1 is not t2

    def test_declarative_function_with_dependencies(self) -> None:
        """Test declarative function provider with dependencies."""

        def create_service_b(service_a: ServiceA) -> ServiceB:
            return ServiceB(service_a)

        class TestContainer(Container):
            service_a: object = provider(ServiceA, scope=Scope.APP)
            service_b: object = provider(create_service_b, scope=Scope.REQUEST)

        init(TestContainer)

        service_b = resolve(ServiceB)
        assert isinstance(service_b, ServiceB)
        assert isinstance(service_b.service_a, ServiceA)

    @pytest.mark.asyncio
    async def test_declarative_async_with_dependencies(self) -> None:
        """Test declarative async provider with dependencies."""

        async def create_async_service_b(service_a: ServiceA) -> ServiceB:
            # Simulate some async work
            return ServiceB(service_a)

        class TestContainer(Container):
            service_a: object = provider(ServiceA, scope=Scope.APP)
            service_b_async: object = provider(
                create_async_service_b, scope=Scope.REQUEST
            )

        init(TestContainer)

        service_b = await aresolve(ServiceB)
        assert isinstance(service_b, ServiceB)
        assert isinstance(service_b.service_a, ServiceA)

    def test_mixed_method_and_declarative(self) -> None:
        """Test mixing method and declarative providers."""

        class TestContainer(Container):
            # Method provider
            @provider(scope=Scope.APP)
            def service_a_method(self) -> ServiceA:
                svc = ServiceA()
                svc.value = "from_method"
                return svc

            # Declarative provider
            service_b: object = provider(ServiceB, scope=Scope.REQUEST)

        init(TestContainer)

        service_a = resolve(ServiceA)
        service_b = resolve(ServiceB)

        assert service_a.value == "from_method"
        assert service_b.service_a is service_a
