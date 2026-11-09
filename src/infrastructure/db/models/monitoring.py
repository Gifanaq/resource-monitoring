from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.models.base import Base, TimestampMixin


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)


class ServiceModel(TimestampMixin, Base):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("failure_threshold > 0", name="positive_failure_threshold"),
        CheckConstraint("recovery_threshold > 0", name="positive_recovery_threshold"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    failure_threshold: Mapped[int] = mapped_column(SmallInteger, server_default="3")
    recovery_threshold: Mapped[int] = mapped_column(SmallInteger, server_default="2")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class CheckTypeModel(Base):
    __tablename__ = "check_types"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class CheckModel(TimestampMixin, Base):
    __tablename__ = "checks"
    __table_args__ = (
        CheckConstraint("interval_sec > 0", name="positive_interval"),
        CheckConstraint(
            "timeout_sec > 0 AND timeout_sec < 'Infinity'::double precision",
            name="finite_positive_timeout",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    check_type_id: Mapped[int] = mapped_column(ForeignKey("check_types.id"))
    target: Mapped[str] = mapped_column(Text)
    interval_sec: Mapped[int] = mapped_column(Integer, server_default="60")
    timeout_sec: Mapped[float] = mapped_column(Double, server_default="10")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class HttpCheckSettingsModel(Base):
    __tablename__ = "http_check_settings"
    __table_args__ = (
        CheckConstraint("expected_status BETWEEN 100 AND 599", name="http_status"),
        CheckConstraint("slow_response_ms > 0", name="positive_slow_response"),
    )

    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), primary_key=True)
    expected_status: Mapped[int] = mapped_column(SmallInteger, server_default="200")
    follow_redirects: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    slow_response_ms: Mapped[int] = mapped_column(Integer, server_default="2000")
    content_pattern: Mapped[str | None] = mapped_column(Text)


class TlsCheckSettingsModel(Base):
    __tablename__ = "tls_check_settings"
    __table_args__ = (
        CheckConstraint("warn_before_days > 0", name="positive_warning_threshold"),
    )

    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"), primary_key=True)
    warn_before_days: Mapped[int] = mapped_column(SmallInteger, server_default="14")


class CheckResultModel(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        CheckConstraint("status_code BETWEEN 100 AND 599", name="http_status"),
        CheckConstraint("response_time_ms >= 0", name="nonnegative_response_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    check_id: Mapped[int] = mapped_column(ForeignKey("checks.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    success: Mapped[bool] = mapped_column(Boolean)
    status_code: Mapped[int | None] = mapped_column(SmallInteger)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    tls_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "ix_check_results_check_id_checked_at",
    CheckResultModel.check_id,
    CheckResultModel.checked_at.desc(),
)


class StatusLevelModel(Base):
    __tablename__ = "status_levels"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    label: Mapped[str] = mapped_column(String(64))
    color: Mapped[str] = mapped_column(String(16))
    severity: Mapped[int] = mapped_column(SmallInteger)


class ServiceStatusModel(Base):
    __tablename__ = "service_statuses"
    __table_args__ = (
        CheckConstraint("consecutive_failures >= 0", name="nonnegative_failures"),
        CheckConstraint("consecutive_successes >= 0", name="nonnegative_successes"),
    )

    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), primary_key=True)
    status_level_id: Mapped[int] = mapped_column(ForeignKey("status_levels.id"))
    consecutive_failures: Mapped[int] = mapped_column(Integer, server_default="0")
    consecutive_successes: Mapped[int] = mapped_column(Integer, server_default="0")
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
