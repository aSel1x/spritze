from typing import Annotated

import uvicorn
from litestar import Litestar, get

from spritze import Container, Depends, Scope, init, inject, provider


# Domain services
class ReportingService:
    def __init__(self) -> None:
        print("ReportingService created (APP scope)")

    async def generate_report(self) -> dict[str, str]:
        return {"source": "app", "data": "report_content"}


class AuditService:
    def __init__(self) -> None:
        print("AuditService created (REQUEST scope)")

    async def log_access(self, user: str) -> None:
        print(f"AUDIT: User '{user}' accessed the report.")


# Container
class AppContainer(Container):
    @provider(scope=Scope.APP)
    def reporting_service(self) -> ReportingService:
        return ReportingService()

    @provider(scope=Scope.REQUEST)
    def audit_service(self) -> AuditService:
        return AuditService()


# Initialize container
init(AppContainer)


# Litestar application
@get("/")
@inject
async def get_report(
    reporter: Annotated[ReportingService, Depends()],
    auditor: Annotated[AuditService, Depends()],
) -> dict[str, str]:
    await auditor.log_access(user="test_user")
    report: dict[str, str] = await reporter.generate_report()
    return report


app = Litestar(route_handlers=[get_report])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
