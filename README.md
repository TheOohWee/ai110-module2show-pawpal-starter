# PawPal+

**PawPal+** is a pet-care planning assistant: a Python domain model plus a Streamlit UI that helps an owner track tasks per pet and build a **non-overlapping daily schedule** from priorities, preferred times, due dates, and recurring rules.

---

## Features

These capabilities map directly to the algorithms and data structures in `pawpal_system.py` and the wiring in `app.py`:

| Feature | What it does |
|--------|----------------|
| **Urgency scoring** | Each open task gets a numeric score from `Task.giveUrgencyScore()` (priority scaled by 10 plus a small **frequency** bonus: daily > weekly > as_needed). Completed tasks score zero so they drop out of scheduling order. |
| **Sorting by preferred time** | `sort_pairs_by_preferred_time()` orders tasks with a **preferred start** (`time_minutes` from midnight) before those without; within each group, sorts by time, then pet name and description for stable ties. |
| **Sorting by urgency** | `sort_pairs_by_urgency()` orders by descending urgency and priority so the UI and previews match scheduler intent. When the task list is filtered to **open only**, the app can align order with `Scheduler.sortTasksByPriority()`. |
| **Scheduler ordering** | `sortTasksByPriority()` considers only **incomplete** tasks that are **due on** the chosen `reference_date`, optionally filtered to a **calendar weekday** so weekly tasks appear only on their day. Tasks are sorted by urgency then priority (descending). |
| **Greedy day packing** | `generateOptimizedSchedule()` walks tasks in that order. For each task it tries the **preferred** slot if the full block (duration + buffer) fits in the day window and does not overlap already placed blocks; otherwise it uses **first-fit** via `findAvailableSlot()` over merged gaps in `[day_start, day_end)`. |
| **Time buffers** | `getRequiredTimeBuffer()` adds slack around each block; `total_block_minutes()` includes buffer for conflict checks and placement. |
| **Conflict warnings (preferences)** | `detect_preferred_time_conflicts()` compares **half-open** minute intervals `[start, end)` for all open tasks with a preferred time and reports overlaps (touching endpoints do not count). The Streamlit app surfaces these as readable lines. |
| **Conflict warnings (plan)** | After building a concrete plan, `detect_plan_conflicts()` / `plan_conflict_warnings()` validate assigned starts the same way—useful if the plan is edited or inspected. |
| **Due date gating** | Tasks with a `due_date` are only eligible when `due_date <= reference_date`, so future-dated work stays off today’s plan until appropriate. |
| **Weekly recurrence** | For `frequency="weekly"`, optional `weekly_weekday` (Monday–Sunday) restricts which day a task is considered; pairs with `Scheduler` weekday filtering. |
| **Daily / weekly completion** | `mark_complete()` on a pet’s task list replaces **daily** or **weekly** rows with a **new open task** for the next due day (`+1` or `+7` days); other frequencies simply mark complete. |
| **Owner-level views** | `Owner.get_all_tasks()`, `iter_tasks_with_pet()`, and `filter_tasks()` (by status and pet name) support flat lists and the Streamlit filters. |

---

## 📸 Demo

Click the image to open the full-size screenshot in a new tab.

<a href="/course_images/ai110/your_screenshot_name.png" target="_blank"><img src='/course_images/ai110/your_screenshot_name.png' title='PawPal App' width='' alt='PawPal App' class='center-block' /></a>

---

## Quick start

### Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the Streamlit app

```bash
streamlit run app.py
```

Add pets and tasks, filter and sort the task table, review **preferred-time** warnings, then **Generate schedule** for a packed day plan (default window 07:00–22:00).

### Run the CLI sample

```bash
python main.py
```

Prints an optimized schedule for the sample data in `main.py`.

### Run tests

```bash
python -m pytest tests/ -v
```

---

## Project layout

| Path | Purpose |
|------|---------|
| `pawpal_system.py` | `Task`, `Pet`, `Owner`, `Scheduler`, `TimeRangeConflict`, and module helpers (sorting, conflict detection, filtering). |
| `app.py` | Streamlit UI: session state, task CRUD, filters, conflict warnings, schedule generation. |
| `main.py` | CLI demo with sample pets and tasks. |
| `tests/test_pawpal.py` | `pytest` coverage for scheduling, recurrence, conflicts, and edge cases. |
| `uml.mmd` / `uml_final.mmd` | Mermaid UML; `uml_final.png` is an exported diagram. |

---

## Architecture notes

- **`Task`** — Care item: description, optional preferred time, frequency, duration, priority, completion, optional weekly weekday and due date.
- **`Pet`** — Holds a list of `Task` instances; species/age drive care hints and health notes.
- **`Owner`** — Aggregates pets; exposes flattened task views and filtering.
- **`Scheduler`** — Holds an `Owner`; filters eligible tasks, sorts by urgency/priority, assigns non-overlapping times in a configurable day window.

For deeper behavior (tradeoffs, non-optimal greedy packing), see `reflection.md`.

---

## Testing and confidence

The suite in `tests/test_pawpal.py` exercises completion and **daily/weekly/as_needed** behavior, **owner filtering**, **preferred-time** and **urgency** sorting, **weekday** and **due_date** gating, **preferred-time and plan** conflict detection, **optimized schedule** generation, and utilities such as warning strings and `findAvailableSlot`.

**Reliability (based on current tests):** strong coverage for domain and scheduling logic; the Streamlit layer is not automated here—add integration or UI tests to raise end-to-end confidence further.
