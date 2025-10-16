import pytest

from spritze import Container, Depends, Scope, init, inject, provider


class ServiceA:
    pass


class ServiceB:
    def __init__(self, a: ServiceA):
        self.a: ServiceA = a


class TestContainer(Container):
    __test__: bool = False

    def __init__(self):
        self.a_call_count: int = 0
        super().__init__()

    @provider(scope=Scope.APP)
    def a(self) -> ServiceA:
        self.a_call_count += 1
        return ServiceA()

    @provider(scope=Scope.REQUEST)
    def b(self, a: ServiceA) -> ServiceB:
        return ServiceB(a=a)


@pytest.mark.asyncio
async def test_scopes_and_injection():
    container = TestContainer()
    init(container)

    @inject
    async def transaction_1(b1: Depends[ServiceB], a1: Depends[ServiceA]):
        assert isinstance(b1, ServiceB)
        assert isinstance(b1.a, ServiceA)
        assert b1.a is a1
        return a1, b1

    a1, b1 = await transaction_1()
    assert container.a_call_count == 1

    @inject
    async def transaction_2(b2: Depends[ServiceB], a2: Depends[ServiceA]):
        assert isinstance(b2, ServiceB)
        assert isinstance(b2.a, ServiceA)
        assert b2.a is a2
        return a2, b2

    a2, b2 = await transaction_2()
    assert container.a_call_count == 1
    assert a1 is a2
    assert b1 is not b2
    assert b1.a is b2.a


def test_reuse_container():
    c = TestContainer()
    init(c)

    @inject
    def handler(a: Depends[ServiceA]):
        return a

    a1 = handler()
    a2 = handler()
    assert a1 is a2
