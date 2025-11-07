"""Tests for declarative function providers.

Tests cover:
- Basic sync function providers
- Function providers with dependencies
- Function providers with explicit 'provides' type
- Async function providers
- Mixed function and class providers
- Lambda function providers
"""

import pytest

from spritze import Container, Scope, aresolve, init, provider, resolve


class Database:
    def __init__(self, url: str) -> None:
        self.url: str = url
        self.connected: bool = True


class Repository:
    def __init__(self, db: Database) -> None:
        self.db: Database = db


class Service:
    def __init__(self, repo: Repository) -> None:
        self.repo: Repository = repo


def create_database() -> Database:
    return Database("sqlite:///:memory:")


def create_repository(db: Database) -> Repository:
    return Repository(db)


async def create_service_async(repo: Repository) -> Service:
    return Service(repo)


class TestBasicFunctionProviders:
    def test_simple_function_provider(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)

        init(AppContainer())
        db = resolve(Database)

        assert isinstance(db, Database)
        assert db.url == "sqlite:///:memory:"
        assert db.connected

    def test_function_provider_with_scope_app(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)

        init(AppContainer())
        db1 = resolve(Database)
        db2 = resolve(Database)

        assert db1 is db2

    def test_function_provider_with_scope_request(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.REQUEST)

        init(AppContainer())
        db1 = resolve(Database)
        db2 = resolve(Database)

        assert db1 is db2
        db1 = resolve(Database)
        db2 = resolve(Database)

        assert db1 is db2
        assert isinstance(db1, Database)
        assert isinstance(db2, Database)

    def test_lambda_function_provider(self) -> None:
        def create_db() -> Database:
            return Database("postgresql://localhost")

        class AppContainer(Container):
            db: object = provider(create_db, scope=Scope.APP)

        init(AppContainer())
        db = resolve(Database)

        assert isinstance(db, Database)
        assert db.url == "postgresql://localhost"


class TestFunctionProvidersWithDependencies:
    def test_function_provider_with_single_dependency(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(create_repository, scope=Scope.REQUEST)

        init(AppContainer())
        repo = resolve(Repository)

        assert isinstance(repo, Repository)
        assert isinstance(repo.db, Database)

    def test_function_provider_with_nested_dependencies(self) -> None:
        def create_service(repo: Repository) -> Service:
            return Service(repo)

        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(create_repository, scope=Scope.REQUEST)
            service: object = provider(create_service, scope=Scope.REQUEST)

        init(AppContainer())
        service = resolve(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)

    def test_function_provider_dependency_scope_mixing(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(create_repository, scope=Scope.REQUEST)

        init(AppContainer())
        repo1 = resolve(Repository)
        repo2 = resolve(Repository)

        assert repo1 is repo2
        assert repo1.db is repo2.db


class TestFunctionProvidersWithExplicitType:
    def test_function_provider_with_provides_interface(self) -> None:
        class IDatabase:
            pass

        class PostgresDB(IDatabase):
            def __init__(self) -> None:
                self.driver: str = "postgres"

        def create_postgres() -> PostgresDB:
            return PostgresDB()

        class AppContainer(Container):
            db: object = provider(create_postgres, provides=IDatabase, scope=Scope.APP)

        init(AppContainer())
        db = resolve(IDatabase)

        assert isinstance(db, PostgresDB)
        assert isinstance(db, IDatabase)
        assert db.driver == "postgres"

    def test_function_provider_with_provides_resolves_by_interface(self) -> None:
        class IDatabase:
            pass

        class PostgresDB(IDatabase):
            def __init__(self) -> None:
                self.driver: str = "postgres"

        class Service:
            def __init__(self, db: IDatabase) -> None:
                self.db: IDatabase = db

        def create_postgres() -> PostgresDB:
            return PostgresDB()

        class AppContainer(Container):
            db: object = provider(create_postgres, provides=IDatabase, scope=Scope.APP)
            service: object = provider(Service, scope=Scope.REQUEST)

        init(AppContainer())
        service = resolve(Service)

        assert isinstance(service.db, PostgresDB)
        assert isinstance(service.db, IDatabase)


class TestAsyncFunctionProviders:
    @pytest.mark.asyncio
    async def test_async_function_provider(self) -> None:
        async def create_db_async() -> Database:
            return Database("async://db")

        class AppContainer(Container):
            db: object = provider(create_db_async, scope=Scope.REQUEST)

        init(AppContainer())
        db = await aresolve(Database)

        assert isinstance(db, Database)
        assert db.url == "async://db"

    @pytest.mark.asyncio
    async def test_async_function_provider_with_dependencies(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(create_repository, scope=Scope.REQUEST)
            service: object = provider(create_service_async, scope=Scope.REQUEST)

        init(AppContainer())
        service = await aresolve(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)


class TestMixedProviders:
    def test_function_and_class_providers_together(self) -> None:
        def create_service_from_repo(repo: Repository) -> Service:
            return Service(repo)

        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(Repository, scope=Scope.REQUEST)
            service: object = provider(create_service_from_repo, scope=Scope.REQUEST)

        init(AppContainer())
        service = resolve(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert isinstance(service.repo.db, Database)

    def test_class_depending_on_function_provider(self) -> None:
        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(Repository, scope=Scope.REQUEST)

        init(AppContainer())
        repo = resolve(Repository)

        assert isinstance(repo, Repository)
        assert isinstance(repo.db, Database)

    def test_function_depending_on_class_provider(self) -> None:
        def create_service(repo: Repository) -> Service:
            return Service(repo)

        class AppContainer(Container):
            db: object = provider(create_database, scope=Scope.APP)
            repo: object = provider(Repository, scope=Scope.REQUEST)
            service: object = provider(create_service, scope=Scope.REQUEST)

        init(AppContainer())
        service = resolve(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)


class TestEdgeCases:
    def test_function_without_return_type_raises_error(self) -> None:
        from spritze.exceptions import InvalidProvider

        def bad_provider(x):  # pyright: ignore[reportUnknownParameterType, reportMissingParameterType]
            return x  # pyright: ignore[reportUnknownVariableType]

        class AppContainer(Container):
            bad: object = provider(bad_provider, scope=Scope.APP)  # pyright: ignore[reportUnknownArgumentType]

        with pytest.raises(InvalidProvider, match="return type"):
            init(AppContainer())
