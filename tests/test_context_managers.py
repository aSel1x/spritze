"""Tests for context manager providers."""

from collections.abc import AsyncIterable, Iterable

import pytest

from spritze import Container, Scope, aresolve, init, provider, resolve


class Resource:
    def __init__(self) -> None:
        self.closed: bool = False
        self.id: int = id(self)

    def close(self) -> None:
        self.closed = True


class AsyncResource:
    def __init__(self) -> None:
        self.closed: bool = False
        self.id: int = id(self)

    async def aclose(self) -> None:
        self.closed = True


class TestContextManagers:
    def test_sync_context_manager(self) -> None:
        """Test synchronous context manager provider."""

        class TestContainer(Container):
            @provider(scope=Scope.REQUEST)
            def resource(self) -> Iterable[Resource]:
                res = Resource()
                try:
                    yield res
                finally:
                    res.close()

        init(TestContainer)

        resource1 = resolve(Resource)
        assert not resource1.closed

        # Resolve again in same request - should be same instance
        resource2 = resolve(Resource)
        assert resource1 is resource2
        assert not resource2.closed

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test asynchronous context manager provider."""

        class TestContainer(Container):
            @provider(scope=Scope.REQUEST)
            async def async_resource(self) -> AsyncIterable[AsyncResource]:
                res = AsyncResource()
                try:
                    yield res
                finally:
                    await res.aclose()

        init(TestContainer)

        resource1 = await aresolve(AsyncResource)
        assert not resource1.closed

        # Resolve again in same request - should be same instance
        resource2 = await aresolve(AsyncResource)
        assert resource1 is resource2
        assert not resource2.closed

    def test_context_manager_with_dependencies(self) -> None:
        """Test context manager with dependencies."""

        class Dependency:
            def __init__(self) -> None:
                self.value: str = "dep"

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def dependency(self) -> Dependency:
                return Dependency()

            @provider(scope=Scope.REQUEST)
            def resource(self, dependency: Dependency) -> Iterable[Resource]:
                assert dependency.value == "dep"
                res = Resource()
                try:
                    yield res
                finally:
                    res.close()

        init(TestContainer)

        resource = resolve(Resource)
        assert not resource.closed

    @pytest.mark.asyncio
    async def test_async_context_manager_with_dependencies(self) -> None:
        """Test async context manager with dependencies."""

        class Dependency:
            def __init__(self) -> None:
                self.value: str = "dep"

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def dependency(self) -> Dependency:
                return Dependency()

            @provider(scope=Scope.REQUEST)
            async def async_resource(
                self, dependency: Dependency
            ) -> AsyncIterable[AsyncResource]:
                assert dependency.value == "dep"
                res = AsyncResource()
                try:
                    yield res
                finally:
                    await res.aclose()

        init(TestContainer)

        resource = await aresolve(AsyncResource)
        assert not resource.closed
