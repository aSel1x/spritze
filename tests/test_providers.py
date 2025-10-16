from collections.abc import AsyncGenerator, Generator

import pytest

from spritze import Container, Depends, init, inject, provider


def test_sync_generator_provider():
    class Gen(Container):
        @provider()
        def res(self) -> Generator[str, None, None]:
            yield "ok"

    c = Gen()
    init(c)

    @inject
    def handler(res: Depends[str]):
        return res

    assert handler() == "ok"


@pytest.mark.asyncio
async def test_async_generator_provider():
    class Gen(Container):
        @provider()
        async def res(self) -> AsyncGenerator[str, None]:
            yield "async_ok"

    c = Gen()
    init(c)

    @inject
    async def handler(res: Depends[str]):
        return res

    assert await handler() == "async_ok"
