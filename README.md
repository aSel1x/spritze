# spritze

[![CI](https://github.com/aSel1x/spritze/actions/workflows/ci.yml/badge.svg)](https://github.com/aSel1x/spritze/actions/workflows/ci.yml)
[![Code Quality](https://github.com/aSel1x/spritze/actions/workflows/quality.yml/badge.svg)](https://github.com/aSel1x/spritze/actions/workflows/quality.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/spritze.svg)](https://pypi.org/project/spritze/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A modern, type-safe Dependency Injection framework for Python with support for async/await and context managers.

## Features

- **Type Safety**: Full support for Python 3.11+ type hints with `Annotated` and `Depends`
- **Scopes**: APP (singleton) and REQUEST (per-request) scoping
- **Async Support**: Native async/await support for providers and injection
- **Context Managers**: Automatic lifecycle management with generators and async generators
- **Framework Agnostic**: Easy integration with Flask, FastAPI, Litestar, Django, and more
- **No Globals**: Explicit containers with per-request context management
- **Clean Architecture**: Follows Domain-Driven Design principles

## Installation

```bash
uv add spritze
# or
pip install spritze
```

## Quick Start

### Basic Usage

```python
from typing import Annotated
from spritze import Container, Scope, provider, Depends, init, inject


class DatabaseConfig:
    def __init__(self, url: str) -> None:
        self.url: str = url


class DatabaseConnection:
    def __init__(self, config: DatabaseConfig) -> None:
        self.config: DatabaseConfig = config
    
    def query(self, sql: str) -> str:
        return f"Executed: {sql} on {self.config.url}"


class UserService:
    def __init__(self, db: DatabaseConnection) -> None:
        self.db: DatabaseConnection = db
    
    def get_user(self, user_id: int) -> str:
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")


class AppContainer(Container):
    @provider(scope=Scope.APP)
    def config(self) -> DatabaseConfig:
        return DatabaseConfig("postgresql://localhost/db")
    
    @provider(scope=Scope.REQUEST)
    def database(self, config: DatabaseConfig) -> DatabaseConnection:
        return DatabaseConnection(config)
    
    @provider(scope=Scope.REQUEST)
    def user_service(self, db: DatabaseConnection) -> UserService:
        return UserService(db)


# Initialize container
container = AppContainer()
init(container)


@inject
def get_user_handler(
    user_id: int,
    service: Annotated[UserService, Depends()]
) -> str:
    return service.get_user(user_id)


if __name__ == "__main__":
    result = get_user_handler(123)
    print(result)  # -> Executed: SELECT * FROM users WHERE id = 123 on postgresql://localhost/db
```

### Async Providers

```python
import asyncio
from typing import Annotated
from spritze import Container, Scope, provider, Depends, init, inject


class AsyncDatabaseConnection:
    def __init__(self, url: str) -> None:
        self.url: str = url
    
    async def query(self, sql: str) -> str:
        await asyncio.sleep(0.1)  # Simulate async operation
        return f"Async executed: {sql} on {self.url}"


class AsyncUserService:
    def __init__(self, db: AsyncDatabaseConnection) -> None:
        self.db: AsyncDatabaseConnection = db
    
    async def get_user(self, user_id: int) -> str:
        return await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")


class AsyncContainer(Container):
    @provider(scope=Scope.APP)
    def db_url(self) -> str:
        return "postgresql://localhost/db"
    
    @provider(scope=Scope.REQUEST)
    async def database(self, url: str) -> AsyncDatabaseConnection:
        return AsyncDatabaseConnection(url)
    
    @provider(scope=Scope.REQUEST)
    async def user_service(self, db: AsyncDatabaseConnection) -> AsyncUserService:
        return AsyncUserService(db)


container = AsyncContainer()
init(container)


@inject
async def async_handler(
    user_id: int,
    service: Annotated[AsyncUserService, Depends()]
) -> str:
    return await service.get_user(user_id)


async def main() -> None:
    result = await async_handler(123)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### Context Managers

```python
from typing import Annotated, Generator
from spritze import Container, Scope, provider, Depends, init, inject


class DatabaseConnection:
    def __init__(self, url: str) -> None:
        self.url: str = url
        print(f"Connected to {url}")
    
    def close(self) -> None:
        print(f"Disconnected from {self.url}")


class AppContainer(Container):
    @provider(scope=Scope.REQUEST)
    def database(self) -> Generator[DatabaseConnection, None, None]:
        db = DatabaseConnection("postgresql://localhost/db")
        try:
            yield db
        finally:
            db.close()


container = AppContainer()
init(container)


@inject
def handler(db: Annotated[DatabaseConnection, Depends()]) -> str:
    return f"Using database: {db.url}"


# Database will be automatically closed after the request
result = handler()
```

## Advanced Features

### Multiple Containers

```python
from spritze import Container, init, inject, Scope, provider

class CoreContainer(Container):
    @provider(scope=Scope.APP)
    def config(self) -> str:
        return "core_config"

class FeatureContainer(Container):
    @provider(scope=Scope.REQUEST)
    def feature(self, config: str) -> str:
        return f"feature_with_{config}"

# Initialize multiple containers
init((CoreContainer(), FeatureContainer()))

@inject
def handler(feature: Annotated[str, Depends()]) -> str:
    return feature
```

### Context Values

```python
from spritze import Container, context, ContextField, Scope, provider

class RequestContext:
    def __init__(self, user_id: int) -> None:
        self.user_id: int = user_id

class AppContainer(Container):
    request: ContextField[RequestContext] = context.get(RequestContext)
    
    @provider(scope=Scope.REQUEST)
    def user_service(self, request: RequestContext) -> str:
        return f"User {request.user_id} service"

container = AppContainer()
container.context.update(RequestContext=RequestContext(user_id=123))
```

## Examples

See [examples/](examples/) for complete integrations:
- **Flask**: `examples/flask_example.py` - Web application with request scoping
- **Litestar**: `examples/litestar_example.py` - Modern async web framework
- **Django**: `examples/django_example.py` - Traditional web framework
- **Multi-Container**: `examples/multi_container_example.py` - Complex dependency graphs

## Architecture

Spritze follows Clean Architecture and Domain-Driven Design principles:

- **Domain Layer**: Core entities (`Provider`, `Transient`) and value objects (`Scope`, `ProviderType`)
- **Application Layer**: Decorators and global container management
- **Infrastructure Layer**: Context management and exception handling
- **Repository Layer**: Container implementation and dependency resolution

## License

Apache 2.0 — see [LICENSE](LICENSE)
