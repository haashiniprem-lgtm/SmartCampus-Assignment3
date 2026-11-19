import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app

client = app.test_client()


def test_homepage_loads():
    response = client.get("/")
    assert response.status_code == 200


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_booking_api_returns_list():
    response = client.get("/api/bookings")
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_invalid_booking_is_rejected():
    response = client.post("/book", data={
        "facility_id": "",
        "requester": "Test Student",
        "start_at": "",
        "end_at": ""
    })
    assert response.status_code == 400