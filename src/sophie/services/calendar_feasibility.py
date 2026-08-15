"""Calendar feasibility engine — deterministic, LLM-free.

Per docs/ARCHITECTURE.md ("Calendar feasibility engine") and
docs/PRODUCT_SPEC.md §44: the LLM never invents calendar availability. This
module is the single source of truth for *when* a training session could
realistically happen next week; the coach (LLM or deterministic planner)
only ever picks among the `CalendarWindow`s this module already produced.
Nothing here needs an LLM, a database, or a network call — it is pure
scheduling logic over plain dataclasses, mirroring how
`sophie.domain.training_load`/`sophie.domain.recovery` document their
formulas in docs/HEALTH_LOGIC_AND_SAFETY.md.

Timezone contract: `busy_intervals` (and any `weather_by_date` keys) must
already represent *local* calendar days/wall-clock times — this module does
no timezone conversion itself (see `sophie.config.timezone.to_local`, which
the caller is expected to have applied when assembling these inputs). If a
`BusyInterval`'s `start`/`end` carry tzinfo, that tzinfo is treated as
already-local and stripped for comparison purposes only.

## Candidate generation

For each of the 7 days of the week starting `week_start` (a Monday), this
module sweeps candidate start times in `_CANDIDATE_STEP_MINUTES` (30-minute)
increments across the full day, and classifies each one as either a
`CalendarWindow` (feasible) or a `RejectedWindow` (infeasible, with a
`reason_code`):

- `"outside_allowed_hours"` — starts before the earliest allowed time
  (`preferences.earliest_weekday_session` on Mon-Fri, a more open
  `_WEEKEND_EARLIEST_TIME` on Sat/Sun — weekends have no school-dropoff
  constraint).
- `"after_latest_session_time"` — the session itself (duration only, not the
  post-session buffer) would end after `preferences.latest_session`.
- `"busy_calendar"` — the session plus `buffer_min` overlaps an existing
  busy interval (including all-day entries).

## Scoring (`rank_score`, 0.0-1.0)

Every feasible window gets a single weighted-sum score, each component
independently in `[0, 1]`, clamped at the end:

```
rank_score = clamp(
      0.40 * day_preference_score      # day-of-week + time-of-day fit
    + 0.20 * load_recovery_score       # current training load / recovery context
    + 0.15 * weather_score             # neutral (0.5) when weather is unavailable
    + 0.15 * padel_spacing_score       # soft penalty for hard efforts day-after-padel
    + 0.10 * rest_day_preservation_score
)
```

- **day_preference_score** = `0.6 * weekday_component + 0.4 * time_of_day_component`.
  For `SessionType.LONG`, `weekday_component` rewards
  `preferences.long_run_weekday_preference` order (1st choice → 1.0, 2nd →
  0.75, 3rd → 0.5, listed-but-later → 0.3, unlisted → 0.15) — per
  docs/PRODUCT_SPEC.md ("long run Friday-Sunday, Saturday preferred, Sunday
  second choice"). For other session types, weekends get a mild flat bump
  over weekdays (no day-of-week hierarchy is prescribed for quality/easy
  runs). `time_of_day_component` follows the documented weekday preference
  order post-dropoff → lunch → after-work on Mon-Fri, and is flat on
  weekends (no dropoff constraint).
- **load_recovery_score** reflects the week's overall `training_load_status`
  (low/typical/elevated/very_elevated) and `recovery_status`
  (normal/watch/concern) — this is current context for the whole week, not
  a per-day signal, so it shifts every window in the week the same amount
  rather than reordering days; it still surfaces in the number shown to the
  coach/UI.
- **weather_score** is 0.5 (neutral) whenever `weather_by_date` is `None`,
  has no entry for that date, or the entry's fields are all `None` — missing
  weather is never treated as a rejection reason or as bad weather. When
  data is present, it averages sub-scores for temperature (mild ~5-18°C
  best), precipitation (less is better), and wind (calmer is better).
- **padel_spacing_score** applies a soft penalty (0.5, not rejection) to
  `SessionType.LONG`/`SessionType.QUALITY` windows on the day immediately
  after `preferences.padel_weekday`, per docs/PRODUCT_SPEC.md ("avoid hard
  Friday running... after Thursday padel... soft constraints scored by the
  feasibility engine, not inflexible laws"). Neutral (1.0) otherwise,
  including for easy runs.
- **rest_day_preservation_score** softly deprioritizes (0.85, never
  rejects) Monday when `preferences.preserve_rest_day` is true, as a
  practical proxy for "keep one day per week free of structured training"
  immediately following the preferred long-run weekend — this module only
  ever scores one session-window request at a time and has no visibility
  into which other days already have sessions placed, so a stronger
  cross-week "don't use every single day" rule belongs to the orchestrator
  that calls this module once per session and can see the whole week's
  picks.

`session_type` is not part of the caller-facing contract described in the
build brief's example signature, but scoring "long-run day preference" and
"hard efforts after padel" both require knowing what kind of session is
being scheduled — it is added as an optional keyword (default
`SessionType.EASY`) so the module still works with the minimal call shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sophie.domain.calendar_types import BusyInterval
from sophie.domain.coach_types import CalendarWindow, RejectedWindow
from sophie.domain.training_block import SessionType

_CANDIDATE_STEP_MINUTES = 30
_MINUTES_PER_DAY = 24 * 60
_WEEKEND_EARLIEST_TIME = time(7, 0)
_WEEKEND_WEEKDAY_INDICES = (5, 6)  # Saturday, Sunday (Monday == 0)

_LOAD_STATUS_SCORE = {
    "low": 1.0,
    "typical": 0.85,
    "elevated": 0.55,
    "very_elevated": 0.3,
}
_RECOVERY_STATUS_SCORE = {
    "normal": 1.0,
    "watch": 0.6,
    "concern": 0.3,
}
_DEFAULT_STATUS_SCORE = 0.7  # unrecognized status string: neutral-ish, never crash

_LONG_RUN_RANK_SCORES = (1.0, 0.75, 0.5)  # index 0/1/2 of long_run_weekday_preference
_LONG_RUN_LISTED_LATER_SCORE = 0.3
_LONG_RUN_UNLISTED_SCORE = 0.15

_PADEL_PENALTY_SCORE = 0.5
_REST_DAY_PENALTY_SCORE = 0.85

_WEIGHT_DAY_PREFERENCE = 0.40
_WEIGHT_LOAD_RECOVERY = 0.20
_WEIGHT_WEATHER = 0.15
_WEIGHT_PADEL_SPACING = 0.15
_WEIGHT_REST_DAY = 0.10


@dataclass(frozen=True)
class SchedulingPreferences:
    """Mirrors the relevant `UserConfig` scheduling fields
    (`src/sophie/db/models/core.py`) as a plain, DB-free dataclass."""

    dropoff_start: str  # "HH:MM"
    dropoff_end: str  # "HH:MM"
    earliest_weekday_session: str  # "HH:MM"
    latest_session: str  # "HH:MM"
    long_run_weekday_preference: list[str]  # e.g. ["Saturday", "Sunday", "Friday"]
    padel_weekday: int | None  # Mon=0 ... Sun=6
    preserve_rest_day: bool


@dataclass(frozen=True)
class WeatherContext:
    """Minimal per-day weather context. Any/all fields may be `None` when
    unavailable — this module always treats that as neutral, never as a
    rejection reason (docs/PRIVACY.md / docs/PRODUCT_SPEC.md)."""

    temp_c: float | None = None
    precip_mm: float | None = None
    wind_kph: float | None = None
    condition_summary: str | None = None


def compute_feasible_windows(
    week_start: date,
    busy_intervals: list[BusyInterval],
    session_duration_min: int,
    buffer_min: int,
    preferences: SchedulingPreferences,
    training_load_status: str,
    recovery_status: str,
    weather_by_date: dict[date, WeatherContext] | None,
    session_type: SessionType = SessionType.EASY,
) -> tuple[list[CalendarWindow], list[RejectedWindow]]:
    """Returns (feasible windows ranked by nothing in particular — sort by
    `rank_score` yourself if you want a top pick, since different callers
    may want different tie-breaking, rejected windows) for one candidate
    session across the 7 days starting `week_start` (a Monday)."""

    earliest_weekday_time = _parse_hhmm(preferences.earliest_weekday_session)
    latest_session_time = _parse_hhmm(preferences.latest_session)
    dropoff_end_time = _parse_hhmm(preferences.dropoff_end)

    load_recovery_score = _clamp(
        (
            _LOAD_STATUS_SCORE.get(training_load_status, _DEFAULT_STATUS_SCORE)
            + _RECOVERY_STATUS_SCORE.get(recovery_status, _DEFAULT_STATUS_SCORE)
        )
        / 2
    )

    feasible: list[CalendarWindow] = []
    rejected: list[RejectedWindow] = []

    for day_offset in range(7):
        day_date = week_start + timedelta(days=day_offset)
        weekday_idx = day_date.weekday()  # Mon=0 ... Sun=6
        weekday_name = day_date.strftime("%A")
        is_weekend = weekday_idx in _WEEKEND_WEEKDAY_INDICES
        earliest_allowed = _WEEKEND_EARLIEST_TIME if is_weekend else earliest_weekday_time

        weather = (weather_by_date or {}).get(day_date)
        weather_score, weather_note = _weather_score(weather)
        padel_score, padel_note = _padel_spacing_score(
            weekday_idx, session_type, preferences.padel_weekday
        )
        rest_day_score, rest_day_note = _rest_day_score(weekday_idx, preferences.preserve_rest_day)

        for minute_of_day in range(0, _MINUTES_PER_DAY, _CANDIDATE_STEP_MINUTES):
            candidate_start = time(minute_of_day // 60, minute_of_day % 60)
            start_dt = datetime.combine(day_date, candidate_start)
            session_end_dt = start_dt + timedelta(minutes=session_duration_min)
            block_end_dt = start_dt + timedelta(minutes=session_duration_min + buffer_min)

            if candidate_start < earliest_allowed:
                rejected.append(
                    RejectedWindow(
                        date=day_date,
                        start=candidate_start,
                        end=session_end_dt.time(),
                        reason_code="outside_allowed_hours",
                    )
                )
                continue

            if session_end_dt.date() != day_date or session_end_dt.time() > latest_session_time:
                rejected.append(
                    RejectedWindow(
                        date=day_date,
                        start=candidate_start,
                        end=min(session_end_dt.time(), time(23, 59)),
                        reason_code="after_latest_session_time",
                    )
                )
                continue

            if _overlaps_any_busy(start_dt, block_end_dt, busy_intervals):
                rejected.append(
                    RejectedWindow(
                        date=day_date,
                        start=candidate_start,
                        end=session_end_dt.time(),
                        reason_code="busy_calendar",
                    )
                )
                continue

            day_preference_score = _day_preference_score(
                weekday_idx=weekday_idx,
                is_weekend=is_weekend,
                candidate_start=candidate_start,
                session_type=session_type,
                long_run_weekday_preference=preferences.long_run_weekday_preference,
                dropoff_end_time=dropoff_end_time,
                latest_session_time=latest_session_time,
            )

            rank_score = _clamp(
                _WEIGHT_DAY_PREFERENCE * day_preference_score
                + _WEIGHT_LOAD_RECOVERY * load_recovery_score
                + _WEIGHT_WEATHER * weather_score
                + _WEIGHT_PADEL_SPACING * padel_score
                + _WEIGHT_REST_DAY * rest_day_score
            )

            notes = [n for n in (weather_note, padel_note, rest_day_note) if n]

            feasible.append(
                CalendarWindow(
                    date=day_date,
                    start=candidate_start,
                    end=session_end_dt.time(),
                    weekday_name=weekday_name,
                    rank_score=round(rank_score, 4),
                    notes=notes,
                )
            )

    return feasible, rejected


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _day_preference_score(
    *,
    weekday_idx: int,
    is_weekend: bool,
    candidate_start: time,
    session_type: SessionType,
    long_run_weekday_preference: list[str],
    dropoff_end_time: time,
    latest_session_time: time,
) -> float:
    weekday_component = _weekday_component(
        weekday_idx, is_weekend, session_type, long_run_weekday_preference
    )
    time_of_day_component = _time_of_day_component(
        candidate_start, is_weekend, dropoff_end_time, latest_session_time
    )
    return _clamp(0.6 * weekday_component + 0.4 * time_of_day_component)


def _weekday_component(
    weekday_idx: int,
    is_weekend: bool,
    session_type: SessionType,
    long_run_weekday_preference: list[str],
) -> float:
    if session_type == SessionType.LONG:
        weekday_name = _WEEKDAY_NAMES[weekday_idx]
        normalized_preference = [d.strip().lower() for d in long_run_weekday_preference]
        if weekday_name.lower() in normalized_preference:
            rank = normalized_preference.index(weekday_name.lower())
            if rank < len(_LONG_RUN_RANK_SCORES):
                return _LONG_RUN_RANK_SCORES[rank]
            return _LONG_RUN_LISTED_LATER_SCORE
        return _LONG_RUN_UNLISTED_SCORE
    return 0.7 if is_weekend else 0.55


_WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _time_of_day_component(
    candidate_start: time, is_weekend: bool, dropoff_end_time: time, latest_session_time: time
) -> float:
    if is_weekend:
        return 0.75

    post_dropoff_end = _add_minutes(dropoff_end_time, 120)
    lunch_start, lunch_end = time(11, 30), time(13, 30)
    after_work_start = time(16, 0)

    if dropoff_end_time <= candidate_start < post_dropoff_end:
        return 1.0
    if lunch_start <= candidate_start < lunch_end:
        return 0.8
    if after_work_start <= candidate_start <= latest_session_time:
        return 0.65
    return 0.45


def _weather_score(weather: WeatherContext | None) -> tuple[float, str | None]:
    if weather is None:
        return 0.5, None

    sub_scores: list[float] = []
    if weather.temp_c is not None:
        sub_scores.append(_temp_sub_score(weather.temp_c))
    if weather.precip_mm is not None:
        sub_scores.append(_precip_sub_score(weather.precip_mm))
    if weather.wind_kph is not None:
        sub_scores.append(_wind_sub_score(weather.wind_kph))

    if not sub_scores:
        return 0.5, None

    score = sum(sub_scores) / len(sub_scores)
    note = None
    if score < 0.5 and weather.condition_summary:
        note = f"Weather may be tough: {weather.condition_summary}"
    return score, note


def _temp_sub_score(temp_c: float) -> float:
    if 5.0 <= temp_c <= 18.0:
        return 1.0
    if -2.0 <= temp_c < 5.0 or 18.0 < temp_c <= 24.0:
        return 0.7
    return 0.4


def _precip_sub_score(precip_mm: float) -> float:
    if precip_mm <= 0.2:
        return 1.0
    if precip_mm <= 2.0:
        return 0.7
    return 0.3


def _wind_sub_score(wind_kph: float) -> float:
    if wind_kph <= 15.0:
        return 1.0
    if wind_kph <= 30.0:
        return 0.7
    return 0.4


def _padel_spacing_score(
    weekday_idx: int, session_type: SessionType, padel_weekday: int | None
) -> tuple[float, str | None]:
    if padel_weekday is None:
        return 1.0, None
    day_after_padel = (padel_weekday + 1) % 7
    if weekday_idx == day_after_padel and session_type in (SessionType.LONG, SessionType.QUALITY):
        return (
            _PADEL_PENALTY_SCORE,
            "Day after padel — soft penalty for scheduling a hard effort here.",
        )
    return 1.0, None


def _rest_day_score(weekday_idx: int, preserve_rest_day: bool) -> tuple[float, str | None]:
    if preserve_rest_day and weekday_idx == 0:  # Monday
        return (
            _REST_DAY_PENALTY_SCORE,
            "Monday kept lighter where practical, to preserve a rest day.",
        )
    return 1.0, None


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def _parse_hhmm(value: str) -> time:
    hour_str, _, minute_str = value.partition(":")
    return time(int(hour_str), int(minute_str))


def _add_minutes(base: time, minutes: int) -> time:
    dummy_date = date(2000, 1, 1)
    result = datetime.combine(dummy_date, base) + timedelta(minutes=minutes)
    if result.date() != dummy_date:
        return time(23, 59)
    return result.time()


def _overlaps_any_busy(
    block_start: datetime, block_end: datetime, busy_intervals: list[BusyInterval]
) -> bool:
    for busy in busy_intervals:
        busy_start = busy.start.replace(tzinfo=None) if busy.start.tzinfo else busy.start
        busy_end = busy.end.replace(tzinfo=None) if busy.end.tzinfo else busy.end
        if block_start < busy_end and block_end > busy_start:
            return True
    return False


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
