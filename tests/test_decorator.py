from spritze import Container, Scope, provider


def test_provider_decorator():
    class D(Container):
        @provider(scope=Scope.APP)
        def foo(self) -> int:
            return 1

    c = D()
    assert c.resolve(int) == 1
