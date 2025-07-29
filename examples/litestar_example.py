import uvicorn
from litestar import Litestar, get

from spritze.core.container import Container
from spritze.core.entities import Depends, Scope
from spritze.decorators import provide


# 1. Define our services
class ReportingService:
    def __init__(self):
        print("ReportingService created (APP scope)")

    async def generate_report(self) -> dict:
        return {"source": "app", "data": "report_content"}


class AuditService:
    def __init__(self):
        print("AuditService created (REQUEST scope)")

    async def log_access(self, user: str):
        print(f"AUDIT: User '{user}' accessed the report.")


# 2. Create a container and define providers in it
class AppContainer(Container):
    @provide(scope=Scope.APP)
    def reporting_service(self) -> ReportingService:
        return ReportingService()

    @provide(scope=Scope.REQUEST)
    def audit_service(self) -> AuditService:
        return AuditService()


# 3. Initialize the container and get the injector from it
container = AppContainer()
inject = container.injector()


# 4. Create a LiteStar application and use the injector
@get("/")
@inject
async def get_report(
    reporter: Depends[ReportingService], auditor: Depends[AuditService]
) -> dict:
    await auditor.log_access(user="test_user")
    report = await reporter.generate_report()
    return report


app = Litestar(route_handlers=[get_report])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
