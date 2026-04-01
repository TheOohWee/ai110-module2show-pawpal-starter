from datetime import date, timedelta

from pawpal_system import (
    Owner,
    Pet,
    Scheduler,
    Task,
    detect_plan_conflicts,
    detect_preferred_time_conflicts,
    format_time_range_conflict_warning,
    filter_tasks_with_pets,
    sort_pairs_by_preferred_time,
    sort_pairs_by_urgency,
)


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", 8 * 60, "daily", completed=False)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    pet = Pet(name="Milo", species="dog", age=4, tasks=[])
    assert len(pet.tasks) == 0
    pet.tasks.append(Task("Dinner", 19 * 60 + 30, "daily"))
    assert len(pet.tasks) == 1


def test_weekly_recurrence_respects_weekday():
    mon_only = Task("Grooming", None, "weekly", weekly_weekday=0)
    assert mon_only.applies_for_weekday(0) is True
    assert mon_only.applies_for_weekday(2) is False
    daily = Task("Walk", 8 * 60, "daily")
    assert daily.applies_for_weekday(6) is True


def test_filter_tasks_by_pet_and_status():
    dog = Pet(name="A", species="dog", age=1, tasks=[Task("w", None, "daily")])
    cat = Pet(name="B", species="cat", age=1, tasks=[Task("c", None, "daily")])
    owner = Owner(pets=[dog, cat])
    dog.tasks[0].mark_complete()
    assert len(filter_tasks_with_pets(owner, status="open")) == 1
    assert len(filter_tasks_with_pets(owner, status="done")) == 1
    assert len(filter_tasks_with_pets(owner, pet=dog, status="all")) == 1


def test_owner_filter_tasks_by_pet_name_case_insensitive():
    dog = Pet(name="Milo", species="dog", age=1, tasks=[Task("walk", None, "daily")])
    owner = Owner(pets=[dog])
    assert len(owner.filter_tasks(pet_name="milo")) == 1
    assert len(owner.filter_tasks(pet_name="MILO ")) == 1
    assert len(owner.filter_tasks(pet_name="Nobody")) == 0


def test_sort_pairs_by_preferred_time_orders_none_last():
    pet = Pet("p", "dog", 1, [])
    t_late = Task("late", 12 * 60, "daily")
    t_none = Task("any", None, "daily")
    t_early = Task("early", 8 * 60, "daily")
    pairs = [(pet, t_none), (pet, t_late), (pet, t_early)]
    ordered = [t.description for _, t in sort_pairs_by_preferred_time(pairs)]
    assert ordered == ["early", "late", "any"]


def test_sort_pairs_by_preferred_time_returns_chronological_order():
    """
    Preferred-time sort is ascending by clock time (minutes from midnight).
    Tasks with a set time_minutes are ordered earliest-first.
    """
    pet = Pet("p", "dog", 1, [])
    pairs = [
        (pet, Task("noon", 12 * 60, "daily")),
        (pet, Task("morning", 8 * 60, "daily")),
        (pet, Task("evening", 18 * 60, "daily")),
    ]
    ordered = sort_pairs_by_preferred_time(pairs)
    times = [t.time_minutes for _, t in ordered]
    assert times == [8 * 60, 12 * 60, 18 * 60]
    assert all(t.time_minutes is not None for _, t in ordered)


def test_detect_preferred_time_conflicts():
    owner = Owner(
        pets=[
            Pet(
                "p",
                "dog",
                1,
                tasks=[
                    Task("a", 8 * 60, "daily", duration_minutes=60),
                    Task("b", 8 * 60 + 30, "daily", duration_minutes=30),
                ],
            )
        ]
    )
    conflicts = detect_preferred_time_conflicts(owner)
    assert len(conflicts) >= 1


def test_detect_plan_conflicts_finds_overlap():
    pet = Pet("p", "dog", 1, [])
    t1 = Task("a", None, "daily", duration_minutes=30)
    t2 = Task("b", None, "daily", duration_minutes=30)
    plan = [(pet, t1, 8 * 60), (pet, t2, 8 * 60 + 15)]
    assert len(detect_plan_conflicts(plan)) == 1


def test_scheduler_weekday_filters_weekly_tasks():
    pet = Pet("p", "dog", 1, tasks=[Task("weekly job", None, "weekly", weekly_weekday=2)])
    sched = Scheduler(owner=Owner(pets=[pet]))
    on_tuesday = sched.sortTasksByPriority(weekday=2)
    on_monday = sched.sortTasksByPriority(weekday=1)
    assert len(on_tuesday) == 1
    assert len(on_monday) == 0


