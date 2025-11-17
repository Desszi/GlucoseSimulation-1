from typing import Optional
from sqlmodel import SQLModel, Field
import enum

class UserRole(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole
