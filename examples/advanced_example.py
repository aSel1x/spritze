"""Advanced example demonstrating all Spritze features."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from typing import Annotated

from spritze import (
    Container,
    ContextField,
    Depends,
    Scope,
    get_context,
    init,
    inject,
    provider,
)


# Domain entities
class DatabaseConfig:
    def __init__(self, url: str, pool_size: int = 10) -> None:
        self.url: str = url
        self.pool_size: int = pool_size


class CacheConfig:
    def __init__(self, redis_url: str, ttl: int = 3600) -> None:
        self.redis_url: str = redis_url
        self.ttl: int = ttl


class DatabaseConnection:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config: DatabaseConfig = config
        self._connected: bool = False
        print(f"Database connection created for {config.url}")

    def connect(self) -> None:
        self._connected = True
        print("Database connected")

    def disconnect(self) -> None:
        self._connected = False
        print("Database disconnected")

    def query(self, sql: str) -> str:
        if not self._connected:
            raise RuntimeError("Database not connected")
        return f"Query result: {sql}"


class CacheConnection:
    def __init__(self, config: CacheConfig) -> None:
        self.config: CacheConfig = config
        print(f"Cache connection created for {config.redis_url}")

    def get(self, key: str) -> str | None:
        return f"cached_value_for_{key}"

    def set(self, key: str, value: str) -> None:
        print(f"Cache set: {key} = {value}")


class UserRepository:
    def __init__(self, db: DatabaseConnection) -> None:
        self.db: DatabaseConnection = db

    def get_user(self, user_id: int) -> dict[str, object]:
        result = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": f"User {user_id}", "data": result}


class UserCache:
    def __init__(self, cache: CacheConnection) -> None:
        self.cache: CacheConnection = cache

    def get_user(self, user_id: int) -> dict[str, object] | None:
        cached = self.cache.get(f"user:{user_id}")
        if cached:
            return {"id": user_id, "name": f"Cached User {user_id}", "data": cached}
        return None

    def set_user(self, user_id: int, user_data: dict[str, object]) -> None:
        self.cache.set(f"user:{user_id}", str(user_data))


class UserService:
    def __init__(self, repo: UserRepository, cache: UserCache) -> None:
        self.repo: UserRepository = repo
        self.cache: UserCache = cache

    def get_user(self, user_id: int) -> dict[str, object]:
        # Try cache first
        cached = self.cache.get_user(user_id)
        if cached:
            return cached

        # Fallback to database
        user_data = self.repo.get_user(user_id)
        self.cache.set_user(user_id, user_data)
        return user_data


# Async domain entities
class AsyncDatabaseConnection:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config: DatabaseConfig = config
        self._connected: bool = False

    async def connect(self) -> None:
        await asyncio.sleep(0.1)  # Simulate async connection
        self._connected = True
        print("Async database connected")

    async def disconnect(self) -> None:
        await asyncio.sleep(0.1)  # Simulate async disconnection
        self._connected = False
        print("Async database disconnected")

    async def query(self, sql: str) -> str:
        if not self._connected:
            raise RuntimeError("Database not connected")
        await asyncio.sleep(0.1)  # Simulate async query
        return f"Async query result: {sql}"


class AsyncUserService:
    def __init__(self, db: AsyncDatabaseConnection) -> None:
        self.db: AsyncDatabaseConnection = db

    async def get_user(self, user_id: int) -> dict[str, object]:
        result = await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return {"id": user_id, "name": f"Async User {user_id}", "data": result}


# Container with all features
class AdvancedContainer(Container):
    # Context fields
    request_id: ContextField[str] = ContextField(str)

    @provider(scope=Scope.APP)
    def provide_db_config(self) -> DatabaseConfig:
        return DatabaseConfig("postgresql://localhost/prod_db", pool_size=20)

    @provider(scope=Scope.APP)
    def provide_cache_config(self) -> CacheConfig:
        return CacheConfig("redis://localhost:6379", ttl=1800)

    @provider(scope=Scope.REQUEST)
    def provide_db_connection(
        self, config: DatabaseConfig
    ) -> Generator[DatabaseConnection, None, None]:
        conn = DatabaseConnection(config)
        conn.connect()
        try:
            yield conn
        finally:
            conn.disconnect()

    @provider(scope=Scope.REQUEST)
    def provide_cache_connection(self, config: CacheConfig) -> CacheConnection:
        return CacheConnection(config)

    @provider(scope=Scope.REQUEST)
    def provide_user_repository(self, db: DatabaseConnection) -> UserRepository:
        return UserRepository(db)

    @provider(scope=Scope.REQUEST)
    def provide_user_cache(self, cache: CacheConnection) -> UserCache:
        return UserCache(cache)

    @provider(scope=Scope.REQUEST)
    def provide_user_service(
        self, repo: UserRepository, cache: UserCache
    ) -> UserService:
        return UserService(repo, cache)

    # Async providers
    @provider(scope=Scope.REQUEST)
    async def provide_async_db_connection(
        self, config: DatabaseConfig
    ) -> AsyncGenerator[AsyncDatabaseConnection, None]:
        conn = AsyncDatabaseConnection(config)
        await conn.connect()
        try:
            yield conn
        finally:
            await conn.disconnect()

    @provider(scope=Scope.REQUEST)
    async def provide_async_user_service(
        self, db: AsyncDatabaseConnection
    ) -> AsyncUserService:
        return AsyncUserService(db)

    # Declarative providers (default REQUEST scope)
    user_repository_transient: object = provider(UserRepository)
    user_cache_transient: object = provider(UserCache)


# Initialize container
container = AdvancedContainer()
init(container)


# Sync handlers
@inject
def get_user_sync(
    user_id: int,
    service: Annotated[UserService, Depends()],
    request_id: Annotated[str, Depends()],
) -> dict[str, object]:
    print(f"Processing request {request_id}")
    return service.get_user(user_id)


@inject
def get_user_with_transient(
    user_id: int,
    repo: Annotated[UserRepository, Depends()],
    cache: Annotated[UserCache, Depends()],
) -> dict[str, object]:
    # Using transient dependencies directly
    cached = cache.get_user(user_id)
    if cached:
        return cached
    return repo.get_user(user_id)


# Async handlers
@inject
async def get_user_async(
    user_id: int,
    service: Annotated[AsyncUserService, Depends()],
) -> dict[str, object]:
    return await service.get_user(user_id)


# Context manager example
@contextmanager
def request_context(request_id: str):
    """Context manager for request-scoped operations."""
    print(f"Starting request {request_id}")
    try:
        yield
    finally:
        print(f"Finishing request {request_id}")


async def main():
    """Demonstrate all features."""
    print("Spritze Advanced Example\n")

    # Set context
    ctx = get_context()
    ctx.set(request_id="req-123")

    print("1. Sync dependency injection with context managers:")
    result1 = get_user_sync(42)
    print(f"Result: {result1}\n")

    print("2. Transient dependency injection:")
    result2 = get_user_with_transient(42)
    print(f"Result: {result2}\n")

    print("3. Async dependency injection:")
    result3 = await get_user_async(42)
    print(f"Result: {result3}\n")

    print("4. Multiple requests (demonstrating scoping):")
    for i in range(3):
        ctx.set(request_id=f"req-{i}")
        result = get_user_sync(100 + i)
        print(f"Request {i}: {result}")

    print("\nExample completed")


if __name__ == "__main__":
    asyncio.run(main())
