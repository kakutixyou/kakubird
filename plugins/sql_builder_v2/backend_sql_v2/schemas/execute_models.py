from typing import Any, Optional
from pydantic import BaseModel

class ExecuteRequest(BaseModel):
    sql: str
    db_path: str
    params: list = []

class ExecuteResult(BaseModel):
    success: bool
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
    affected_rows: int
    error: Optional[str] = None
    query_id: str