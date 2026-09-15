from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_create_and_list_tasks():
    # Crée une nouvelle tâche avec un titre simple.
    response = client.post("/api/tasks", params={"title": "Sortir les poubelles"})
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Sortir les poubelles"
    assert data["done"] is False
    assert "id" in data

    # Vérifie ensuite qu'elle apparaît dans la liste.
    response = client.get("/api/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert any(task["title"] == "Sortir les poubelles" for task in tasks)


def test_toggle_and_delete_task():
    # Crée une tâche puis la bascule comme terminée.
    response = client.post("/api/tasks", params={"title": "Faire la vaisselle"})
    task_id = response.json()["id"]

    response = client.patch(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["done"] is True

    # Supprime ensuite la tâche créée.
    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_empty_title_is_rejected():
    # Refuse un titre vide avec une erreur explicite.
    response = client.post("/api/tasks", params={"title": "   "})

    assert response.status_code == 422
    assert response.json()["detail"] == "Le titre ne peut pas être vide"


def test_missing_task_returns_not_found():
    # Renvoie une erreur claire pour une tâche absente lors d'une modification.
    response = client.patch("/api/tasks/999999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche introuvable"

    # Renvoie la même erreur claire lors d'une suppression.
    response = client.delete("/api/tasks/999999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche introuvable"
