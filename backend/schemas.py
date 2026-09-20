from typing import Literal
from pydantic import BaseModel, Field


class PatientRegister(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=0, le=120)
    doctor_id: int = 1
    phone: str | None = None


class DoctorCreate(BaseModel):
    name: str
    department: str = "General Medicine"
    average_consultation_minutes: float = Field(default=4.2, gt=0, le=60)


class PredictionRequest(BaseModel):
    patients_ahead: int = Field(ge=0, le=100)
    average_consultation_minutes: float = Field(default=4.2, gt=0, le=60)
    doctor_available: bool = True
    queue_movement: float = Field(default=1.0, gt=0, le=2)
    queue_speed: Literal["fast", "normal", "busy", "delayed"] = "normal"
    opd_load: Literal["low", "normal", "high"] = "normal"


class DoctorAction(BaseModel):
    token: str
