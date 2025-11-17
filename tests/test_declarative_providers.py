"""Tests for declarative provider style."""

from typing import override

from spritze import Container, Scope, init, provider, resolve


# Test services
class SimpleService:
    def __init__(self) -> None:
        self.value: str = "simple"


class ConfigurableService:
    def __init__(self, config: str) -> None:
        self.config: str = config


class DependentService:
    def __init__(self, simple: SimpleService) -> None:
        self.simple: SimpleService = simple
        self.value: str = "dependent"


# Interfaces
class ServiceInterface:
    def get_value(self) -> str:
        return "interface"


class ServiceImplementation(ServiceInterface):
    def __init__(self) -> None:
        self.impl_value: str = "implementation"

    @override
    def get_value(self) -> str:
        return self.impl_value


# Factory functions
def create_configurable(config_value: str = "default") -> ConfigurableService:
    return ConfigurableService(config_value)


def create_implementation() -> ServiceImplementation:
    return ServiceImplementation()


class TestDeclarativeProviders:
    def test_declarative_class_provider(self) -> None:
        """Test declarative provider for class."""

        class TestContainer(Container):
            simple: object = provider(SimpleService, scope=Scope.APP)

        init(TestContainer)

        service = resolve(SimpleService)
        assert isinstance(service, SimpleService)
        assert service.value == "simple"

        # Should be singleton
        service2 = resolve(SimpleService)
        assert service is service2

    def test_declarative_class_provider_with_provide_as(self) -> None:
        """Test declarative provider with provide_as."""

        class TestContainer(Container):
            service: object = provider(
                ServiceImplementation, provide_as=ServiceInterface, scope=Scope.APP
            )

        init(TestContainer)

        # Resolve by interface
        service = resolve(ServiceInterface)
        assert isinstance(service, ServiceImplementation)
        assert service.get_value() == "implementation"

    def test_declarative_function_provider(self) -> None:
        """Test declarative provider for function."""

        class TestContainer(Container):
            configurable: object = provider(create_configurable, scope=Scope.REQUEST)

        init(TestContainer)

        service = resolve(ConfigurableService)
        assert isinstance(service, ConfigurableService)
        assert service.config == "default"

    def test_declarative_function_provider_with_provide_as(self) -> None:
        """Test declarative function provider with provide_as."""

        class TestContainer(Container):
            impl: object = provider(
                create_implementation, provide_as=ServiceInterface, scope=Scope.APP
            )

        init(TestContainer)

        service = resolve(ServiceInterface)
        assert isinstance(service, ServiceImplementation)
        assert service.get_value() == "implementation"

    def test_declarative_with_dependencies(self) -> None:
        """Test declarative provider with dependencies."""

        class TestContainer(Container):
            simple: object = provider(SimpleService, scope=Scope.APP)
            dependent: object = provider(DependentService, scope=Scope.REQUEST)

        init(TestContainer)

        dependent = resolve(DependentService)
        assert isinstance(dependent, DependentService)
        assert isinstance(dependent.simple, SimpleService)
        assert dependent.value == "dependent"

    def test_mixed_declarative_and_method_providers(self) -> None:
        """Test mixing declarative and method providers."""

        class TestContainer(Container):
            # Declarative
            simple: object = provider(SimpleService, scope=Scope.APP)

            # Method
            @provider(scope=Scope.REQUEST)
            def configurable(self) -> ConfigurableService:
                return ConfigurableService("from_method")

        init(TestContainer)

        simple = resolve(SimpleService)
        configurable = resolve(ConfigurableService)

        assert isinstance(simple, SimpleService)
        assert isinstance(configurable, ConfigurableService)
        assert configurable.config == "from_method"

    def test_declarative_transient_scope(self) -> None:
        """Test declarative provider with transient scope."""

        class TestContainer(Container):
            transient: object = provider(SimpleService, scope=Scope.TRANSIENT)

        init(TestContainer)

        service1 = resolve(SimpleService)
        service2 = resolve(SimpleService)

        # Transient should create new instances each time
        assert service1 is not service2
        assert isinstance(service1, SimpleService)
        assert isinstance(service2, SimpleService)

    def test_multiple_declarative_providers_same_scope(self) -> None:
        """Test multiple declarative providers in same scope."""

        class Service1:
            def __init__(self) -> None:
                self.name: str = "service1"

        class Service2:
            def __init__(self) -> None:
                self.name: str = "service2"

        class Service3:
            def __init__(self, s1: Service1, s2: Service2) -> None:
                self.s1: Service1 = s1
                self.s2: Service2 = s2

        class TestContainer(Container):
            svc1: object = provider(Service1, scope=Scope.APP)
            svc2: object = provider(Service2, scope=Scope.APP)
            svc3: object = provider(Service3, scope=Scope.REQUEST)

        init(TestContainer)

        service3 = resolve(Service3)
        assert isinstance(service3, Service3)
        assert service3.s1.name == "service1"
        assert service3.s2.name == "service2"

        # APP scoped services should be same instances
        service1_direct = resolve(Service1)
        service2_direct = resolve(Service2)
        assert service3.s1 is service1_direct
        assert service3.s2 is service2_direct
