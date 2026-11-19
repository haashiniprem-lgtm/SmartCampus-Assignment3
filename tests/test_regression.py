import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app, suggest

client = app.test_client()


def test_water_leak_priority_remains_high():
    category, priority = suggest("Water leak")
    assert category == "Plumbing"
    assert priority == "High"


def test_sparking_remains_urgent():
    category, priority = suggest("Electrical sparking")
    assert category == "Electrical"
    assert priority == "Urgent"


def test_invalid_ticket_is_rejected():
    response = client.post("/ticket", data={
        "facility_id": "",
        "description": ""
    })
    assert response.status_code == 400


def test_unknown_api_route_returns_404():
    response = client.get("/unknown")
    assert response.status_code == 404