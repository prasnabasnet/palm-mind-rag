import uuid
from datetime import date, time

from sqlalchemy import Date, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255))
    interview_date: Mapped[date] = mapped_column(Date)
    interview_time: Mapped[time] = mapped_column(Time)