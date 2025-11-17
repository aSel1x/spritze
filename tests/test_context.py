from dataclasses import dataclass
from typing import Annotated

import pytest

from spritze import Container, Depends, init, inject
from spritze.exceptions import NoProviderFound


@dataclass
class ConfigFixture:
    value: str | None = "default_value"

    def set_value(self, new_value: str) -> None:
        self.value = new_value


class ContainerFixture(Container):
    pass


def test_default_context_value():
    init(ContainerFixture, context={ConfigFixture: ConfigFixture()})

    @inject
    def handler(
        v: Annotated[ConfigFixture, Depends()],
    ) -> ConfigFixture:
        return v

    v = handler()
    assert v.value == "default_value"


def test_custom_context_value():
    init(ContainerFixture, context={ConfigFixture: ConfigFixture(value="custom_value")})

    @inject
    def handler(v: Annotated[ConfigFixture, Depends()]) -> ConfigFixture:
        return v

    v = handler()
    assert v.value == "custom_value"


def test_missing_context_value_raises_lookup_error():
    init(ContainerFixture)

    @inject
    def handler(v: Annotated[ConfigFixture, Depends()]) -> ConfigFixture:
        return v

    with pytest.raises(NoProviderFound):
        _ = handler()


def test_context_value_modification():
    init(ContainerFixture, context={ConfigFixture: ConfigFixture()})

    @inject
    def handler(v: Annotated[ConfigFixture, Depends()]) -> ConfigFixture:
        return v

    v = handler()

    assert v.value == "default_value"

    v.set_value("modified_value")

    del v

    @inject
    def handler2(v: Annotated[ConfigFixture, Depends()]) -> ConfigFixture:
        return v

    v2 = handler2()

    assert v2.value == "modified_value"
