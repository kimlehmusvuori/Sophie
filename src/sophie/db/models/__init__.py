"""Import every model module so Base.metadata is fully populated for
create_all() / Alembic autogenerate."""

from sophie.db.base import Base
from sophie.db.models.chat import ChatMessage
from sophie.db.models.clinical import (
    BodyCompositionAssessment,
    ClinicalImport,
    ClinicalSymptomNote,
    LabResult,
)
from sophie.db.models.core import FamilyHistoryItem, Profile, UserConfig
from sophie.db.models.health_intel import (
    AerobicEfficiencyPoint,
    CircadianSummary,
    HearingSummary,
    MovementBaseline,
    RecoverySummary,
    TrainingLoadSummary,
    WellbeingAssessment,
)
from sophie.db.models.imports import AppleHealthMetricCatalog, ImportManifest
from sophie.db.models.planning import (
    CalendarSnapshot,
    DecisionLog,
    ManualCheckin,
    Plan,
    Session,
)
from sophie.db.models.summaries import DailyHealthSummary, WeeklySummary
from sophie.db.models.weather import WeatherSnapshot
from sophie.db.models.workouts import CanonicalWorkout, WorkoutSourceProvenance

__all__ = [
    "Base",
    "Profile",
    "UserConfig",
    "FamilyHistoryItem",
    "ImportManifest",
    "AppleHealthMetricCatalog",
    "CanonicalWorkout",
    "WorkoutSourceProvenance",
    "DailyHealthSummary",
    "WeeklySummary",
    "TrainingLoadSummary",
    "RecoverySummary",
    "CircadianSummary",
    "WellbeingAssessment",
    "HearingSummary",
    "AerobicEfficiencyPoint",
    "MovementBaseline",
    "WeatherSnapshot",
    "ClinicalImport",
    "LabResult",
    "BodyCompositionAssessment",
    "ClinicalSymptomNote",
    "ManualCheckin",
    "Plan",
    "Session",
    "CalendarSnapshot",
    "DecisionLog",
    "ChatMessage",
]
