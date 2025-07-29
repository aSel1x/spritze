from spritze.core.container import Container
from spritze.core.entities import Scope
from spritze.decorators import provide


def test_provide_decorator():
    class D(Container):
        @provide(scope=Scope.APP)
        def foo(self) -> int:
            return 1

    c = D()
    assert c.resolve_sync(int) == 1
