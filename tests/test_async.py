"""Tests for async functionality."""

import pytest

from spritze import Container, Scope, aresolve, init, provider
from spritze.exceptions import AsyncSyncMismatch


class AsyncService:
    def __init__(self) -> None:
        self.value: str = "async"

    @classmethod
    async def create(cls) -> "AsyncService":
        instance = cls.__new__(cls)
        instance.value = "async"
        return instance


class SyncService:
    def __init__(self) -> None:
        self.value: str = "sync"


class TestAsync:
    @pytest.mark.asyncio
    async def test_async_provider(self) -> None:
        """Test async provider resolution."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            async def async_service(self) -> AsyncService:
                return await AsyncService.create()

        init(TestContainer)

        service = await aresolve(AsyncService)
        assert isinstance(service, AsyncService)
        assert service.value == "async"

    @pytest.mark.asyncio
    async def test_async_provider_with_dependency(self) -> None:
        """Test async provider with dependencies."""

        class DependentService:
            def __init__(self, sync: SyncService) -> None:
                self.sync: SyncService = sync

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def sync_service(self) -> SyncService:
                return SyncService()

            @provider(scope=Scope.APP)
            async def async_service(self) -> AsyncService:
                return await AsyncService.create()

            @provider(scope=Scope.APP)
            async def dependent_service(
                self, sync: SyncService, _: AsyncService
            ) -> DependentService:
                return DependentService(sync)

        init(TestContainer)

        dependent = await aresolve(DependentService)
        assert isinstance(dependent, DependentService)
        assert isinstance(dependent.sync, SyncService)

    def test_async_provider_in_sync_context(self) -> None:
        """Test that async provider cannot be resolved in sync context."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            async def async_service(self) -> AsyncService:
                return await AsyncService.create()

        init(TestContainer)

        with pytest.raises(AsyncSyncMismatch):
            from spritze import resolve

            _ = resolve(AsyncService)

    @pytest.mark.asyncio
    async def test_sync_provider_in_async_context(self) -> None:
        """Test that sync provider can be resolved in async context."""

        class TestContainer(Container):
            @provider(scope=Scope.APP)
            def sync_service(self) -> SyncService:
                return SyncService()

        init(TestContainer)

        service = await aresolve(SyncService)
        assert isinstance(service, SyncService)
        assert service.value == "sync"
