from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class QueueStatus(str, Enum):
    waiting = "waiting"
    consulting = "consulting"
    completed = "completed"
    cancelled = "cancelled"


class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120))
    average_consultation_minutes: Mapped[float] = mapped_column(Float, default=4.2)
    available: Mapped[bool] = mapped_column(default=True)
    patients: Mapped[list["Patient"]] = relationship(back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    doctor: Mapped[Doctor] = relationship(back_populates="patients")
    tokens: Mapped[list["Token"]] = relationship(back_populates="patient")


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    status: Mapped[QueueStatus] = mapped_column(default=QueueStatus.waiting)
    queue_position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    patient: Mapped[Patient] = relationship(back_populates="tokens")


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    appointment_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")


class QueueHistory(Base):
    __tablename__ = "queue_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_id: Mapped[int] = mapped_column(ForeignKey("tokens.id"))
    status: Mapped[str] = mapped_column(String(30))
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
