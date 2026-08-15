# Sophie — Data Dictionary

All tables live under `profile_id` (single local profile, see `docs/ARCHITECTURE.md`). Full column
definitions are the SQLAlchemy models in `src/sophie/db/models/`; this document is the narrative
index kept in sync with them.

## Core / config

- **profile** — the one local user. `id`, `display_name`, `birth_year`, `sex`, `height_cm`,
  `created_at`.
- **user_config** — editable JSON-backed settings blob + queryable key fields: goals (race, race
  date, weight goal), planning prefs (max runs/week, padel day, schedule windows), nutrition
  preferences, explicit exclusions, free-text Sophie memory. One row per profile; versioned via
  `updated_at`.
- **family_history_item** — optional, private. `category` (cardiovascular / diabetes /
  autoimmune_inflammatory / other), `note`, `entered_at`. Context only — see
  `docs/HEALTH_LOGIC_AND_SAFETY.md`.

## Import plumbing

- **import_manifest** — `id`, `profile_id`, `source_type` (apple_health/sports_tracker/clinical/
  body_composition), `content_fingerprint` (sha256 of the source stream), `importer_version`,
  `started_at`, `finished_at`, `state` (pending/success/partial/failed), `records_processed`,
  `duplicates_detected`, `warnings` (JSON list of safe strings), `error_summary`.
- **apple_health_metric_catalog** — `record_type` (HKQuantityTypeIdentifier...), `friendly_name`,
  `first_seen_at`, `last_seen_at`, `approx_record_count`, `unit`, `status` (actively_used /
  stored_aggregate / recognized_unused / deliberately_excluded), `sophie_use` (free text).

## Workouts

- **canonical_workout** — one row per real-world activity. `id` (UUID), `profile_id`,
  `activity_type`, `start_at`, `end_at`, `duration_s`, `distance_m`, `avg_hr`, `max_hr`, `elevation_gain_m`,
  `avg_pace_s_per_km`, `source_quality` (best available source used for these fields), `notes`.
- **workout_source_provenance** — `canonical_workout_id`, `source_type` (apple_health/
  sports_tracker_fit/sports_tracker_gpx), `source_identifier`, `raw_start_at`, `raw_duration_s`,
  `raw_distance_m`, `matched_confidence` (exact/high/user_confirmed), `import_manifest_id`.

## Daily / weekly derived summaries

