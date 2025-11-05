from typing import Annotated

import pytest

from spritze import Container, Depends, Scope, init, inject, provider
from spritze.context import ContextField
from spritze.exceptions import InvalidProvider


class Config:
    def __init__(self, db_dsn: str = "sqlite+aiosqlite:///:memory:") -> None:
        self.db_dsn: str = db_dsn


class EngineProtocol:
    def __init__(self, dsn: str) -> None:
        self.dsn: str = dsn


class AsyncEngine(EngineProtocol):
    pass


class AsyncSession:
    def __init__(self, engine: EngineProtocol) -> None:
        self.engine: EngineProtocol = engine


class AppContainer(Container):
    config: ContextField[Config] = ContextField(Config)

    @provider(scope=Scope.APP)
    async def db_engine(self, config: Config) -> EngineProtocol:
        return AsyncEngine(config.db_dsn)

    async_session: object = provider(AsyncSession)


@pytest.mark.asyncio
async def test_integration_async():
    container = AppContainer()

    init(container, context={Config: Config(db_dsn="memory")})

    @inject
    async def handler(
        s: Annotated[AsyncSession, Depends()],
        e: Annotated[EngineProtocol, Depends()],
    ) -> tuple[str, str]:
        return s.engine.dsn, e.dsn

    dsn1, dsn2 = await handler()
    assert dsn1 == "memory"
    assert dsn2 == "memory"


def test_sync_inject_rejects_async_provider():
    container = AppContainer()

    init(container, context={Config: Config()})

    @inject
    def f(e: Annotated[EngineProtocol, Depends()]) -> None:
        assert isinstance(e, AsyncEngine)
        return None

    with pytest.raises(InvalidProvider):
        f()
