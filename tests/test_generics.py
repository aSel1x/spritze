"""Test generic type support in providers."""

from typing import Annotated, Generic, TypeVar

from spritze import Container, Depends, Scope, init, inject, provider, resolve

T = TypeVar("T")


class GenericService(Generic[T]):
    """Generic service for testing."""

    value: T

    def __init__(self, value: T) -> None:
        self.value = value


class StringService:
    """Non-generic service."""

    data: str

    def __init__(self) -> None:
        self.data = "string_data"


class MyContainer(Container):
    """Container with generic providers."""

    @provider(scope=Scope.APP)
    def string_data(self) -> StringService:
        return StringService()

    @provider(scope=Scope.APP)
    def generic_string(self) -> GenericService[str]:
        """Provider returning generic type with str parameter."""
        return GenericService("hello")

    @provider(scope=Scope.APP)
    def generic_int(self) -> GenericService[int]:
        """Provider returning generic type with int parameter."""
        return GenericService(42)


def test_generic_provider_direct_access() -> None:
    """Test that generic types work in provider return annotations."""
    container = MyContainer()

    string_svc = container.generic_string()
    assert isinstance(string_svc, GenericService)
    assert string_svc.value == "hello"

    int_svc = container.generic_int()
    assert isinstance(int_svc, GenericService)
    assert int_svc.value == 42


def test_generic_provider_with_resolve() -> None:
    """Test that generic types work with resolve()."""
    container = MyContainer()
    init(container)

    string_svc = resolve(GenericService[str])
    assert isinstance(string_svc, GenericService)
    assert string_svc.value == "hello"

    int_svc = resolve(GenericService[int])
    assert isinstance(int_svc, GenericService)
    assert int_svc.value == 42

    assert string_svc is not int_svc


def test_generic_provider_with_inject() -> None:
    """Test that generic types work with inject decorator."""
    container = MyContainer()
    init(container)

    @inject
    def use_generic(
        string_svc: Annotated[GenericService[str], Depends()],
        int_svc: Annotated[GenericService[int], Depends()],
    ) -> tuple[str, int]:
        return (string_svc.value, int_svc.value)

    result = use_generic()
    assert result == ("hello", 42)


def test_non_generic_still_works() -> None:
    """Ensure non-generic types still work correctly."""
    container = MyContainer()
    init(container)

    string_data = resolve(StringService)
    assert isinstance(string_data, StringService)
    assert string_data.data == "string_data"

    string_data2 = resolve(StringService)
    assert isinstance(string_data2, StringService)
    assert string_data2 is string_data
