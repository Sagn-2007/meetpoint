"""SQLAlchemy ORM models for collaborative sessions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MeetingSession(Base):
    """Meeting session entity."""

    __tablename__ = "meeting_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    invitation_code: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    host_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    network_type: Mapped[str] = mapped_column(String(32), default="walk", nullable=False)
    optimization_objective: Mapped[str] = mapped_column(String(32), default="median", nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # "active", "closed"
    result_is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    participants: Mapped[List[SessionParticipant]] = relationship(
        "SessionParticipant",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionParticipant.joined_at",
    )
    optimizations: Mapped[List[SessionOptimization]] = relationship(
        "SessionOptimization",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(SessionOptimization.created_at)",
    )


class SessionParticipant(Base):
    """Participant in a meeting session."""

    __tablename__ = "session_participants"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meeting_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    participant_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    session: Mapped[MeetingSession] = relationship(
        "MeetingSession",
        back_populates="participants",
    )


class SessionOptimization(Base):
    """Stored optimization result for a meeting session."""

    __tablename__ = "session_optimizations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meeting_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    objective: Mapped[str] = mapped_column(String(32), nullable=False)
    network_type: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    session: Mapped[MeetingSession] = relationship(
        "MeetingSession",
        back_populates="optimizations",
    )
