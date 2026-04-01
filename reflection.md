# PawPal+ Project Reflection

## 1. System Design

**a. Initial design** (apparently I confused it, and answered this before making a class diagram)

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

I would define next 4 classes: owner, pet, task, scheduler. Attributes of pet: name, species, age. Attrbiutes of task: title, duration, priority. Attributes of scheduler: constraintsList. 

This would allow to provide specific care requirements for each pet based on its biology, define urgency for scheduler and resolve conflict. 

Methods
pet: getRecommendedFrequence(), getHealthConstraints()
task: giveUrgencyScore(), getRequiredTimeBuffer()
scheduler: sortTasksByPriority(), findAvailableSlot(), generateOptimizedSchedule()


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler builds the day plan **greedily**: after sorting open tasks by urgency (and priority), it walks that list once and places each task either at its preferred start (if that full block fits inside the day window and does not overlap anything already placed) or at the **first** gap found by `findAvailableSlot`. It never backtracks or reshuffles earlier placements to make room for later tasks. That means the result is fast and easy to reason about, but it is **not globally optimal**—a different ordering or selective “bumping” could sometimes satisfy more preferences or fit an extra task. For a small pet-care planner, that tradeoff is reasonable because predictable, linear behavior matters more than squeezing out a theoretically better packing, and true optimization would add complexity and harder-to-explain schedules.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I shared `findAvailableSlot` from the scheduler with Copilot and asked: *“How could this algorithm be simplified for better readability or performance?”* It suggested collapsing the loop with `itertools.pairwise` on sorted occupied ranges (or merging intervals first), which is compact and idiomatic Python. Helpful prompts were concrete ones tied to one function and a clear goal (“readability or performance”), not vague “improve this file” requests.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

I kept the explicit `cursor` loop over `sorted(occupied)` instead of the pairwise version. The AI’s approach is more “Pythonic” on paper, but for someone scanning the file once, the indexed loop makes the invariant obvious: advance past each block and try the gap before it. I verified behavior by running the existing tests in `tests/test_pawpal.py` after any change and by mentally tracing edge cases (empty `occupied`, one block, gap exactly equal to `needed_minutes`).

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
