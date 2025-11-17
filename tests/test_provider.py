"""Tests for provider decorator and factory."""

from spritze import Container, Scope, init, provider, resolve


class Service:
    def __init__(self) -> None:
        self.value: str = "service"


class Interface:
    pass


class Implementation(Interface):
    def __init__(self) -> None:
        self.value: str = "impl"


class TestProvider:
    def test_provider_decorator_method(self) -> None:
        """Test provider decorator on container method."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def service(self) -> Service:
                return Service()

        init(TestContainer)

        service = resolve(Service)
        assert isinstance(service, Service)
        assert service.value == "service"

    def test_provider_decorator_with_scope(self) -> None:
        """Test provider decorator with explicit scope."""

        class TestContainer(Container):
            @provider(scope=Scope.REQUEST)
            def service(self) -> Service:
                return Service()

        init(TestContainer)

        service1 = resolve(Service)
        service2 = resolve(Service)
        # Same request context
        assert service1 is service2

    def test_provider_factory_class(self) -> None:
        """Test provider factory with class."""

        class TestContainer(Container):
            service: object = provider(Service, scope=Scope.APP)

        init(TestContainer)

        service = resolve(Service)
        assert isinstance(service, Service)

    def test_provider_factory_class_with_provide_as(self) -> None:
        """Test provider factory with class and provide_as."""

        class TestContainer(Container):
            impl: object = provider(
                Implementation, provide_as=Interface, scope=Scope.APP
            )

        init(TestContainer)

        instance = resolve(Interface)
        assert isinstance(instance, Implementation)
        assert instance.value == "impl"

    def test_provider_factory_function(self) -> None:
        """Test provider factory with function."""

        def create_service() -> Service:
            return Service()

        class TestContainer(Container):
            service: object = provider(create_service, scope=Scope.APP)

        init(TestContainer)

        service = resolve(Service)
        assert isinstance(service, Service)

    def test_provider_factory_function_with_provide_as(self) -> None:
        """Test provider factory with function and provide_as."""

        def create_impl() -> Implementation:
            return Implementation()

        class TestContainer(Container):
            impl: object = provider(create_impl, provide_as=Interface, scope=Scope.APP)

        init(TestContainer)

        instance = resolve(Interface)
        assert isinstance(instance, Implementation)
