from typing import Optional
from sqlmodel import SQLModel, Field

class SimulationRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    created_at: str
    started_at: str
    finished_at: str
    input_meals: str  # JSON
    result_metrics: str  # JSON
    chart_path: str | None = None
    log_path: str | None = None
