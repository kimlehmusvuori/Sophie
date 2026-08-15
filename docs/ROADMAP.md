# Sophie — Roadmap

## Now (this build)

See `docs/PRODUCT_SPEC.md` and the acceptance criteria in the build brief — Priorities 1–6.

## Future — explicitly deferred, not current blockers

- **Neko Health** (or an equivalent deeper preventive-health assessment) as an optional additional
  clinical/body-composition data source. Do not build a dedicated integration now; the
  provider-independent clinical data model (`clinical_import` / `lab_result` /
  `body_composition_assessment`) is designed so this can be added later without a schema rewrite.
  Evaluate only after existing Apple Health + Avonova + body-composition data has been assessed.
- **Commercial cloud/SaaS**: hosted backend, browser/mobile frontend, user accounts, integrations
  marketplace, subscription billing. Today's architecture (services/domain layer with no
  Streamlit dependency, Postgres-compatible SQLAlchemy models) is deliberately kept ready for this,
  but none of it is built now.
- **Native mobile app.**
- **Automated background synchronization** (today's imports are user-initiated).

## Explicit exclusions — do not build unless the user later reopens these

- Mobility/functional-health analytics (walking asymmetry, double-support time, gait metrics) —
  recognized-but-unused in the Apple Health metric catalogue.
- Shoe-mileage tracking.
- Detailed hydration tracking.
- Daily readiness alerts / daily push notifications.
- Daily mood journaling (WHO-5 biweekly + optional State-of-Mind context only).
- Complex strength programming.
- A complex race-readiness score (would violate "no false precision").
- Clinical diagnosis of any kind.
- Multi-user support / authentication.
- Payments / billing.
- A SaaS admin portal.

If a future request touches one of the items above, treat it as new scope requiring explicit user
sign-off — do not quietly re-add it as a side effect of another change.
