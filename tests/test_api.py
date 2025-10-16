from typing import Annotated

import pytest

from spritze import Container, Depends, init, inject, singleton, transient
from spritze.infrastructure.context import ContextField, context
from spritze.infrastructure.exceptions import InvalidProvider


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
    config: ContextField[Config] = context.get(Config)

    @singleton
    async def db_engine(self, config: Config) -> EngineProtocol:
        return AsyncEngine(config.db_dsn)

    async_session: object = transient(AsyncSession)


@pytest.mark.asyncio
async def test_integration_async():
    container = AppContainer()
    container.context.update(Config=Config(db_dsn="memory"))

    init(container)

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
    container.context.update(Config=Config())

    init(container)

    @inject
    def f(e: Annotated[EngineProtocol, Depends()]) -> None:
        assert isinstance(e, AsyncEngine)
        return None

    with pytest.raises(InvalidProvider):
        f()
