from pydantic import BaseModel


class ProjectDetailsResponse(BaseModel):
    project_code: str
    project_name: str
    account_id: str
    project_lead_id: str | None
    lead_name: str | None

