from typing import Annotated

from spritze import Container, Depends, Scope, init, inject, provider


# Domain services
class PublicService:
    def who(self) -> str:
        return "public"


class AdminService:
    def who(self) -> str:
        return "admin"


# Containers
class PublicContainer(Container):
    @provider(scope=Scope.APP)
    def public_service(self) -> PublicService:
        return PublicService()


class AdminContainer(Container):
    @provider(scope=Scope.APP)
    def admin_service(self) -> AdminService:
        return AdminService()


# Initialize container
init(PublicContainer())


@inject
def public_route(svc: Annotated[PublicService, Depends()]) -> str:
    return f"hello {svc.who()}"


if __name__ == "__main__":
    print(public_route())  # hello public

    # Switch to admin container
    init(AdminContainer())

    @inject
    def admin_route(svc: Annotated[AdminService, Depends()]) -> str:
        return f"hello {svc.who()}"

    print(admin_route())  # hello admin
