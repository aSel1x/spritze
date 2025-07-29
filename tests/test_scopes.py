import pytest

from spritze.core.container import Container
from spritze.core.entities import Depends, Scope
from spritze.decorators import provide


class ServiceA:
    pass


class ServiceB:
    def __init__(self, a: ServiceA):
        self.a = a


class TestContainer(Container):
    __test__ = False

    def __init__(self):
        self.provide_a_call_count = 0
        super().__init__()

    @provide(scope=Scope.APP)
    def provide_a(self) -> ServiceA:
        self.provide_a_call_count += 1
        return ServiceA()

    @provide(scope=Scope.REQUEST)
    def provide_b(self, a: ServiceA) -> ServiceB:
        return ServiceB(a=a)


@pytest.mark.asyncio
async def test_scopes_and_injection():
    container = TestContainer()
    inject = container.injector()

    @inject
    async def transaction_1(b1: Depends[ServiceB], a1: Depends[ServiceA]):
        assert isinstance(b1, ServiceB)
        assert isinstance(b1.a, ServiceA)
        assert b1.a is a1
        return a1, b1

    a1, b1 = await transaction_1()
    assert container.provide_a_call_count == 1

    @inject
    async def transaction_2(b2: Depends[ServiceB], a2: Depends[ServiceA]):
        return a2, b2

    a2, b2 = await transaction_2()
    assert container.provide_a_call_count == 1
    assert a1 is a2
    assert b1 is not b2
    assert b1.a is b2.a


def test_reuse_container():
    c = TestContainer()
    inject = c.injector()

    @inject
    def handler(a: Depends[ServiceA]):
        return a

    a1 = handler()
    a2 = handler()
    assert a1 is a2
