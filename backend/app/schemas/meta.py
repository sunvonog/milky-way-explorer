from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class BuildResponse(BaseModel):
    build_id: str
    created_at: str
    source_snapshots: dict[str, str]
    row_counts: dict[str, int]
