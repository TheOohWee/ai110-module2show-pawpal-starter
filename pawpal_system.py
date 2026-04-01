"""
Backend logic for PawPal+.

Class skeletons generated from `uml.mmd`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, List, Literal, Optional, Tuple


TaskStatusFilter = Literal["all", "open", "done"]


@dataclass
class Task:
    """A single care activity: what to do, when, how often, and whether it is done."""

    description: str
    time_minutes: Optional[int]
    frequency: str
    completed: bool = False
    duration_minutes: int = 30
    priority: int = 1
    # For frequency == "weekly": which weekday this recurs (0=Monday … 6=Sunday). Ignored otherwise.
    weekly_weekday: Optional[int] = None
    # Calendar day this task is due; None means no date gate (legacy / due whenever).
    due_date: Optional[date] = None

    def total_block_minutes(self) -> int:
        """
        Minutes the task occupies on the timeline for conflict and placement checks.

        Returns:
            ``duration_minutes`` plus the buffer from ``getRequiredTimeBuffer()``.
        """
        return self.duration_minutes + self.getRequiredTimeBuffer()

    def applies_for_weekday(self, weekday: int) -> bool:
        """
        Whether this task is due on the given calendar weekday.
        `weekday` uses datetime semantics: 0=Monday … 6=Sunday.
        """
        freq = self.frequency.lower().strip()
        if freq == "daily":
            return True
        if freq == "as_needed":
            return True
        if freq == "weekly":
            if self.weekly_weekday is None:
                return True
            return weekday == self.weekly_weekday
        return True

    def giveUrgencyScore(self) -> float:
        """
        Scalar urgency used to order tasks before placement.

        Open tasks: ``priority * 10`` plus a small bonus by frequency (daily >
        weekly > as_needed). Completed tasks always return ``0.0``.

        Returns:
            Non-negative urgency; higher means schedule earlier when possible.
        """
        if self.completed:
            return 0.0
        base = float(self.priority) * 10.0
        freq = self.frequency.lower().strip()
        freq_bonus = {"daily": 3.0, "weekly": 1.0, "as_needed": 0.5}.get(freq, 1.0)
        return base + freq_bonus

    def getRequiredTimeBuffer(self) -> int:
        """Return extra minutes reserved around a task when placing it on the timeline."""
        return max(5, self.duration_minutes // 10)

    def is_due_on(self, reference: date) -> bool:
        """True if this task should be considered for scheduling on the given calendar day."""
        if self.due_date is None:
            return True
        return self.due_date <= reference

    def _clone_next_occurrence(self, next_due: date) -> Task:
        """Copy this task for a future occurrence with a new due date (not completed)."""
        return Task(
            description=self.description,
            time_minutes=self.time_minutes,
            frequency=self.frequency,
            completed=False,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            weekly_weekday=self.weekly_weekday,
            due_date=next_due,
        )

    def mark_complete(self, pet: Optional[Pet] = None, *, today: Optional[date] = None) -> None:
        """
        Mark done, or for daily/weekly recurring tasks attached to a pet, replace this row with
        a new open task for the next occurrence.

        Without `pet`, or for `as_needed` / unknown frequency, sets `completed` on this instance.

        Daily next due date: `today + timedelta(days=1)` (use `today=` for tests).
        Weekly next due date: `today + timedelta(days=7)`.
        """
        if today is None:
            today = date.today()
        freq = self.frequency.lower().strip()
        if (
            pet is not None
            and self in pet.tasks
            and freq == "daily"
        ):
            idx = pet.tasks.index(self)
            next_due = today + timedelta(days=1)
            pet.tasks[idx] = self._clone_next_occurrence(next_due)
            return
        if (
            pet is not None
            and self in pet.tasks
            and freq == "weekly"
        ):
            idx = pet.tasks.index(self)
            next_due = today + timedelta(days=7)
            pet.tasks[idx] = self._clone_next_occurrence(next_due)
            return
        self.completed = True


@dataclass
class Pet:
    """A pet with identity, species, age, and an owned list of care tasks."""

    name: str
    species: str
    age: int
    tasks: List[Task] = field(default_factory=list)

    def getRecommendedFrequence(self) -> str:
        """Return a short species- and age-based care frequency guideline string."""
        s = self.species.lower()
        if s == "dog":
            if self.age <= 2:
                return "3 short walks daily; meals 3x for puppies"
            if self.age >= 8:
                return "2 gentle walks daily; meals 2x; joint care"
            return "2–3 walks daily; meals 2x"
        if s == "cat":
            return "Enrichment/play 2x daily; meals 2–3 small portions"
        return "Follow vet guidance for species-specific care"

    def getHealthConstraints(self) -> List[str]:
        """Return bullet-style health notes for this pet's life stage and species."""
        s = self.species.lower()
        notes: List[str] = []
        if self.age < 1:
            notes.append("Young animal: frequent meals, vet schedule, supervised exercise")
        if s == "dog" and self.age >= 8:
            notes.append("Senior dog: joint-friendly movement, weight and dental checks")
        if s == "cat" and self.age >= 10:
            notes.append("Senior cat: hydration, litter access, renal monitoring")
        return notes if notes else ["Maintain regular wellness exams"]


