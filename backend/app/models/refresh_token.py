from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class RefreshToken(Base):
    """A refresh token issued to a user, identified by the JWT's `jti` claim.

    Each refresh rotates the token: the old row is revoked and points at its
    replacement. Presenting a revoked token again (outside a short grace
    window for concurrent refreshes) is treated as theft and revokes every
    active token of that user.
    """

    __tablename__ = "refresh_tokens"

    id = Column(String(32), primary_key=True)  # jti
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(String(32), nullable=True)

    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)
