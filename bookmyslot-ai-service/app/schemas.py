from pydantic import BaseModel
from typing import List


class Location(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Finding(BaseModel):
    class_id: int
    label: str
    confidence: float
    location: Location


class Analysis(BaseModel):
    findings: List[Finding]


class AnalyseResponse(BaseModel):
    success: bool
    analysis: Analysis | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    service: str
    status: str
