from pydantic import BaseModel
from typing import Any

class SimulationRunCreate(BaseModel):
    meal_ids: list[int] | None = None  # Ha None vagy üres: összes étkezés
    timesteps: int | None = None  # Opcionális; default backendben 500
    mode: str | None = None  # 'simple' (default) vagy 'physio'
    full_day: bool | None = None  # True esetén 24 órás futás (1440 perc / timesteps felülírása)

class SimulationRunRead(BaseModel):
    id: int
    patient_id: int
    created_at: str
    started_at: str
    finished_at: str
    result_metrics: str
    chart_path: str | None
    class Config:
        from_attributes = True
