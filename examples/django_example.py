import importlib
from collections.abc import Callable, Generator
from typing import Annotated, Protocol, cast

from spritze import Container, Depends, Scope, init, inject, provider

# Domain services


class Settings:
    def __init__(self, value: str) -> None:
        print(f"Settings created with value: '{value}' (APP scope)")
        self.value: str = value


class SyncResource:
    _id_counter: int = 0

    def __init__(self) -> None:
        self.id: int = SyncResource._id_counter
        SyncResource._id_counter += 1
        print(f"Resource [{self.id}] acquired.")

    def use(self) -> str:
        return f"using resource {self.id}"

    def close(self) -> None:
        print(f"Resource [{self.id}] released.")
        return None


class MainService:
    def __init__(self, settings: Settings, resource: SyncResource) -> None:
        self._settings: Settings = settings
        self._resource: SyncResource = resource
        print("MainService created (REQUEST scope)")

    def process(self) -> str:
        res_usage: str = self._resource.use()
        return f"Processed with {self._settings.value} and {res_usage}"


# Container


class AppContainer(Container):
    @provider(scope=Scope.APP)
    def settings(self) -> Settings:
        return Settings(value="prod_settings")

    @provider(scope=Scope.REQUEST)
    def resource(self) -> Generator[SyncResource, None, None]:
        res = SyncResource()
        try:
            yield res
        finally:
            res.close()

    @provider(scope=Scope.REQUEST)
    def main_service(self, settings: Settings, resource: SyncResource) -> MainService:
        return MainService(settings, resource)


container = AppContainer()
init(container)

# In a typical Django app, you'd have `app_name` and named URL patterns.
app_name: str = "example"


# Django integration helpers


class Request(Protocol):
    """Minimal protocol for typing request objects without importing Django."""

    ...


class _DJ:
    """Compact namespace with Django compatibility helpers and app objects."""

    def __init__(self) -> None:
        self.path: Callable[[str, object], object] = self._get_path()
        self.json: Callable[[object], object] = self._json_response
        self.wsgi_app: object = self._get_wsgi_application()
        self.asgi_app: object = self._get_asgi_application()

    @staticmethod
    def _json_response(data: object) -> object:
        try:
            mod = importlib.import_module("django.http")
            jr = cast("Callable[[object], object]", mod.JsonResponse)
            return jr(data)
        except Exception:
            return {"__json__": data}

    @staticmethod
    def _get_path() -> Callable[[str, object], object]:
        try:
            mod = importlib.import_module("django.urls")
            fn = cast("Callable[[str, object], object]", mod.path)
            return fn
        except Exception:

            def _stub(route: str, view: object) -> tuple[str, object]:
                return (route, view)

            return _stub

    @staticmethod
    def _get_wsgi_application() -> object:
        try:
            mod = importlib.import_module("django.core.wsgi")
            make_app = cast("Callable[[], object]", mod.get_wsgi_application)
            return make_app()
        except Exception:

            def _stub_app(
                environ: object,
                start_response: Callable[[str, list[tuple[str, str]]], None],
            ) -> list[bytes]:
                del environ
                start_response("200 OK", [("Content-Type", "application/json")])
                return [b'{"detail":"WSGI stub"}']

            return _stub_app

    @staticmethod
    def _get_asgi_application() -> object:
        try:
            mod = importlib.import_module("django.core.asgi")
            make_app = cast("Callable[[], object]", mod.get_asgi_application)
            return make_app()
        except Exception:

            async def _stub_app(
                scope: object,
                receive: Callable[[], object],
                send: Callable[[object], object],
            ) -> None:
                del scope, receive, send
                return None

            return _stub_app


dj = _DJ()


@inject
def index(_request: Request, service: Annotated[MainService, Depends()]) -> object:
    return dj.json({"data": service.process()})


@inject
def item_detail(
    _request: Request,
    item_id: int,
    service: Annotated[MainService, Depends()],
) -> object:
    return dj.json({"id": item_id, "data": service.process()})


urlpatterns: list[object] = [
    dj.path("", index),
    dj.path("items/<int:item_id>/", item_detail),
]


def _run_devserver() -> None:
    try:
        conf_mod = importlib.import_module("django.conf")
        conf = cast("object", conf_mod.settings)
    except Exception:
        raise SystemExit(
            "Django is not installed. Install with `uv run pip install django`"
        ) from None
    if not bool(getattr(conf, "configured", False)):
        configure = getattr(conf, "configure", None)
        if configure is not None:
            configure(
                DEBUG=True,
                SECRET_KEY="dev",
                ROOT_URLCONF=__name__,
                ALLOWED_HOSTS=["*"],
                MIDDLEWARE=[
                    "django.middleware.security.SecurityMiddleware",
                    "django.middleware.common.CommonMiddleware",
                ],
                INSTALLED_APPS=[],
            )
    django = importlib.import_module("django")
    exec_mgmt = importlib.import_module("django.core.management")
    setup_fn = cast("Callable[[], None]", django.setup)
    setup_fn()
    exec_fn = cast(
        "Callable[[list[str]], None]",
        exec_mgmt.execute_from_command_line,
    )
    exec_fn(
        [
            "manage.py",
            "runserver",
            "127.0.0.1:8003",
        ]
    )


# Expose conventional application symbols like wsgi.py/asgi.py would do.
application: object = dj.wsgi_app
asgi_application: object = dj.asgi_app

# Limit public surface like a real app module
__all__ = [
    "app_name",
    "application",
    "asgi_application",
    "urlpatterns",
]


if __name__ == "__main__":
    _run_devserver()
