from pydantic import BaseModel
from typing import Any, Optional, List, Dict

class Condition(BaseModel):
    field: str
    operator: str
    value: Any

class SQLRequest(BaseModel):
    table: str
    columns: List[str]
    conditions: List[Condition]
    
    
class ExecuteRequest(BaseModel):
    sql: str
    db_path: str
    params: list = []

class AnalysisResponse(BaseModel):
    type: str
    title: str
    icon: str
    description: str
    sql: str
    parts: List[Dict[str, str]]
    input: str

# 他の BuildRequest, BuildResponse などもここへ移動...
# Pydanticを使って、変なデータが入ってこないようにガードします。