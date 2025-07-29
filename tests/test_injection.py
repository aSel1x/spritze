from spritze.core.container import Container
from spritze.core.entities import Depends, Scope
from spritze.decorators import provide


class ServiceA:
    pass


class ServiceB:
    def __init__(self, a: ServiceA):
        self.a = a


class ServiceC:
    def __init__(self, b: ServiceB):
        self.b = b


def test_sync_injection():
    class SyncContainer(Container):
        @provide(scope=Scope.APP)
        def provide_x(self) -> int:
            return 42

        @provide(scope=Scope.REQUEST)
        def provide_y(self, x: int) -> str:
            return f"Y{x}"

    c = SyncContainer()
    inject = c.injector()

    @inject
    def handler(y: Depends[str], x: Depends[int]):
        return y, x

    y, x = handler()
    assert y == "Y42"
    assert x == 42


def test_deep_dependency():
    class TestContainer(Container):
        __test__ = False

        @provide(scope=Scope.APP)
        def provide_a(self) -> ServiceA:
            return ServiceA()

        @provide(scope=Scope.REQUEST)
        def provide_b(self, a: ServiceA) -> ServiceB:
            return ServiceB(a=a)

        @provide(scope=Scope.REQUEST)
        def provide_c(self, b: ServiceB) -> ServiceC:
            return ServiceC(b=b)

    c = TestContainer()
    inject = c.injector()

    @inject
    def handler(c: Depends[ServiceC]):
        return c

    result = handler()
    assert isinstance(result, ServiceC)
    assert isinstance(result.b, ServiceB)
    assert isinstance(result.b.a, ServiceA)
