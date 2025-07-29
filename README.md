# spritze

[![CI](https://github.com/aSel1x/spritze/actions/workflows/ci.yml/badge.svg)](https://github.com/aSel1x/spritze/actions/workflows/ci.yml)
[![Code Quality](https://github.com/aSel1x/spritze/actions/workflows/quality.yml/badge.svg)](https://github.com/aSel1x/spritze/actions/workflows/quality.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/spritze.svg)](https://pypi.org/project/spritze/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A Dependency Injection framework for Python.

## License

Apache 2.0 — see [LICENSE](LICENSE)

## Features

- Modern, type-safe dependency injection for Python 3.11+
- Scopes: APP (singleton), REQUEST (per-request)
- Sync & async support, context managers
- No global state, explicit containers
- Decorator-based provider registration
- Easy integration with FastAPI, Flask, Litestar, etc.

## Installation

```bash
uv add spritze
# or
pip install spritze
```

## Usage

Here's a quick example of how to use Spritze:

```python
from spritze.core.container import Container
from spritze.core.entities import Depends, Scope
from spritze.decorators import provide


class MyService:
    def __init__(self, value: int):
        self.value = value


class AppContainer(Container):
    @provide(scope=Scope.APP)
    def provide_config_value(self) -> int:
        return 123

    @provide(scope=Scope.REQUEST)
    def provide_my_service(self, config_value: int) -> MyService:
        return MyService(value=config_value)


app_container = AppContainer()


@app_container.injector()
def my_function(service: Depends[MyService]):
    return f"Service value: {service.value}"


if __name__ == "__main__":
    result = my_function()
    print(result)  # Output: Service value: 123
```

## Examples

See the [examples/](examples/) directory for real-world usage with Flask, Litestar, etc.
