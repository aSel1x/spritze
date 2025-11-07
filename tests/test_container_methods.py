"""Tests for Container API methods and edge cases."""

import pytest

from spritze import Container, Scope, aresolve, init, provider, resolve
from spritze.exceptions import AsyncSyncMismatch


class Database:
    def __init__(self, url: str = "test_db") -> None:
        self.url: str = url


class Repository:
    def __init__(self, db: Database) -> None:
        self.db: Database = db


class AsyncService:
    def __init__(self, value: str = "async") -> None:
        self.value: str = value


class TestGlobalResolveAresolve:
    def test_resolve_basic(self) -> None:
        class AppContainer(Container):
            @provider(scope=Scope.APP)
            def database(self) -> Database:
                return Database("global_db")

        container = AppContainer()
        init(container)

        db = resolve(Database)
        assert db.url == "global_db"

    def test_resolve_with_dependencies(self) -> None:
        class AppContainer(Container):
            @provider(scope=Scope.APP)
            def database(self) -> Database:
                return Database("nested_db")

            @provider(scope=Scope.REQUEST)
            def repository(self, db: Database) -> Repository:
                return Repository(db)

        container = AppContainer()
        init(container)

        repo = resolve(Repository)
        assert repo.db.url == "nested_db"

    @pytest.mark.asyncio
    async def test_aresolve_basic(self) -> None:
        class AppContainer(Container):
            @provider(scope=Scope.APP)
            async def async_service(self) -> AsyncService:
                return AsyncService("async_value")

        container = AppContainer()
        init(container)

        service = await aresolve(AsyncService)
        assert service.value == "async_value"

    @pytest.mark.asyncio
    async def test_aresolve_with_dependencies(self) -> None:
        class AppContainer(Container):
            @provider(scope=Scope.APP)
            async def database(self) -> Database:
                return Database("async_db")

            @provider(scope=Scope.REQUEST)
            async def repository(self, db: Database) -> Repository:
                return Repository(db)

        container = AppContainer()
        init(container)

        repo = await aresolve(Repository)
        assert repo.db.url == "async_db"

    def test_resolve_sync_rejects_async_provider(self) -> None:
        class AppContainer(Container):
            @provider(scope=Scope.APP)
            async def async_service(self) -> AsyncService:
                return AsyncService()

        container = AppContainer()
        init(container)

        with pytest.raises(AsyncSyncMismatch, match="Cannot resolve async provider"):
            _ = resolve(AsyncService)


class TestMultiContainerMerging:
    def test_init_merges_providers_from_multiple_containers(self) -> None:
        class DatabaseContainer(Container):
            @provider(scope=Scope.APP)
            def database(self) -> Database:
                return Database("merged_db")

        class RepositoryContainer(Container):
            @provider(scope=Scope.REQUEST)
            def repository(self, db: Database) -> Repository:
                return Repository(db)

        db_container = DatabaseContainer()
        repo_container = RepositoryContainer()
        init(db_container, repo_container)

        repo = resolve(Repository)
        assert repo.db.url == "merged_db"

    def test_init_with_three_containers(self) -> None:
        class ContainerA(Container):
            @provider(scope=Scope.APP)
            def database(self) -> Database:
                return Database("a_db")

        class ContainerB(Container):
            @provider(scope=Scope.REQUEST)
            def repository(self, db: Database) -> Repository:
                return Repository(db)

        class ContainerC(Container):
            @provider(scope=Scope.APP)
            def async_service(self) -> AsyncService:
                return AsyncService("c_value")

        a = ContainerA()
        b = ContainerB()
        c = ContainerC()
        init(a, b, c)

        repo = resolve(Repository)
        service = resolve(AsyncService)
        assert repo.db.url == "a_db"
        assert service.value == "c_value"

    def test_init_with_no_containers_raises_error(self) -> None:
        with pytest.raises(ValueError, match="At least one container must be provided"):
            init()
