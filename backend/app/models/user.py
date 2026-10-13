from sqlalchemy import BigInteger, Column, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    # Monthly OpenAI spend cap and usage in micro-USD (1 USD = 1_000_000).
    monthly_budget_micro_usd = Column(BigInteger, nullable=False, default=1_000_000)
    spent_micro_usd = Column(BigInteger, nullable=False, default=0)
    # UTC month ("YYYY-MM") that spent_micro_usd belongs to; a new month resets it lazily.
    spend_month = Column(String(7), nullable=True)
