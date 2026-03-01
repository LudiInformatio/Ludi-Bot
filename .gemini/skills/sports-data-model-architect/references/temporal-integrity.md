# Temporal Integrity Rules

## Goals
- Prevent feature leakage from future games/events.
- Preserve correct team/entity state at event time.
- Ensure backtests simulate information available at decision time.

## Core checks
- Join logs and features with explicit `event_date <= as_of_date` rules.
- Ensure no feature timestamp occurs after label timestamp.
- Avoid implicit "latest row" joins without date predicates.

## High-risk patterns
- Joining player dimension rows without effective dates.
- Using current-team assignment for historical game rows.
- Deriving rolling windows that include current label game.

## Safe patterns
- Keep historical fact tables immutable and date-stamped.
- Use as-of joins with deterministic tie-breakers.
- Materialize feature windows with explicit lower/upper bounds.

## NBA-specific reminders
- Trade periods require date-aware team assignment.
- DNP/VOID outcomes must be handled before model metrics.
- Postponed/rescheduled games can break naive date assumptions.
