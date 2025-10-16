from spritze import Container, Depends, Scope, init, inject, provider


class ServiceA:
    pass


class ServiceB:
    def __init__(self, a: ServiceA):
        self.a: ServiceA = a


class ServiceC:
    def __init__(self, b: ServiceB):
        self.b: ServiceB = b


def test_sync_injection():
    class SyncContainer(Container):
        @provider(scope=Scope.APP)
        def x(self) -> int:
            return 42

        @provider(scope=Scope.REQUEST)
        def y(self, x: int) -> str:
            return f"Y{x}"

    c = SyncContainer()
    init(c)

    @inject
    def handler(y: Depends[str], x: Depends[int]):
        return y, x

    y, x = handler()
    assert y == "Y42"
    assert x == 42


def test_deep_dependency():
    class TestContainer(Container):
        __test__: bool = False

        @provider(scope=Scope.APP)
        def a(self) -> ServiceA:
            return ServiceA()

        @provider(scope=Scope.REQUEST)
        def b(self, a: ServiceA) -> ServiceB:
            return ServiceB(a=a)

        @provider(scope=Scope.REQUEST)
        def c(self, b: ServiceB) -> ServiceC:
            return ServiceC(b=b)

    c = TestContainer()
    init(c)

    @inject
    def handler(c: Depends[ServiceC]):
        return c

    result = handler()
    assert isinstance(result, ServiceC)
    assert isinstance(result.b, ServiceB)
    assert isinstance(result.b.a, ServiceA)
