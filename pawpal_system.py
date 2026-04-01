"""
Backend logic for PawPal+.

Class skeletons generated from `uml.mmd`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class Task:
    """A single care activity: what to do, when, how often, and whether it is done."""

    description: str
    time_minutes: Optional[int]
    frequency: str
    completed: bool = False
    duration_minutes: int = 30
    priority: int = 1

    def giveUrgencyScore(self) -> float:
        """Return scheduling urgency for open tasks; completed tasks score 0."""
        if self.completed:
            return 0.0
        base = float(self.priority) * 10.0
        freq = self.frequency.lower().strip()
        freq_bonus = {"daily": 3.0, "weekly": 1.0, "as_needed": 0.5}.get(freq, 1.0)
        return base + freq_bonus

    def getRequiredTimeBuffer(self) -> int:
        """Return extra minutes reserved around a task when placing it on the timeline."""
        return max(5, self.duration_minutes // 10)

    def mark_complete(self) -> None:
        """Mark this task as done for scheduling and urgency purposes."""
        self.completed = True


@dataclass
class Pet:
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
    pets: List[Pet] = field(default_factory=list)

    def get_all_tasks(self) -> List[Task]:
        """Return every task from every pet in a single flat list."""
        return [task for pet in self.pets for task in pet.tasks]

    def iter_tasks_with_pet(self) -> List[Tuple[Pet, Task]]:
        """Return (pet, task) pairs for all tasks across all pets."""
        return [(pet, task) for pet in self.pets for task in pet.tasks]


@dataclass
class Scheduler:
    """
    Retrieves tasks via the Owner (each Pet's task list), then sorts and places them in a day.
    """

    owner: Owner
    constraintsList: List[Any] = field(default_factory=list)

    def _open_tasks_with_pets(self) -> List[Tuple[Pet, Task]]:
        """List incomplete tasks paired with the pet that owns each task."""
        return [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if not task.completed
        ]

    def sortTasksByPriority(self) -> List[Tuple[Pet, Task]]:
        """Sort open (pet, task) pairs by urgency score then priority, highest first."""
        pairs = self._open_tasks_with_pets()
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
        """Find the first start minute that fits `needed_minutes` in gaps of occupied ranges."""
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
    ) -> List[Tuple[Pet, Task, int]]:
        """Build a non-overlapping day plan: each row is (pet, task, start_minutes_from_midnight)."""
        sorted_pairs = self.sortTasksByPriority()
        occupied: List[Tuple[int, int]] = []
        plan: List[Tuple[Pet, Task, int]] = []
        budget = day_end_minutes - day_start_minutes
        used = 0

        for pet, task in sorted_pairs:
            need = task.duration_minutes + task.getRequiredTimeBuffer()
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
