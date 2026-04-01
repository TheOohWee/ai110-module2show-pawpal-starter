from pawpal_system import Pet, Task


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
