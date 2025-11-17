"""Edge case tests for declarative providers."""

from collections.abc import Generator
from typing import Protocol

from spritze import Container, Scope, init, provider, resolve


class ServiceProtocol(Protocol):
    """Service protocol."""

    def get_value(self) -> str: ...


class ConcreteService:
    """Concrete service implementation."""

    def __init__(self) -> None:
        self.data: str = "concrete"

    def get_value(self) -> str:
        return self.data


class ComplexService:
    """Service with multiple optional dependencies."""

    def __init__(self, required: ConcreteService, optional: str = "default") -> None:
        self.required: ConcreteService = required
        self.optional: str = optional

    def get_value(self) -> str:
        return f"{self.required.get_value()}_{self.optional}"


def service_factory() -> ConcreteService:
    """Simple service factory."""
    return ConcreteService()


def protocol_factory() -> ServiceProtocol:
    """Factory that returns protocol implementation."""
    service = ConcreteService()
    service.data = "from_factory"
    return service


class TestDeclarativeEdgeCases:
    def test_declarative_class_auto_interface_detection(self) -> None:
        """Test automatic interface detection for classes."""

        class TestContainer(Container):
            # Should auto-detect ServiceProtocol from ConcreteService
            concrete: object = provider(ConcreteService, scope=Scope.APP)

        init(TestContainer)

        service = resolve(ConcreteService)
        assert isinstance(service, ConcreteService)
        assert service.get_value() == "concrete"

    def test_declarative_function_with_complex_signature(self) -> None:
        """Test function with optional parameters."""

        class TestContainer(Container):
            concrete: object = provider(ConcreteService, scope=Scope.APP)
            complex_svc: object = provider(ComplexService, scope=Scope.REQUEST)

        init(TestContainer)

        service = resolve(ComplexService)
        assert isinstance(service, ComplexService)
        assert service.get_value() == "concrete_default"  # Uses default "default"

    def test_declarative_function_provider_with_protocol(self) -> None:
        """Test function that provides protocol."""

        class TestContainer(Container):
            service: object = provider(
                protocol_factory, provide_as=ServiceProtocol, scope=Scope.APP
            )

        init(TestContainer)

        service = resolve(ServiceProtocol)
        assert isinstance(service, ConcreteService)
        assert service.get_value() == "from_factory"

    def test_declarative_lambda_provider(self) -> None:
        """Test lambda as declarative provider."""

        class TestContainer(Container):
            simple: object = provider(
                lambda: ConcreteService(),
                provide_as=ServiceProtocol,
                scope=Scope.TRANSIENT,
            )

        init(TestContainer)

        service1 = resolve(ServiceProtocol)
        service2 = resolve(ServiceProtocol)

        # Transient scope - should be different instances
        assert service1 is not service2
        assert isinstance(service1, ConcreteService)
        assert isinstance(service2, ConcreteService)

    def test_declarative_multiple_providers_same_type(self) -> None:
        """Test that later provider overwrites earlier one."""

        def factory1() -> ConcreteService:
            service = ConcreteService()
            service.data = "factory1"
            return service

        def factory2() -> ConcreteService:
            service = ConcreteService()
            service.data = "factory2"
            return service

        class TestContainer(Container):
            # This should be overwritten
            service1: object = provider(factory1, scope=Scope.APP)
            # This should be the final one
            service2: object = provider(factory2, scope=Scope.APP)

        init(TestContainer)

        service = resolve(ConcreteService)
        # Should get the last registered provider
        assert service.get_value() == "factory2"

    def test_declarative_with_inheritance(self) -> None:
        """Test declarative providers with container inheritance."""

        class BaseService:
            def __init__(self) -> None:
                self.value: str = "base"

        class ExtendedService(BaseService):
            def __init__(self) -> None:
                super().__init__()
                self.value: str = "extended"

        class BaseContainer(Container):
            base: object = provider(BaseService, scope=Scope.APP)

        class ExtendedContainer(BaseContainer):
            extended: object = provider(ExtendedService, scope=Scope.APP)

        init(ExtendedContainer)

        base_service = resolve(BaseService)
        extended_service = resolve(ExtendedService)

        assert isinstance(base_service, BaseService)
        assert isinstance(extended_service, ExtendedService)
        assert base_service.value == "base"
        assert extended_service.value == "extended"

    def test_declarative_context_manager_with_dependency(self) -> None:
        """Test declarative context manager with dependencies."""

        def resource_factory(
            service: ConcreteService,
        ) -> Generator[ComplexService, None, None]:
            """Context manager factory with dependency."""
            complex_svc = ComplexService(service, "from_cm")
            try:
                yield complex_svc
            finally:
                # Cleanup logic here
                pass

        class TestContainer(Container):
            concrete: object = provider(ConcreteService, scope=Scope.APP)
            resource: object = provider(
                resource_factory, provide_as=ComplexService, scope=Scope.REQUEST
            )

        init(TestContainer)

        service = resolve(ComplexService)
        assert isinstance(service, ComplexService)
        assert service.get_value() == "concrete_from_cm"
