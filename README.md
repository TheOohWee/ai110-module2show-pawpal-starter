# PawPal+ (Module 2 Project)

**PawPal+** is a small Python backend plus a Streamlit shell that helps a pet owner plan care tasks (walks, feeding, meds, enrichment) under time and priority constraints.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Project layout

| Path | Purpose |
|------|---------|
| `pawpal_system.py` | Domain model (`Task`, `Pet`, `Owner`) and `Scheduler` (priority sort + day packing) |
| `main.py` | CLI demo: sample pets/tasks, prints an optimized schedule |
| `app.py` | Streamlit UI starter (wire your scheduler here when ready) |
| `tests/` | `pytest` tests for core behaviors |
| `uml.mmd` | UML source (Mermaid) |

## Backend overview

- **`Task`** — Care item: description, optional preferred time (`time_minutes` from midnight), frequency, duration, priority, and `completed`. Urgency scoring drives ordering; `mark_complete()` sets done.
- **`Pet`** — Name, species, age, and a list of `Task` instances. Species/age inform recommended care hints and health notes.
- **`Owner`** — Holds `Pet` list; exposes flat views of all tasks (with or without pet pairing).
- **`Scheduler`** — Given an `Owner`, considers only incomplete tasks, sorts by urgency/priority, then assigns non-overlapping start times within a day window (default 07:00–22:00), respecting preferred times when they fit.

## Smarter Scheduling

PawPal+ goes beyond a simple priority list:

- **Due dates** — Each task can carry a calendar `due_date`. The scheduler only considers tasks that are due on the chosen planning day (`reference_date`), so future occurrences stay off today’s plan until appropriate.
- **Weekly rules** — For `frequency="weekly"`, optional `weekly_weekday` (Monday–Sunday) limits which calendar day a task appears on, so weekly meds or grooming only show when they apply.
- **Preferred times and conflicts** — Preferred start (`time_minutes`) is honored when it fits the day window and does not overlap another placed block; otherwise the scheduler **first-fits** the task into the next gap. You can detect overlapping *preferences* across open tasks with `detect_preferred_time_conflicts` / `Scheduler.preferred_time_conflict_warnings`, and validate any concrete plan with `detect_plan_conflicts` / `plan_conflict_warnings`.
- **Recurring completion** — Completing a **daily** or **weekly** task that lives on a pet’s list replaces that row with a new open task for the next due day (`today + 1 day` or `today + 7 days`), so the model stays aligned with recurring care.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the CLI demo

```bash
python main.py
```

Prints a sorted daily plan for the sample pets defined in `main.py`.

### Run the Streamlit app

```bash
streamlit run app.py
```

### Run tests

```bash
pytest tests/ -v
```


