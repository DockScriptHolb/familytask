from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_create_task_with_scheduled_date_and_toggle():
    response = client.post(
        "/api/tasks",
        params={"title": "Faire la vaisselle", "scheduled_date": "2026-09-20"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Faire la vaisselle"
    assert data["scheduled_date"] == "2026-09-20"
    assert data["done"] is False

    task_id = data["id"]
    response = client.patch(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["done"] is True
