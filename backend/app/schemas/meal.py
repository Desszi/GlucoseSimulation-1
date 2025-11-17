from pydantic import BaseModel
from typing import Optional

class MealCreate(BaseModel):
    timestamp: str
    carbs_g: int
    meal_type: str
    notes: Optional[str] = None

class MealRead(BaseModel):
    id: int
    timestamp: str
    carbs_g: int
    meal_type: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True