- **daily_health_summary** — `profile_id`, `day`, and nullable columns for weight_kg, steps,
  walking_running_distance_m, active_energy_kcal, exercise_minutes, resting_hr, hrv_ms,
  sleep_minutes, sleep_efficiency, respiratory_rate, spo2_pct, wrist_temp_deviation_c, vo2_max,
  daylight_minutes, dietary_energy_kcal, protein_g, carbs_g, fat_g, mindful_minutes,
  headphone_audio_db, environmental_audio_db. All nullable — absence is meaningful (see "no fake
  precision").
- **weekly_summary** — `profile_id`, `week_start`, planned/actual running distance & session
  counts, long-run distance, other-training minutes, and rollups of the daily columns above
  (avg/last-available), `calculation_version`.

## Health intelligence (derived, versioned, evidence-carrying)

- **training_load_summary** — `profile_id`, `week_start`, `status` (low/typical/elevated/
  very_elevated), `evidence` (JSON: contributing sessions + relative-load ratio),
  `calculation_version`, `data_quality`.
- **recovery_summary** — `profile_id`, `day`, `status` (normal/watch/concern`), `signals` (JSON:
  which of RHR/HRV/sleep/respiratory/wrist-temp deviated and by how much vs personal baseline),
  `calculation_version`, `data_quality`.
- **circadian_summary** — `profile_id`, `week_start`, `bedtime_variability_min`,
  `waketime_variability_min`, `sleep_midpoint`, `duration_consistency`, `disrupted_nights`,
  `avg_daylight_minutes`, `calculation_version`.
- **wellbeing_assessment** — `profile_id`, `assessed_at`, `instrument` ("WHO-5"),
  `instrument_version`, `raw_score` (0–25), `percentage_score` (0–100), `answers` (JSON, 5 items).
- **hearing_summary** — `profile_id`, `period_start`, `period_end`, `headphone_avg_db`,
  `environmental_avg_db`, `exposure_events`, `calculation_version`.
- **aerobic_efficiency_point** — `profile_id`, `workout_id`, `week_start`, `pace_s_per_km`,
  `avg_hr`, `efficiency_proxy` (pace/HR ratio, normalized), `comparable_group` (easy/steady),
  `calculation_version`.
- **movement_baseline** — `profile_id`, `week_start`, `avg_daily_steps`, `personal_baseline_steps`,
  `status` (below/at/above personal baseline).

## Weather

- **weather_snapshot** — `profile_id`, `for_date`, `location_name`, `lat_rounded`, `lon_rounded`
  (coarse, user-configured — never derived from GPS routes), `temp_c`, `humidity_pct`,
  `precip_mm`, `wind_kph`, `condition_summary`, `fetched_at`, `provider`.

## Clinical / body composition

- **clinical_import** — `id`, `profile_id`, `provider` (e.g. "Avonova", free text), `source_kind`
  (csv/json/manual/pdf_confirmed), `imported_at`, `user_confirmed` (bool — required true for
  pdf_confirmed before any `lab_result` row is written), `import_manifest_id`.
- **lab_result** — `id`, `profile_id`, `clinical_import_id`, `sample_date`, `test_name` (as
  supplied), `canonical_test_id` (nullable — normalized identifier, e.g. "hba1c", when confidently
  mapped), `value`, `unit`, `reference_low`, `reference_high`, `reference_text` (raw range string
  when not cleanly numeric), `abnormal_flag` (only set if the lab itself supplied it — Sophie
  never invents one), `category` (blood_count/iron/glucose/lipids/liver/kidney/thyroid/
  inflammatory/vitamins/autoimmune/other), `notes`.
- **body_composition_assessment** — `profile_id`, `assessed_at`, `method` (e.g. "DEXA",
  "bioimpedance-InBody", "caliper"), `provider`, `weight_kg`, `body_fat_pct`, `lean_mass_kg`,
  `segmental_json` (nullable), `visceral_metric` (nullable, method-specific — never normalized
  across methods), `notes`.

## Sunday Review / planning

- **manual_checkin** — `profile_id`, `week_start`, `pain_0_10`, `pain_location`,
  `stress_1_5`, `fasting_quality` (good/mixed/poor), `nutrition_quality` (nullable, only asked
  when Apple Health nutrition data is weak), `alcohol` (low/medium/high, nullable), `note`.
- **plan** — `id`, `profile_id`, `week_start`, `state` (proposed/approved/modified/rejected/
  calendar_written/completed/partial/missed), `verdict` (build/repeat/reduce/minimum_viable),
  `reasons` (JSON, ≤3), `conservative_alternative` (JSON), `coach_note`, `llm_used` (bool),
  `validation_notes` (JSON — what the deterministic validator repaired/rejected).
- **session** — `id`, `plan_id`, `date`, `time`, `session_type` (long/quality/easy/padel/other),
  `purpose`, `distance_m` (nullable), `estimated_duration_min`, `note`, `calendar_event_id`
  (nullable, set after write-back).
- **calendar_snapshot** — `profile_id`, `week_start`, `fetched_at`, `busy_intervals` (JSON,
  start/end/all_day only — never titles/attendees), `source` (graph/ics_fallback/mock).
- **decision_log** — `profile_id`, `week_start`, `verdict`, `recommended_plan_ref`,
  `approved_plan_ref`, `actual_result_summary`, `training_load_status`, `data_quality_summary`,
  `coach_note`, `calendar_write_state`, `created_at`. View-only in the UI.

## Provenance convention

Every derived table above carries `calculation_version` (bumped when the formula changes) and,
where relevant, `data_quality` (e.g. `sufficient` / `limited` / `insufficient`). Raw clinical
source documents and provider/reference-range text are preserved verbatim on `lab_result` and
`clinical_import` — never rewritten to a Sophie-invented universal range.