@dataclass
class Owner:
    """An owner aggregate: holds pets and supports flat task views and filtering."""

    pets: List[Pet] = field(default_factory=list)

    def get_all_tasks(self) -> List[Task]:
        """Return every task from every pet in a single flat list."""
        return [task for pet in self.pets for task in pet.tasks]

    def iter_tasks_with_pet(self) -> List[Tuple[Pet, Task]]:
        """Return (pet, task) pairs for all tasks across all pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]

    def filter_tasks(
        self,
        *,
        status: TaskStatusFilter = "all",
        pet_name: Optional[str] = None,
    ) -> List[Tuple[Pet, Task]]:
        """
        Return (pet, task) pairs filtered by completion status and/or pet name.
        Pet name matching is case-insensitive; whitespace is stripped on both sides.
        """
        pairs = self.iter_tasks_with_pet()
        if pet_name is not None:
            key = pet_name.strip().casefold()
            pairs = [(p, t) for p, t in pairs if p.name.strip().casefold() == key]
        if status == "open":
            pairs = [(p, t) for p, t in pairs if not t.completed]
        elif status == "done":
            pairs = [(p, t) for p, t in pairs if t.completed]
        return pairs


def filter_tasks_with_pets(
    owner: Owner,
    pet: Optional[Pet] = None,
    status: TaskStatusFilter = "all",
) -> List[Tuple[Pet, Task]]:
    """Filter (pet, task) pairs by optional pet instance and completion status."""
    pairs = owner.filter_tasks(status=status)
    if pet is not None:
        pairs = [(p, t) for p, t in pairs if p is pet]
    return pairs


def sort_pairs_by_preferred_time(pairs: List[Tuple[Pet, Task]]) -> List[Tuple[Pet, Task]]:
    """
    Sort (pet, task) pairs for display or planning previews by preferred start time.

    Tasks with ``time_minutes`` set are ordered earlier by that value; tasks without
    a preferred time are placed after all timed tasks. Ties break on pet name, then
    task description (case-insensitive).

    Args:
        pairs: Zero or more (pet, task) tuples (not mutated; a sorted copy is returned).

    Returns:
        New list sorted by preferred time, then stable secondary keys.
    """
    out = list(pairs)

    def key(pt: Tuple[Pet, Task]) -> Tuple[int, int, str, str]:
        pet, task = pt
        has_pref = task.time_minutes is not None
        pref = task.time_minutes if has_pref else 0
        # no preferred time -> sort after those with time
        return (0 if has_pref else 1, pref, pet.name.lower(), task.description.lower())

    out.sort(key=key)
    return out


def sort_pairs_by_urgency(pairs: List[Tuple[Pet, Task]]) -> List[Tuple[Pet, Task]]:
    """
    Sort (pet, task) pairs by scheduling urgency (highest first).

    Uses ``Task.giveUrgencyScore()`` and ``priority`` descending; completed tasks
    contribute zero urgency. Secondary keys keep ordering deterministic.

    Args:
        pairs: Zero or more (pet, task) tuples.

    Returns:
        New list sorted from most urgent to least urgent.
    """
    out = list(pairs)

    def key(pt: Tuple[Pet, Task]) -> Tuple[float, int, str, str]:
        pet, task = pt
        return (
            -task.giveUrgencyScore(),
            -task.priority,
            pet.name.lower(),
            task.description.lower(),
        )

    out.sort(key=key)
    return out


@dataclass(frozen=True)
class TimeRangeConflict:
    """Two scheduled or preferred blocks that overlap in time."""

    pet_a: str
    task_a: str
    start_a: int
    end_a: int
    pet_b: str
    task_b: str
    start_b: int
    end_b: int


def _intervals_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    """
    Return whether two half-open minute intervals overlap.

    Intervals are treated as [start, end): they touch at an endpoint without
    overlapping (e.g. [0, 60) and [60, 120) do not conflict).

    Args:
        s1: Start of the first interval (minutes from midnight).
        e1: End of the first interval (exclusive).
        s2: Start of the second interval.
        e2: End of the second interval (exclusive).

    Returns:
        True if the intervals share any positive-length overlap.
    """
    return not (e1 <= s2 or e2 <= s1)


def detect_preferred_time_conflicts(owner: Owner) -> List[TimeRangeConflict]:
    """
    Detect pairwise overlaps between preferred-time windows across the owner's open tasks.

    Only incomplete tasks with ``time_minutes`` set are considered. Each window spans
    ``[time_minutes, time_minutes + total_block_minutes)``, including the task buffer.
    Conflicts may involve the same pet or different pets.

    Args:
        owner: Owner whose pets' tasks are scanned.

    Returns:
        All unordered pairs of overlapping preferred windows as ``TimeRangeConflict``
        records (may be empty).
    """
    items: List[Tuple[Pet, Task, int, int]] = []
    for pet, task in owner.iter_tasks_with_pet():
        if task.completed or task.time_minutes is None:
            continue
        start = task.time_minutes
        end = start + task.total_block_minutes()
        items.append((pet, task, start, end))

    conflicts: List[TimeRangeConflict] = []
    for i in range(len(items)):
        pet_a, task_a, sa, ea = items[i]
        for j in range(i + 1, len(items)):
            pet_b, task_b, sb, eb = items[j]
            if _intervals_overlap(sa, ea, sb, eb):
                conflicts.append(
                    TimeRangeConflict(
                        pet_a=pet_a.name,
                        task_a=task_a.description,
                        start_a=sa,
                        end_a=ea,
                        pet_b=pet_b.name,
                        task_b=task_b.description,
                        start_b=sb,
                        end_b=eb,
                    )
                )
    return conflicts


def format_time_range_conflict_warning(conflict: TimeRangeConflict) -> str:
    """Human-readable line for logging or UI; does not raise."""

    def _clock(m: int) -> str:
        h, mm = divmod(m, 60)
        return f"{h:02d}:{mm:02d}"

    return (
        f"{conflict.pet_a}'s \"{conflict.task_a}\" "
        f"({_clock(conflict.start_a)}–{_clock(conflict.end_a)}) overlaps with "
        f"{conflict.pet_b}'s \"{conflict.task_b}\" "
        f"({_clock(conflict.start_b)}–{_clock(conflict.end_b)})"
    )


def detect_plan_conflicts(
    plan: List[Tuple[Pet, Task, int]],
) -> List[TimeRangeConflict]:
    """
    Detect time overlaps in an assigned schedule (actual slot starts, not preferences).

    Each plan row is ``(pet, task, slot_start_minutes)``; block end is
    ``slot_start + task.total_block_minutes()``. Used to validate optimized or
    hand-built plans.

    Args:
        plan: Assigned starts in minutes-from-midnight for each (pet, task).

    Returns:
        Pairs of overlapping placements as ``TimeRangeConflict`` entries.
    """
    enriched: List[Tuple[Pet, Task, int, int]] = []
    for pet, task, slot_start in plan:
        end = slot_start + task.total_block_minutes()
        enriched.append((pet, task, slot_start, end))

    conflicts: List[TimeRangeConflict] = []
    for i in range(len(enriched)):
        pet_a, task_a, sa, ea = enriched[i]
        for j in range(i + 1, len(enriched)):
            pet_b, task_b, sb, eb = enriched[j]
            if _intervals_overlap(sa, ea, sb, eb):
                conflicts.append(
                    TimeRangeConflict(
                        pet_a=pet_a.name,
                        task_a=task_a.description,
                        start_a=sa,
                        end_a=ea,
                        pet_b=pet_b.name,
                        task_b=task_b.description,
                        start_b=sb,
                        end_b=eb,
                    )
                )
    return conflicts


@dataclass
class Scheduler:
    """
    Retrieves tasks via the Owner (each Pet's task list), then sorts and places them in a day.
    """

    owner: Owner
    constraintsList: List[Any] = field(default_factory=list)

    def _open_tasks_with_pets(
        self,
        weekday: Optional[int] = None,
        reference_date: Optional[date] = None,
    ) -> List[Tuple[Pet, Task]]:
        """
        List incomplete tasks paired with the pet that owns each task, optionally for a weekday.
        Tasks with `due_date` after `reference_date` are excluded. `reference_date` defaults to today.
        """
        ref = reference_date if reference_date is not None else date.today()
        pairs = [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if not task.completed and task.is_due_on(ref)
        ]
        if weekday is not None:
            pairs = [(p, t) for p, t in pairs if t.applies_for_weekday(weekday)]
        return pairs

    def preferred_time_conflict_warnings(self) -> List[str]:
        """
        Lightweight conflict check: compare preferred start + block length for each open task.
        Same pet or different pets; returns warning lines only (never raises).
        """
        return [
            format_time_range_conflict_warning(c)
            for c in detect_preferred_time_conflicts(self.owner)
        ]

    def plan_conflict_warnings(
        self, plan: List[Tuple[Pet, Task, int]]
    ) -> List[str]:
        """Warn if assigned slots overlap (e.g. manual plans); never raises."""
        return [
            format_time_range_conflict_warning(c) for c in detect_plan_conflicts(plan)
        ]

    def sortTasksByPriority(
        self,
        weekday: Optional[int] = None,
        reference_date: Optional[date] = None,
    ) -> List[Tuple[Pet, Task]]:
        """
        List open tasks eligible for scheduling, ordered by urgency then priority.

        Applies the same filters as schedule generation: not completed, due on
        ``reference_date`` (default today), and if ``weekday`` is given, matching
        ``Task.applies_for_weekday``.

        Args:
            weekday: Optional calendar weekday (0=Monday … 6=Sunday) for recurring rules.
            reference_date: Tasks with ``due_date`` after this day are excluded.

        Returns:
            Mutable list of (pet, task) pairs, sorted highest urgency first.
        """
        pairs = self._open_tasks_with_pets(
            weekday=weekday, reference_date=reference_date
        )
        pairs.sort(
            key=lambda pt: (pt[1].giveUrgencyScore(), pt[1].priority),
            reverse=True,
        )
        return pairs

    def findAvailableSlot(
        self,
        start_of_day_minutes: int,
        end_of_day_minutes: int,
        needed_minutes: int,
        occupied: List[Tuple[int, int]],
    ) -> Optional[int]:
        """
        First-fit placement: earliest minute where a block fits in the day window.

        Treats ``occupied`` as half-open intervals ``[start, end)`` in minute-of-day
        coordinates. Merges overlaps implicitly by scanning sorted blocks and
        advancing a cursor past each block.

        Args:
            start_of_day_minutes: Earliest allowed start (e.g. 7 * 60).
            end_of_day_minutes: End of planning window; block must finish by this minute.
            needed_minutes: Required contiguous length (typically ``total_block_minutes``).
            occupied: Already placed intervals as (start, end) pairs.

        Returns:
            Start minute for the new block, or ``None`` if no gap is large enough.
        """
        cursor = start_of_day_minutes
        for block_start, block_end in sorted(occupied):
            if block_start > cursor and block_start - cursor >= needed_minutes:
                return cursor
            cursor = max(cursor, block_end)
        if end_of_day_minutes - cursor >= needed_minutes:
            return cursor
        return None

    def generateOptimizedSchedule(
        self,
        day_start_minutes: int = 7 * 60,
        day_end_minutes: int = 22 * 60,
        weekday: Optional[int] = None,
        reference_date: Optional[date] = None,
    ) -> List[Tuple[Pet, Task, int]]:
        """
        Greedy day packer: assign non-overlapping start times within a time budget.

        Iterates tasks in urgency/priority order (see ``sortTasksByPriority``). For each
        task, if preferred ``time_minutes`` fits inside the day window and does not
        overlap existing blocks, that slot is used; otherwise ``findAvailableSlot``
        searches for the first gap. Tasks that need more time than remains in the
        day window are skipped.

        Args:
            day_start_minutes: Planning window start (minutes from midnight).
            day_end_minutes: Planning window end (exclusive upper bound for block ends).
            weekday: If set, only tasks whose frequency/weekday rules apply are included.
            reference_date: Only tasks with ``due_date`` None or ``<= reference_date`` are eligible.

        Returns:
            List of ``(pet, task, start_minutes_from_midnight)`` with no overlapping blocks.
        """
        sorted_pairs = self.sortTasksByPriority(
            weekday=weekday, reference_date=reference_date
        )
        occupied: List[Tuple[int, int]] = []
        plan: List[Tuple[Pet, Task, int]] = []
        budget = day_end_minutes - day_start_minutes
        used = 0

        for pet, task in sorted_pairs:
            need = task.total_block_minutes()
            if need > budget or used + need > budget:
                continue

            slot: Optional[int] = None
            pref = task.time_minutes
            if pref is not None:
                end_pref = pref + need
                fits_window = day_start_minutes <= pref and end_pref <= day_end_minutes
                overlaps = any(not (end_pref <= s or pref >= e) for s, e in occupied)
                if fits_window and not overlaps:
                    slot = pref

            if slot is None:
                slot = self.findAvailableSlot(
                    day_start_minutes, day_end_minutes, need, occupied
                )
            if slot is None:
                continue

            occupied.append((slot, slot + need))
            plan.append((pet, task, slot))
            used += need

        return plan
