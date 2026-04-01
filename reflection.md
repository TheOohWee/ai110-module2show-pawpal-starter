# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

I started with four main classes: **Owner**, **Pet**, **Task**, and **Scheduler**. **Pet** carried identity and biology-oriented hints: name, species, age. **Task** held a title, duration, and priority so the scheduler could rank work. **Scheduler** owned a `constraintsList` and was responsible for ordering tasks and placing them in time. I sketched methods such as `getRecommendedFrequence()` and `getHealthConstraints()` on **Pet**, `giveUrgencyScore()` and `getRequiredTimeBuffer()` on **Task**, and `sortTasksByPriority()`, `findAvailableSlot()`, and `generateOptimizedSchedule()` on **Scheduler** so care requirements, urgency, and placement stayed separated.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. The biggest shift was treating **Task** as a richer lifecycle object and **Owner** as a real aggregate. Tasks gained **description**, **frequency**, **completed**, **time_minutes**, **weekly_weekday**, and **due_date** so the scheduler could respect preferred times, recurring rules, and calendar gates. **Pet** gained an explicit **`tasks`** list instead of an implicit relationship. **Scheduler** stopped being a standalone class with only a constraint bag: it now holds an **`Owner`** reference and pulls tasks through each pet, which matches how the Streamlit app and tests build state. I also introduced **`TimeRangeConflict`** and **module-level helpers** (filtering, sorting pairs, conflict detection) instead of forcing everything onto **Scheduler**, to keep conflict logic testable and reusable without bloating one class.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers: **completion status** (done tasks are excluded), **due on the planning day** (`due_date` vs `reference_date`), optional **weekday** for weekly recurring tasks, **task urgency** derived from priority and frequency (for ordering), **preferred start time** when the full block fits in the day window without overlapping prior placements, and a **fixed day window** (default 07:00–22:00) with **duration plus buffer** for each block. **Priority and frequency** matter most for *order*—that is what makes one open task “more urgent” than another. **Preferred time** matters next when it is feasible; otherwise the algorithm falls back to **first-fit** in remaining gaps. I prioritized a clear, explainable ordering (urgency first) over perfect global optimization because this is a personal planner, not a solver for NP-hard packing.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The scheduler builds the day plan **greedily**: after sorting open tasks by urgency (and priority), it walks that list once and places each task either at its preferred start (if that full block fits inside the day window and does not overlap anything already placed) or at the **first** gap found by `findAvailableSlot`. It never backtracks or reshuffles earlier placements to make room for later tasks. That means the result is fast and easy to reason about, but it is **not globally optimal**—a different ordering or selective “bumping” could sometimes satisfy more preferences or fit an extra task. For a small pet-care planner, that tradeoff is reasonable because predictable, linear behavior matters more than squeezing out a theoretically better packing, and true optimization would add complexity and harder-to-explain schedules.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used AI mainly for **targeted code questions**: walking through one function at a time, comparing alternatives for `findAvailableSlot`, and sanity-checking edge cases for interval overlap. The most helpful prompts were **concrete and scoped**—for example, pasting `findAvailableSlot` and asking how to simplify it for readability or performance, or asking whether half-open intervals `[start, end)` matched my conflict tests. Vague “improve this file” requests were less useful than questions tied to a single behavior and a clear success criterion.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

I kept the explicit `cursor` loop over `sorted(occupied)` instead of the pairwise version. The AI’s approach is more “Pythonic” on paper, but for someone scanning the file once, the indexed loop makes the invariant obvious: advance past each block and try the gap before it. I verified behavior by running the existing tests in `tests/test_pawpal.py` after any change and by mentally tracing edge cases (empty `occupied`, one block, gap exactly equal to `needed_minutes`).

### AI Strategy: VS Code Copilot

**Which Copilot features were most effective for building your scheduler?**

- **Inline completions** while typing dataclass fields and small helpers—fast for boilerplate that still had to match my types and naming.
- **Chat scoped to a file** (e.g., `#file:pawpal_system.py`) when I wanted a second pass on **one algorithm** (like `generateOptimizedSchedule`) without rewriting unrelated modules.
- **Suggesting test cases** from a function signature or docstring—useful as a checklist, though I still had to decide whether each case belonged in the spec.

**One example of a suggestion I rejected or modified to keep the design clean**

Copilot once suggested folding **conflict detection** entirely into **`Scheduler`** as private methods. I **split** that responsibility: keep **`Scheduler`** focused on ordering and placement, and use **module-level functions** plus **`TimeRangeConflict`** for overlap detection so tests could call conflict logic without constructing a full schedule. That rejected refactor kept boundaries clear and avoided a “god class.”

**How separate chat sessions for different phases helped**

Using **different chats** for UML vs implementation vs README/reflection reduced context mixing: one thread kept class relationships stable, another stayed in “Python edge cases,” and another focused on documentation tone. I did not have to re-explain the whole project each time, and I was less likely to “fix” scheduling code while supposedly only editing diagrams.

**What I learned as “lead architect” with powerful AI tools**

The model is strong at **local** edits and plausible patterns, but **ownership** of invariants—half-open intervals, what “due today” means, whether weekly tasks need a weekday column—stays with me. I learned to treat AI output as a **proposal**: run tests, trace one example by hand, and adjust APIs when cohesion suffers. The lead architect’s job is to keep **one coherent story** (data model ↔ scheduler ↔ UI), not to accept the fastest generated diff.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

I tested **task completion** and **daily/weekly recurrence** (including `as_needed`), **owner-level filtering** by pet name and status, **sorting** by preferred time and urgency with deterministic ties, **scheduler gating** by weekday and due date, **preferred-time and plan conflict** detection (including touching intervals and duplicate windows), **optimized schedule** behavior (preferred slot when possible, first-fit fallback, skipping when the day budget is exhausted), and **helpers** such as formatted warning strings and `findAvailableSlot` with unsorted occupied intervals. These tests matter because scheduling bugs are subtle—off-by-one in minutes or wrong interval semantics can break trust in the whole app.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I am **confident** in the behaviors covered by `pytest` for the domain layer—those tests encode the intended spec for urgency, conflicts, and placement. I am **less confident** about **Streamlit-only** paths (session state, reruns, and multi-step flows) because they are not automated. With more time I would add **integration tests** that build an `Owner` in memory, run the same calls the UI uses, and assert tables and warnings; optional **property-based tests** for `findAvailableSlot` with random non-overlapping intervals; and **DST / timezone** checks if `time_minutes` ever maps to real wall clocks beyond a single “minutes from midnight” day.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I am most satisfied with the **clear split** between **urgency ordering**, **greedy placement**, and **conflict reporting**. The app can warn about overlapping *preferences* before generating a plan, and validate *assigned* plans separately—without conflating the two ideas.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I would consider **explicit time-zone support** and a **configurable day window** in the UI only if real users need it. I might also add **optional backtracking** or a second pass for “high priority bumped by low priority placement,” only if user feedback showed the greedy plan was often wrong in practice.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

**Tests are the contract.** When the AI suggested refactors, the only durable check was whether the suite still matched my intent. Designing systems with AI is faster, but the **spec**—encoded in tests and invariants—is what keeps the system from drifting into clever but wrong code.
