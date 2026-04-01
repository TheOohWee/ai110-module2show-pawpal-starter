import json
from datetime import date, time
from pathlib import Path

import streamlit as st
from typing import cast

from pawpal_system import (
    Owner,
    Pet,
    Scheduler,
    Task,
    TaskStatusFilter,
    filter_tasks_with_pets,
    sort_pairs_by_preferred_time,
    sort_pairs_by_urgency,
)

_DATA_FILE = Path(__file__).resolve().parent / "pawpal_data.json"


def _task_to_json(t: Task) -> dict:
    return {
        "description": t.description,
        "time_minutes": t.time_minutes,
        "frequency": t.frequency,
        "completed": t.completed,
        "duration_minutes": t.duration_minutes,
        "priority": t.priority,
        "weekly_weekday": t.weekly_weekday,
        "due_date": t.due_date.isoformat() if t.due_date is not None else None,
    }


def _task_from_json(d: dict) -> Task:
    dd = d.get("due_date")
    return Task(
        description=d["description"],
        time_minutes=d.get("time_minutes"),
        frequency=d["frequency"],
        completed=d.get("completed", False),
        duration_minutes=int(d.get("duration_minutes", 30)),
        priority=int(d.get("priority", 1)),
        weekly_weekday=d.get("weekly_weekday"),
        due_date=date.fromisoformat(dd) if dd else None,
    )


def _load_owner_from_disk() -> Owner:
    if not _DATA_FILE.is_file():
        return Owner()
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Owner()
    pets: list[Pet] = []
    for pd in raw.get("pets", []):
        tasks = [_task_from_json(td) for td in pd.get("tasks", [])]
        pets.append(
            Pet(
                name=pd["name"],
                species=pd["species"],
                age=int(pd["age"]),
                tasks=tasks,
            )
        )
    return Owner(pets=pets)


