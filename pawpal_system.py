"""
Backend logic for PawPal+.

Class skeletons generated from `uml.mmd`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Owner:
    pets: List[Pet] = field(default_factory=list)


@dataclass
class Pet:
    name: str
    species: str
    age: int

    def getRecommendedFrequence(self):
        ...

    def getHealthConstraints(self):
        ...


@dataclass
class Task:
    title: str
    duration: int
    priority: int

    def giveUrgencyScore(self):
        ...

    def getRequiredTimeBuffer(self):
        ...


@dataclass
class Scheduler:
    constraintsList: List = field(default_factory=list)

    def sortTasksByPriority(self):
        ...

    def findAvailableSlot(self):
        ...

    def generateOptimizedSchedule(self):
        ...

