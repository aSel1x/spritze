"""Tests for Container class and dependency resolution."""

import pytest

from spritze import Container, Scope, init, provider, resolve
from spritze.exceptions import (
    CyclicDependency,
    NoProviderFound,
)


class SimpleService:
    def __init__(self) -> None:
        self.value: str = "simple"


class DependentService:
    def __init__(self, simple: SimpleService) -> None:
        self.simple: SimpleService = simple


class AsyncService:
    async def __init__(self) -> None:
        self.value: str = "async"

    @classmethod
    async def create(cls) -> "AsyncService":
        instance = cls.__new__(cls)
        instance.value = "async"
        return instance


class TestContainer:
    def test_basic_resolution(self) -> None:
        """Test basic dependency resolution."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def simple_service(self) -> SimpleService:
                return SimpleService()

            @provider(scope=Scope.APP)
            def dependent_service(self, simple: SimpleService) -> DependentService:
                return DependentService(simple)

        init(TestContainer)

        service = resolve(SimpleService)
        assert isinstance(service, SimpleService)
        assert service.value == "simple"

        dependent = resolve(DependentService)
        assert isinstance(dependent, DependentService)
        assert dependent.simple is service

    def test_singleton_scope(self) -> None:
        """Test that APP scope creates singletons."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def simple_service(self) -> SimpleService:
                return SimpleService()

        init(TestContainer)

        service1 = resolve(SimpleService)
        service2 = resolve(SimpleService)

        assert service1 is service2

    def test_request_scope(self) -> None:
        """Test that REQUEST scope creates new instances per request."""

        class TestContainer(Container):
            @provider(scope=Scope.REQUEST)
            def simple_service(self) -> SimpleService:
                return SimpleService()

        init(TestContainer)

        service1 = resolve(SimpleService)
        service2 = resolve(SimpleService)

        # In the same request context, they should be the same
        assert service1 is service2

    def test_transient_scope(self) -> None:
        """Test that TRANSIENT scope creates new instances each time."""

        class TestContainer(Container):
            @provider(scope=Scope.TRANSIENT)
            def simple_service(self) -> SimpleService:
                return SimpleService()

        init(TestContainer)

        service1 = resolve(SimpleService)
        service2 = resolve(SimpleService)

        # Transient should create new instances
        assert service1 is not service2

    def test_no_provider_found(self) -> None:
        """Test that missing provider raises NoProviderFound."""

        class TestContainer(Container):
            pass

        init(TestContainer)

        with pytest.raises(NoProviderFound):
            _ = resolve(SimpleService)

    def test_cyclic_dependency(self) -> None:
        """Test that cyclic dependencies are detected."""

        class ServiceA:
            def __init__(self, b: "ServiceB") -> None:
                self.b: ServiceB = b

        class ServiceB:
            def __init__(self, a: ServiceA) -> None:
                self.a: ServiceA = a

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def service_a(self, b: ServiceB) -> ServiceA:
                return ServiceA(b)

            @provider(scope=Scope.APP)
            def service_b(self, a: ServiceA) -> ServiceB:
                return ServiceB(a)

        init(TestContainer)

        with pytest.raises(CyclicDependency) as exc_info:
            _ = resolve(ServiceA)

        assert ServiceA in exc_info.value.stack
        assert ServiceB in exc_info.value.stack

    def test_provider_with_provide_as(self) -> None:
        """Test provider with explicit provide_as parameter."""

        class Interface:
            pass

        class Implementation(Interface):
            def __init__(self) -> None:
                self.value: str = "impl"

        class TestContainer(Container):
            impl: object = provider(Implementation, provide_as=Interface)

        init(TestContainer)

        instance = resolve(Interface)
        assert isinstance(instance, Implementation)
        assert instance.value == "impl"

    def test_multiple_containers(self) -> None:
        """Test merging multiple containers."""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ContainerA(Container):
            @provider(scope=Scope.APP)
            def service_a(self) -> ServiceA:
                return ServiceA()

        class ContainerB(Container):
            @provider(scope=Scope.APP)
            def service_b(self) -> ServiceB:
                return ServiceB()

        init(ContainerA, ContainerB)

        assert resolve(ServiceA) is not None
        assert resolve(ServiceB) is not None
