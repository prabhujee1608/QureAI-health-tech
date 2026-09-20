from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from ml_model import predict_wait
from models import Doctor, Patient, QueueHistory, QueueStatus, Token
from schemas import DoctorAction, DoctorCreate, PatientRegister, PredictionRequest


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    use_llm: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(title="Smart OPD Queue Predictor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        if not db.scalar(select(Doctor.id).limit(1)):
            doctor = Doctor(name="Dr. Ananya Sharma", department="General Medicine")
            db.add(doctor)
            db.commit()


def token_payload(token: Token, db: Session) -> dict[str, Any]:
    ahead = db.scalar(
        select(func.count(Token.id)).where(
            Token.status == QueueStatus.waiting,
            Token.queue_position < token.queue_position,
        )
    ) or 0
    doctor = token.patient.doctor
    wait = predict_wait(ahead, doctor.average_consultation_minutes, doctor.available, 1.0)
    return {
        "token": token.token_number,
        "patient": token.patient.name,
        "doctor": doctor.name,
        "department": doctor.department,
        "status": token.status.value,
        "patients_ahead": ahead,
        "estimated_wait_minutes": wait,
        "queue_position": token.queue_position,
    }


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", "database": "connected", "llm_enabled": bool(settings.use_llm and settings.openai_api_key)}


@app.get("/api/availability/{hospital_id}")
def checkup_availability(hospital_id: str) -> dict[str, Any]:
    hospitals = {
        "citycare": {"name": "CityCare Hospital", "city": "Pune", "load": "Normal", "next_slot": "10:30 AM", "doctors_available": 4, "departments": ["General Medicine", "Cardiology", "Pediatrics"]},
        "apollo": {"name": "Apollo Care Centre", "city": "Mumbai", "load": "Busy", "next_slot": "11:15 AM", "doctors_available": 6, "departments": ["General Medicine", "Orthopedics", "Dermatology"]},
        "fortis": {"name": "Fortis Wellness Hospital", "city": "Bengaluru", "load": "Normal", "next_slot": "10:45 AM", "doctors_available": 5, "departments": ["General Medicine", "Neurology", "Pediatrics"]},
        "manipal": {"name": "Manipal Health Point", "city": "Hyderabad", "load": "Light", "next_slot": "9:50 AM", "doctors_available": 3, "departments": ["General Medicine", "Cardiology", "Orthopedics"]},
    }
    availability = hospitals.get(hospital_id.lower())
    if not availability:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return {"hospital_id": hospital_id.lower(), "updated": "just now", **availability, "prototype_data": True}


@app.post("/patient/register", status_code=201)
def register_patient(request: PatientRegister, db: Session = Depends(get_db)) -> dict[str, Any]:
    doctor = db.get(Doctor, request.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    last_position = db.scalar(select(func.max(Token.queue_position))) or 116
    token_number = f"A{last_position + 1:03d}"
    patient = Patient(name=request.name, age=request.age, phone=request.phone, doctor_id=doctor.id)
    db.add(patient)
    db.flush()
    token = Token(token_number=token_number, patient_id=patient.id, queue_position=last_position + 1)
    db.add(token)
    db.flush()
    db.add(QueueHistory(token_id=token.id, status=QueueStatus.waiting.value, notes="Registered at reception"))
    db.commit()
    db.refresh(token)
    return token_payload(token, db)


@app.get("/queue/status")
def queue_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    tokens = db.scalars(select(Token).order_by(Token.queue_position)).all()
    return {"current_token": next((t.token_number for t in tokens if t.status == QueueStatus.consulting), None), "queue": [token_payload(token, db) for token in tokens if token.status != QueueStatus.completed]}


@app.get("/waiting-time/{token}")
def waiting_time(token: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.scalar(select(Token).where(Token.token_number == token.upper()))
    if not record:
        raise HTTPException(status_code=404, detail="Token not found")
    return token_payload(record, db)


@app.post("/doctor/start")
def start_consultation(request: DoctorAction, db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.scalar(select(Token).where(Token.token_number == request.token.upper()))
    if not record:
        raise HTTPException(status_code=404, detail="Token not found")
    record.status = QueueStatus.consulting
    record.started_at = datetime.utcnow()
    db.add(QueueHistory(token_id=record.id, status=QueueStatus.consulting.value, notes="Consultation started"))
    db.commit()
    return token_payload(record, db)


@app.post("/doctor/end")
def end_consultation(request: DoctorAction, db: Session = Depends(get_db)) -> dict[str, Any]:
    record = db.scalar(select(Token).where(Token.token_number == request.token.upper()))
    if not record:
        raise HTTPException(status_code=404, detail="Token not found")
    record.status = QueueStatus.completed
    record.ended_at = datetime.utcnow()
    db.add(QueueHistory(token_id=record.id, status=QueueStatus.completed.value, notes="Consultation completed"))
    next_token = db.scalar(select(Token).where(Token.status == QueueStatus.waiting).order_by(Token.queue_position))
    if next_token:
        next_token.status = QueueStatus.consulting
        next_token.started_at = datetime.utcnow()
        db.add(QueueHistory(token_id=next_token.id, status=QueueStatus.consulting.value, notes="Advanced after completion"))
    db.commit()
    return {"completed": record.token_number, "next": token_payload(next_token, db) if next_token else None}


@app.post("/reception/doctor", status_code=201)
def create_doctor(request: DoctorCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    doctor = Doctor(**request.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return {
        "id": doctor.id,
        "name": doctor.name,
        "department": doctor.department,
        "average_consultation_minutes": doctor.average_consultation_minutes,
        "available": doctor.available,
    }


@app.get("/analytics")
def analytics(db: Session = Depends(get_db)) -> dict[str, Any]:
    completed = db.scalars(select(Token).where(Token.status == QueueStatus.completed)).all()
    durations = [((t.ended_at - t.started_at).total_seconds() / 60) for t in completed if t.ended_at and t.started_at]
    return {"patients_served": len(completed), "average_waiting_minutes": 27, "average_consultation_minutes": round(sum(durations) / len(durations), 1) if durations else 4.2, "peak_hours": "10:00 AM - 12:00 PM", "doctor_performance": []}


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    movement = {"fast": 0.85, "normal": 1.0, "busy": 1.15, "delayed": 1.35}[request.queue_speed]
    load = {"low": 0.95, "normal": 1.0, "high": 1.15}[request.opd_load]
    estimate = predict_wait(request.patients_ahead, request.average_consultation_minutes, request.doctor_available, movement * load)
    base = request.patients_ahead * request.average_consultation_minutes
    return {"estimated_wait_minutes": estimate, "likely_range": f"{max(4, estimate - 4)}-{estimate + 5} min", "base_estimate_minutes": round(base, 1), "prototype_estimate": True, "explanation": "Scikit-learn regression estimate using queue position, consultation duration, doctor availability and queue movement. Not medically validated."}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, str | bool]:
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Whisper is disabled. Set OPENAI_API_KEY to enable transcription.")
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Upload an audio file.")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        result = client.audio.transcriptions.create(model=settings.whisper_model, file=(audio.filename or "recording.webm", io.BytesIO(await audio.read()), audio.content_type))
        return {"text": result.text, "prototype": False}
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Whisper request failed: {error}") from error


@app.post("/api/prediction-explanation")
def prediction_explanation(request: PredictionRequest) -> dict[str, str | bool]:
    fallback = f"There are {request.patients_ahead} patients ahead. At {request.average_consultation_minutes:.1f} minutes per consultation, the queue is moving at a {request.queue_speed} pace. This is a simulated prototype explanation."
    if not settings.use_llm or not settings.openai_api_key:
        return {"text": fallback, "prototype": True}
    try:
        from openai import OpenAI
        response = OpenAI(api_key=settings.openai_api_key).chat.completions.create(model=settings.openai_model, temperature=0.2, max_tokens=120, messages=[{"role": "system", "content": "Explain OPD queue estimates in two short sentences. Do not give medical advice."}, {"role": "user", "content": fallback}])
        return {"text": response.choices[0].message.content or fallback, "prototype": True}
    except Exception:
        return {"text": fallback, "prototype": True}
