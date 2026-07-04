import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ShadowStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProxyRequestModel(Base):
    """Primary proxy response staged for async shadow evaluation."""

    __tablename__ = "proxy_requests"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    request_body: Mapped[dict] = mapped_column(JSON, nullable=False)
    primary_status: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_response: Mapped[str] = mapped_column(Text, nullable=False)
    latency_primary_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    shadow_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ShadowStatus.PENDING.value,
        index=True,
    )

    candidate_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_candidate_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    primary_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    candidate_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    exact_action_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    primary_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shadow_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ShadowEvaluationModel(Base):
    __tablename__ = "shadow_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    request_body: Mapped[dict] = mapped_column(JSON, nullable=False)

    primary_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    candidate_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exact_action_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    primary_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_action: Mapped[str | None] = mapped_column(String(255), nullable=True)

    shadow_outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    latency_primary_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_candidate_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