def test_daily_mark_complete_with_pet_advances_due_next_day():
    """
    Recurrence: completing a daily task on a pet replaces it with a new open task
    due the following calendar day (same description/frequency, new due_date).
    """
    d0 = date(2026, 3, 31)
    pet = Pet("p", "dog", 1, [Task("walk", 8 * 60, "daily", due_date=d0)])
    original = pet.tasks[0]
    original.mark_complete(pet=pet, today=d0)
    assert len(pet.tasks) == 1
    assert pet.tasks[0] is not original
    assert pet.tasks[0].completed is False
    assert pet.tasks[0].due_date == d0 + timedelta(days=1)
    assert pet.tasks[0].description == "walk"
    assert pet.tasks[0].frequency.lower().strip() == "daily"


def test_weekly_mark_complete_with_pet_advances_due_by_one_week():
    d0 = date(2026, 3, 30)
    pet = Pet(
        "p",
        "dog",
        1,
        [Task("groom", None, "weekly", weekly_weekday=0, due_date=d0)],
    )
    pet.tasks[0].mark_complete(pet=pet, today=d0)
    assert pet.tasks[0].due_date == d0 + timedelta(days=7)


def test_scheduler_skips_tasks_with_future_due_date():
    far = date(2099, 1, 1)
    pet = Pet("p", "dog", 1, [Task("future", 8 * 60, "daily", due_date=far)])
    sched = Scheduler(owner=Owner(pets=[pet]))
    assert sched.sortTasksByPriority(reference_date=date.today()) == []


def test_scheduler_preferred_time_conflict_warnings_are_non_fatal_strings():
    """
    Conflict detection: duplicate preferred start times on open tasks produce
    Scheduler warnings and non-empty conflict records (overlapping time blocks).
    """
    dog = Pet(
        "Milo",
        "dog",
        4,
        tasks=[
            Task("Morning walk", 8 * 60, "daily"),
            Task("Yard break", 8 * 60, "daily"),
        ],
    )
    owner = Owner(pets=[dog])
    sched = Scheduler(owner=owner)
    conflicts = detect_preferred_time_conflicts(owner)
    assert len(conflicts) >= 1
    warnings = sched.preferred_time_conflict_warnings()
    assert len(warnings) >= 1
    assert "Morning walk" in warnings[0] and "Yard break" in warnings[0]


def test_format_time_range_conflict_warning_includes_times():
    from pawpal_system import TimeRangeConflict

    c = TimeRangeConflict(
        pet_a="A",
        task_a="x",
        start_a=8 * 60,
        end_a=9 * 60,
        pet_b="B",
        task_b="y",
        start_b=8 * 60 + 30,
        end_b=10 * 60,
    )
    s = format_time_range_conflict_warning(c)
    assert "08:00" in s and "A" in s and "B" in s


def test_mark_complete_as_needed_with_pet_marks_done_no_replacement():
    d0 = date(2026, 3, 31)
    pet = Pet("p", "dog", 1, [Task("extra", None, "as_needed", due_date=d0)])
    t = pet.tasks[0]
    t.mark_complete(pet=pet, today=d0)
    assert pet.tasks[0] is t
    assert t.completed is True


def test_weekly_with_null_weekday_applies_all_calendar_days():
    t = Task("groom", None, "weekly", weekly_weekday=None)
    for wd in range(7):
        assert t.applies_for_weekday(wd) is True


def test_adjacent_preferred_windows_do_not_conflict():
    """Half-open [start, end): touching endpoints are not an overlap."""
    dur = 30
    pet = Pet("p", "dog", 1, [])
    t_a = Task("a", 8 * 60, "daily", duration_minutes=dur)
    t_b = Task("b", 8 * 60 + t_a.total_block_minutes(), "daily", duration_minutes=dur)
    owner = Owner(pets=[Pet("p", "dog", 1, tasks=[t_a, t_b])])
    assert detect_preferred_time_conflicts(owner) == []


def test_adjacent_plan_slots_do_not_conflict():
    pet = Pet("p", "dog", 1, [])
    t1 = Task("a", None, "daily", duration_minutes=30)
    t2 = Task("b", None, "daily", duration_minutes=30)
    end1 = 8 * 60 + t1.total_block_minutes()
    plan = [(pet, t1, 8 * 60), (pet, t2, end1)]
    assert detect_plan_conflicts(plan) == []


