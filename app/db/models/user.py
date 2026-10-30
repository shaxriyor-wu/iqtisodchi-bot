from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram ID
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    # budget summasi shu davr [period_start, period_end] uchun amal qiladi
    monthly_budget: Mapped[int] = mapped_column(BigInteger, default=0)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    anchor_day: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
