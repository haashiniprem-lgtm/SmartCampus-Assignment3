import sys
from pathlib import Path

# Allow importing app.py from the project folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import suggest


def test_water_issue_is_plumbing():
    category, priority = suggest("Water leakage in the laboratory")
    assert category == "Plumbing"
    assert priority == "High"


def test_pipe_issue_is_plumbing():
    category, priority = suggest("Pipe is damaged")
    assert category == "Plumbing"


def test_power_issue_is_electrical():
    category, priority = suggest("Power failure in the lab")
    assert category == "Electrical"
    assert priority == "High"


def test_ac_issue_is_hvac():
    category, priority = suggest("AC not cooling")
    assert category == "HVAC"
    assert priority == "Normal"


def test_fire_issue_is_urgent():
    category, priority = suggest("Fire detected in the building")
    assert priority == "Urgent"


def test_general_issue():
    category, priority = suggest("Chair in classroom")
    assert category == "General"
    assert priority == "Normal"