def _save_owner_to_disk(owner: Owner) -> None:
    payload = {
        "pets": [
            {
                "name": p.name,
                "species": p.species,
                "age": p.age,
                "tasks": [_task_to_json(t) for t in p.tasks],
            }
            for p in owner.pets
        ]
    }
    _DATA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clock(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("PawPal+")
st.caption("Pet care tasks and a daily schedule. Data is stored locally next to this app.")

if "owner" not in st.session_state:
    st.session_state.owner = _load_owner_from_disk()

owner = st.session_state.owner

st.subheader("Pets")

pc1, pc2, pc3 = st.columns(3)
with pc1:
    pet_name = st.text_input("Name", value="Mochi")
with pc2:
    species = st.selectbox("Species", ["dog", "cat", "other"], key="add_pet_species")
with pc3:
    age = st.number_input("Age (years)", min_value=0, max_value=40, value=2)

if st.button("Add pet", key="add_pet_btn"):
    name = (pet_name or "").strip() or "Unnamed"
    owner.pets.append(Pet(name=name, species=species, age=int(age)))
    _save_owner_to_disk(owner)
    st.success(f"Added {name}.")
    st.rerun()

if owner.pets:
    for p in owner.pets:
        st.markdown(f"**{p.name}** · {p.species} · age {p.age} · {len(p.tasks)} task(s)")
else:
    st.info("Add a pet to get started.")

st.divider()

st.subheader("Tasks")

if not owner.pets:
    st.warning("Add a pet first.")
else:
    _add_pet_idx = st.selectbox(
        "Pet",
        options=list(range(len(owner.pets))),
        format_func=lambda i: f"{owner.pets[i].name} ({owner.pets[i].species})",
        key="add_task_pet_idx",
    )
    pet_for_task = owner.pets[_add_pet_idx]

    tc1, tc2 = st.columns(2)
    with tc1:
        description = st.text_input("Description", value="Morning walk")
    with tc2:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as_needed"])

    weekly_day: int | None = None
    if frequency == "weekly":
        _day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        weekly_day = _day_names.index(
            st.selectbox(
                "Weekly on",
                _day_names,
                index=date.today().weekday(),
                key="task_weekly_day",
            )
        )

    ac1, ac2 = st.columns(2)
    with ac1:
        duration_minutes = st.number_input(
            "Duration (minutes)", min_value=1, max_value=240, value=30
        )
    with ac2:
        priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        _priority_value = {"low": 1, "medium": 2, "high": 3}[priority_label]

    use_pref = st.checkbox("Preferred start time")
    pref_minutes: int | None = None
    if use_pref:
        pref_time = st.time_input("Start time", value=time(8, 0))
        pref_minutes = pref_time.hour * 60 + pref_time.minute

    if st.button("Add task", key="add_task_btn"):
        _due = date.today() if frequency in ("daily", "weekly") else None
        pet_for_task.tasks.append(
            Task(
                description=description,
                time_minutes=pref_minutes,
                frequency=frequency,
                duration_minutes=int(duration_minutes),
                priority=_priority_value,
                weekly_weekday=weekly_day,
                due_date=_due,
            )
        )
        _save_owner_to_disk(owner)
        st.success("Task added.")
        st.rerun()

    st.markdown("#### Task list")
    _f1, _f2, _f3 = st.columns(3)
    with _f1:
        filter_pet_opt = st.selectbox(
            "Pet filter",
            ["All pets"] + [p.name for p in owner.pets],
            key="task_filter_pet",
        )
    with _f2:
        filter_status = st.selectbox(
            "Status",
            ["all", "open", "done"],
            format_func=lambda x: {"all": "All", "open": "Open only", "done": "Done only"}[x],
            key="task_filter_status",
        )
    with _f3:
        sort_mode = st.selectbox(
            "Sort by",
            ["preferred_time", "urgency", "description"],
            format_func=lambda x: {
                "preferred_time": "Preferred time",
                "urgency": "Urgency",
                "description": "Description (A–Z)",
            }[x],
            key="task_sort_mode",
        )

    _pet_filter: Pet | None = None
    if filter_pet_opt != "All pets":
        _pet_filter = next(p for p in owner.pets if p.name == filter_pet_opt)

    _pairs = filter_tasks_with_pets(
        owner, pet=_pet_filter, status=cast(TaskStatusFilter, filter_status)
    )
    _pairs_for_order = list(_pairs)
    _scheduler = Scheduler(owner=owner)
    _ref_today = date.today()

    if sort_mode == "preferred_time":
        _pairs = sort_pairs_by_preferred_time(_pairs)
    elif sort_mode == "urgency":
        if filter_status == "open":
            _sched_ordered = _scheduler.sortTasksByPriority(reference_date=_ref_today)
            _allowed_pairs = {(id(p), id(t)) for p, t in _pairs_for_order}
            _pairs = [
                (p, t)
                for p, t in _sched_ordered
                if (id(p), id(t)) in _allowed_pairs
            ]
        else:
            _pairs = sort_pairs_by_urgency(_pairs)
    else:
        _pairs = sorted(_pairs, key=lambda pt: pt[1].description.lower())

    _pref_warnings = _scheduler.preferred_time_conflict_warnings()
    if _pref_warnings:
        st.warning("Some preferred times overlap. Adjust times or use Generate schedule to shift tasks.")
        for line in _pref_warnings:
            st.markdown(f"- {line}")
    else:
        st.success("No overlapping preferred times.")

    if not _pairs:
        st.caption("No tasks match the current filters.")
    else:
        _day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        _sort_label = {
            "preferred_time": "Preferred time",
            "urgency": "Urgency (open tasks use scheduler order)",
            "description": "Description (A–Z)",
        }[sort_mode]
        st.caption(f"{len(_pairs)} row(s) · {_sort_label}")
        st.table(
            [
                {
                    "pet": pet.name,
                    "description": task.description,
                    "status": "done" if task.completed else "open",
                    "duration_min": task.duration_minutes,
                    "priority": task.priority,
                    "frequency": task.frequency,
                    "weekly_on": _day_names[task.weekly_weekday]
                    if task.frequency.lower() == "weekly" and task.weekly_weekday is not None
                    else "—",
                    "preferred": _clock(task.time_minutes)
                    if task.time_minutes is not None
                    else "—",
                    "due_date": task.due_date.isoformat() if task.due_date is not None else "—",
                }
                for pet, task in _pairs
            ]
        )

    with st.expander("Mark task complete"):
        _mark_idx = st.selectbox(
            "Pet",
            options=list(range(len(owner.pets))),
            format_func=lambda i: owner.pets[i].name,
            key="mark_pet",
        )
        _mp = owner.pets[_mark_idx]
        _open_on_pet = [t for t in _mp.tasks if not t.completed]
        if not _open_on_pet:
            st.caption("No open tasks for this pet.")
        else:
            _mt = st.selectbox(
                "Task",
                _open_on_pet,
                format_func=lambda t: t.description,
                key="mark_task",
            )
            if st.button("Mark complete", key="mark_done_btn"):
                _freq = _mt.frequency.lower().strip()
                _mt.mark_complete(pet=_mp)
                _save_owner_to_disk(owner)
                if _freq in ("daily", "weekly"):
                    st.success("Completed. Next occurrence added.")
                else:
                    st.success("Marked complete.")
                st.rerun()

st.divider()

st.subheader("Schedule")

_use_today = st.checkbox("Only include tasks for today's weekday", value=True, key="sched_use_today")
_sched_weekday: int | None = date.today().weekday() if _use_today else None
if _use_today:
    st.caption(f"Today: {date.today().strftime('%A')}")

if st.button("Generate schedule"):
    if not owner.get_all_tasks():
        st.warning("Add at least one task first.")
    else:
        scheduler = Scheduler(owner=owner)
        plan = scheduler.generateOptimizedSchedule(
            weekday=_sched_weekday, reference_date=date.today()
        )
        plan.sort(key=lambda row: row[2])
        _plan_warn = scheduler.plan_conflict_warnings(plan)
        if _plan_warn:
            st.warning("The plan has overlapping slots.")
            for line in _plan_warn:
                st.markdown(f"- {line}")
        if not plan:
            st.info("Nothing to schedule in the current window, or no tasks apply today.")
        else:
            rows = []
            for pet, task, slot_start in plan:
                need = task.total_block_minutes()
                slot_end = slot_start + need
                rows.append(
                    {
                        "start": _clock(slot_start),
                        "end": _clock(slot_end),
                        "pet": pet.name,
                        "task": task.description,
                    }
                )
            if not _plan_warn:
                st.success("Schedule generated (07:00–22:00, includes buffers).")
            else:
                st.caption("Review overlaps above.")
            st.table(rows)
