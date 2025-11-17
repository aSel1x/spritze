from collections.abc import Generator
from typing import Annotated

from flask import Flask, jsonify

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


class MainService:
    def __init__(self, settings: Settings, resource: SyncResource) -> None:
        self._settings: Settings = settings
        self._resource: SyncResource = resource
        print("MainService created (REQUEST scope)")

    @property
    def settings(self) -> Settings:
        return self._settings

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


# Initialize container
init(AppContainer)

# Flask application
app = Flask(__name__)


@app.route("/")
@inject
def index(
    service: Annotated[MainService, Depends()],
    settings: Annotated[Settings, Depends()],
):
    # Make sure the APP-scoped dependency is the same
    # Demonstrate that APP-scoped dependency is the same instance
    _same = service.settings is settings
    print(f"Is settings in service the same as injected? {_same}")
    result = service.process()
    return jsonify({"data": result})


if __name__ == "__main__":
    app.run(port=8002, debug=False)
