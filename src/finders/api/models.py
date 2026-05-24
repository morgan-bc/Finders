from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    query: str
    model: Optional[str] = None
    fast_model: Optional[str] = None
    max_iterations: int = Field(default=10, ge=1, le=50)
    memory_enabled: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
