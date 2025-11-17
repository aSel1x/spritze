from dataclasses import dataclass
from typing import Annotated, Protocol, runtime_checkable

from typing_extensions import override

from spritze import Container, Depends, Scope, init, inject, provider, resolve


@dataclass
class ConfigFixture:
    value: str | None = "default_value"

    def set_value(self, new_value: str) -> None:
        self.value = new_value


@runtime_checkable
class SessionProtocol(Protocol):
    active: bool

    def close(self) -> None: ...


class SessionImpl(SessionProtocol):
    def __init__(self) -> None:
        self.active: bool = True

    @override
    def close(self) -> None:
        self.active = False


@runtime_checkable
class RepositoryProtocol(Protocol):
    session: SessionProtocol


class RepositoryImpl(RepositoryProtocol):
    def __init__(self, session: SessionProtocol) -> None:
        self.session: SessionProtocol = session


class ServiceA:
    def __init__(self, repo: RepositoryProtocol) -> None:
        self.repo: RepositoryProtocol = repo
        self.value: str = "ServiceA"


class ServiceB:
    def __init__(self, repo: RepositoryProtocol, service_a: ServiceA) -> None:
        self.repo: RepositoryProtocol = repo
        self.service_a: ServiceA = service_a
        self.value: str = "ServiceB"


class ContainerFixture(Container):
    @provider(scope=Scope.REQUEST)
    def session(self) -> SessionProtocol:
        return SessionImpl()

    # TODO: provide_as
    repository: object = provider(RepositoryImpl, provide_as=RepositoryProtocol)

    @provider(scope=Scope.REQUEST)
    def service_a(self, repo: RepositoryProtocol) -> ServiceA:
        return ServiceA(repo)

    service_b: object = provider(ServiceB)


def test_injector_resolution() -> None:
    init(ContainerFixture, context={ConfigFixture: ConfigFixture()})

    @inject
    def handler(
        svc_a: Annotated[ServiceA, Depends()],
        svc_b: Annotated[ServiceB, Depends()],
        sess: Annotated[SessionProtocol, Depends()],
    ) -> None:
        assert isinstance(svc_a, ServiceA)
        assert isinstance(svc_b, ServiceB)
        assert isinstance(sess, SessionImpl)

        assert svc_b.service_a is svc_a
        assert sess.active is True

        assert svc_a.repo is svc_b.repo
        assert isinstance(svc_a.repo, RepositoryImpl)
        assert svc_a.repo.session is sess

    handler()


def test_resolve_resolutions() -> None:
    init(ContainerFixture, context={ConfigFixture: ConfigFixture()})

    session = resolve(SessionProtocol)
    service_a = resolve(ServiceA)
    service_b = resolve(ServiceB)

    assert session.active is True
    assert isinstance(session, SessionImpl)
    assert session is service_a.repo.session
    assert session is service_b.repo.session
    assert isinstance(service_a, ServiceA)
    assert isinstance(service_b, ServiceB)
