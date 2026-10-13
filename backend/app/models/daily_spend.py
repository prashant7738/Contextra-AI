from sqlalchemy import BigInteger, Column, Date

from app.database import Base


class DailySpend(Base):
    """Global AI spend for one UTC day, stored in micro-USD (1 USD = 1_000_000)."""

    __tablename__ = "daily_spend"

    day = Column(Date, primary_key=True)
    spent_micro_usd = Column(BigInteger, nullable=False, default=0)
