from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from sophie.db.base import Base, TimestampMixin, UUIDPKMixin


class ClinicalImport(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "clinical_import"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    provider: Mapped[str | None] = mapped_column(String(100), default=None)
    source_kind: Mapped[str] = mapped_column(String(20))  # csv/json/manual/pdf_confirmed
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    import_manifest_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_manifest.id"), default=None
    )


class LabResult(Base, UUIDPKMixin, TimestampMixin):
    """Never discards the original lab's unit or reference range. Never invents
    a reference interval. abnormal_flag only ever comes from the lab itself."""

    __tablename__ = "lab_result"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    clinical_import_id: Mapped[str] = mapped_column(ForeignKey("clinical_import.id"))
    sample_date: Mapped[date] = mapped_column(Date, index=True)
    test_name: Mapped[str] = mapped_column(String(200))
    canonical_test_id: Mapped[str | None] = mapped_column(String(100), default=None, index=True)
    value: Mapped[float | None] = mapped_column(Float, default=None)
    value_text: Mapped[str | None] = mapped_column(String(200), default=None)
    unit: Mapped[str | None] = mapped_column(String(50), default=None)
    reference_low: Mapped[float | None] = mapped_column(Float, default=None)
    reference_high: Mapped[float | None] = mapped_column(Float, default=None)
    reference_text: Mapped[str | None] = mapped_column(String(100), default=None)
    abnormal_flag: Mapped[str | None] = mapped_column(String(20), default=None)
    category: Mapped[str] = mapped_column(String(50), default="other")
    notes: Mapped[str | None] = mapped_column(default=None)


class BodyCompositionAssessment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "body_composition_assessment"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    assessed_at: Mapped[date] = mapped_column(Date, index=True)
    method: Mapped[str] = mapped_column(String(50))  # DEXA/bioimpedance-InBody/caliper/...
    provider: Mapped[str | None] = mapped_column(String(100), default=None)
    weight_kg: Mapped[float | None] = mapped_column(Float, default=None)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, default=None)
    lean_mass_kg: Mapped[float | None] = mapped_column(Float, default=None)
    segmental_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    visceral_metric: Mapped[float | None] = mapped_column(Float, default=None)
    notes: Mapped[str | None] = mapped_column(default=None)


class ClinicalSymptomNote(Base, UUIDPKMixin, TimestampMixin):
    """Optional, occasional, user-entered context only — never daily journaling,
    never a diagnostic input on its own."""

    __tablename__ = "clinical_symptom_note"

    profile_id: Mapped[str] = mapped_column(ForeignKey("profile.id"), index=True)
    entered_at: Mapped[date] = mapped_column(Date)
    symptom: Mapped[str] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(default=None)
