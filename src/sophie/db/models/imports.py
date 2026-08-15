from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class ImportManifest(Base, UUIDPKMixin, TimestampMixin):
    """Idempotence + audit trail for every import. Repeated import of the same
    content must not duplicate records; failed imports must not look successful."""

    __tablename__ = "import_manifest"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"))
    source_type: Mapped[str] = mapped_column(
        String(50)
    )  # apple_health/sports_tracker/clinical/body_composition
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    importer_version: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    state: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending/success/partial/failed
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_detected: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error_summary: Mapped[str | None] = mapped_column(default=None)


class AppleHealthMetricCatalog(Base, UUIDPKMixin):
    """Lightweight discovery catalogue of every Apple Health record type seen,
    so future development is aware of what data already exists without
    persisting millions of unsupported raw records."""

    __tablename__ = "apple_health_metric_catalog"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"))
    record_type: Mapped[str] = mapped_column(String(200), index=True)
    friendly_name: Mapped[str] = mapped_column(String(200))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    approx_record_count: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str | None] = mapped_column(String(50), default=None)
    status: Mapped[str] = mapped_column(String(30), default="recognized_unused")
    sophie_use: Mapped[str | None] = mapped_column(default=None)
