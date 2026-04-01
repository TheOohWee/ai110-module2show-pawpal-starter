from datetime import date, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task, sort_pairs_by_preferred_time


def _clock(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _print_task_lines(pairs: list[tuple[Pet, Task]], title: str) -> None:
    print(title)
    print("-" * 64)
    if not pairs:
        print("(none)")
    else:
        for pet, task in pairs:
            pref = _clock(task.time_minutes) if task.time_minutes is not None else "—"
            state = "done" if task.completed else "open"
            due = task.due_date.isoformat() if task.due_date is not None else "—"
            print(
                f"  [{state:4}] {pet.name:8}  {task.description:20}  pref {pref}  due {due}"
            )
    print()


def main() -> None:
    today = date.today()
    dog = Pet(name="Milo", species="dog", age=4, tasks=[])
    cat = Pet(name="Luna", species="cat", age=2, tasks=[])

    # Append tasks out of preferred-time order. Daily/weekly get `due_date=today` so they schedule today.
    dog.tasks.append(Task("Evening brush", 21 * 60, "daily", due_date=today))
    dog.tasks.append(Task("Dinner & meds", 19 * 60 + 30, "daily", due_date=today))
    dog.tasks.append(Task("Morning walk", 8 * 60, "daily", due_date=today))

    cat.tasks.append(Task("Litter check", 17 * 60, "as_needed"))
    cat.tasks.append(Task("Lunch play", 12 * 60 + 15, "daily", due_date=today))
    cat.tasks.append(Task("Breakfast", 7 * 60 + 45, "daily", due_date=today))

    # Daily + pet: replaces task; next due = today + timedelta(days=1).
    dog.tasks[0].mark_complete(pet=dog)
    # as_needed: no pet → stays a completed row (no new instance).
    cat.tasks[0].mark_complete()

    owner = Owner(pets=[cat, dog])

    print("Recurring completion: Milo’s daily “Evening brush” → new row due", today + timedelta(days=1))
    print("(computed with date.today() + timedelta(days=1) inside Task.mark_complete)\n")

    print("Filtered & sorted task views (tasks were added out of time order)\n")

    open_by_time = sort_pairs_by_preferred_time(owner.filter_tasks(status="open"))
    _print_task_lines(open_by_time, "Open tasks — filter: status=open, sort: preferred time")

    done_only = owner.filter_tasks(status="done")
    _print_task_lines(done_only, "Done tasks — filter: status=done")

    milo_tasks = sort_pairs_by_preferred_time(
        owner.filter_tasks(status="all", pet_name="Milo")
    )
    _print_task_lines(milo_tasks, 'All Milo tasks — filter: pet_name="Milo", sort: preferred time')

    luna_open = sort_pairs_by_preferred_time(
        owner.filter_tasks(status="open", pet_name="luna")
    )
    _print_task_lines(
        luna_open,
        'Luna open tasks — filter: pet_name="luna", status=open, sort: time',
    )

    scheduler = Scheduler(owner=owner)
    plan = scheduler.generateOptimizedSchedule(reference_date=today)
    plan.sort(key=lambda row: row[2])

    print("Today's schedule (tasks gated by reference_date=today; sorted by slot start)")
    print("-" * 64)
    for pet, task, slot_start in plan:
        need = task.total_block_minutes()
        slot_end = slot_start + need
        print(f"{_clock(slot_start)} – {_clock(slot_end)}  {pet.name}: {task.description}")


if __name__ == "__main__":
    main()