def test_sort_pairs_by_preferred_time_tie_breaks_pet_then_description():
    pet_a = Pet("alpha", "dog", 1, [])
    pet_z = Pet("zebra", "dog", 1, [])
    t_b = Task("brush", 9 * 60, "daily")
    t_a = Task("apple", 9 * 60, "daily")
    pairs = [(pet_z, t_b), (pet_a, t_a)]
    ordered = [(p.name, t.description) for p, t in sort_pairs_by_preferred_time(pairs)]
    assert ordered == [("alpha", "apple"), ("zebra", "brush")]


def test_sort_pairs_by_urgency_orders_higher_score_first():
    pet = Pet("p", "dog", 1, [])
    low = Task("low", None, "weekly", priority=1)
    high = Task("high", None, "daily", priority=3)
    pairs = [(pet, low), (pet, high)]
    ordered = [t.description for _, t in sort_pairs_by_urgency(pairs)]
    assert ordered == ["high", "low"]


def test_sort_pairs_by_urgency_completed_tasks_sort_last():
    pet = Pet("p", "dog", 1, [])
    open_t = Task("open", None, "daily", priority=1, completed=False)
    done_t = Task("done", None, "daily", priority=9, completed=True)
    pairs = [(pet, done_t), (pet, open_t)]
    ordered = [t.description for _, t in sort_pairs_by_urgency(pairs)]
    assert ordered == ["open", "done"]


def test_detect_preferred_time_skips_completed_overlapping_tasks():
    owner = Owner(
        pets=[
            Pet(
                "p",
                "dog",
                1,
                tasks=[
                    Task("a", 8 * 60, "daily", duration_minutes=60, completed=True),
                    Task("b", 8 * 60 + 30, "daily", duration_minutes=30),
                ],
            )
        ]
    )
    assert detect_preferred_time_conflicts(owner) == []


def test_generate_optimized_schedule_uses_preferred_when_no_overlap():
    pet = Pet("p", "dog", 1, [Task("solo", 10 * 60, "daily", duration_minutes=30)])
    sched = Scheduler(owner=Owner(pets=[pet]))
    plan = sched.generateOptimizedSchedule()
    assert len(plan) == 1
    assert plan[0][2] == 10 * 60


def test_generate_optimized_schedule_fallback_when_preferred_conflicts():
    """Higher-urgency task keeps 9:00; the other first-fits into the gap at day start."""
    pet = Pet(
        "p",
        "dog",
        1,
        tasks=[
            Task("first", 9 * 60, "daily", duration_minutes=60, priority=2),
            Task("second", 9 * 60, "daily", duration_minutes=60, priority=1),
        ],
    )
    sched = Scheduler(owner=Owner(pets=[pet]))
    plan = sched.generateOptimizedSchedule()
    assert len(plan) == 2
    starts = {slot for _, _, slot in plan}
    assert 9 * 60 in starts
    assert 7 * 60 in starts
    assert len(starts) == 2


def test_generate_optimized_schedule_skips_task_larger_than_full_day():
    """Single block longer than day window is skipped (need > budget)."""
    pet = Pet(
        "p",
        "dog",
        1,
        [Task("huge", 7 * 60, "daily", duration_minutes=24 * 60)],
    )
    sched = Scheduler(owner=Owner(pets=[pet]))
    day_budget = 22 * 60 - 7 * 60
    assert pet.tasks[0].total_block_minutes() > day_budget
    assert sched.generateOptimizedSchedule() == []


def test_scheduler_includes_task_when_due_on_reference_date():
    ref = date(2026, 6, 1)
    pet = Pet("p", "dog", 1, [Task("due", 8 * 60, "daily", due_date=ref)])
    sched = Scheduler(owner=Owner(pets=[pet]))
    pairs = sched.sortTasksByPriority(reference_date=ref)
    assert len(pairs) == 1


def test_find_available_slot_works_with_unsorted_occupied():
    sched = Scheduler(owner=Owner(pets=[]))
    need = 30
    slot = sched.findAvailableSlot(7 * 60, 22 * 60, need, [(12 * 60, 13 * 60), (8 * 60, 9 * 60)])
    assert slot == 7 * 60
