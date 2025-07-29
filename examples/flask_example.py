from flask import Flask, jsonify

from spritze.core.container import Container
from spritze.core.entities import Depends, Scope
from spritze.decorators import provide


# 1. Define our services
class Settings:
    def __init__(self, value: str):
        print(f"Settings created with value: '{value}' (APP scope)")
        self.value = value


class SyncResource:
    _id_counter = 0

    def __init__(self):
        self.id = SyncResource._id_counter
        SyncResource._id_counter += 1
        print(f"Resource [{self.id}] aquired.")

    def use(self) -> str:
        return f"using resource {self.id}"

    def close(self):
        print(f"Resource [{self.id}] released.")


class MainService:
    def __init__(self, settings: Settings, resource: SyncResource):
        self._settings = settings
        self._resource = resource
        print("MainService created (REQUEST scope)")

    def process(self):
        res_usage = self._resource.use()
        return f"Processed with {self._settings.value} and {res_usage}"


# 2. Create a container and define providers in it
class AppContainer(Container):
    @provide(scope=Scope.APP)
    def provide_settings(self) -> Settings:
        # In a real application, this would be reading from .env or a config
        return Settings(value="prod_settings")

    @provide(scope=Scope.REQUEST)
    def provide_resource(self) -> SyncResource:
        res = SyncResource()
        try:
            yield res
        finally:
            res.close()

    @provide(scope=Scope.REQUEST)
    def provide_main_service(
        self, settings: Settings, resource: SyncResource
    ) -> MainService:
        return MainService(settings, resource)


# 3. Initialize the container and get the injector from it
container = AppContainer()
inject = container.injector()

# 4. Create a Flask application and use the injector
app = Flask(__name__)


@app.route("/")
@inject
def index(service: Depends[MainService], settings: Depends[Settings]):
    # Make sure the APP-scoped dependency is the same
    print(
        f"Is settings in service the same as injected? {service._settings is settings}"
    )
    result = service.process()
    return jsonify({"data": result})


if __name__ == "__main__":
    app.run(port=8002, debug=False)
