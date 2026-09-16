from fastapi.testclient import TestClient
from uuid import uuid4

from main import app


client = TestClient(app)


def create_account():
    response = client.post(
        "/api/signup",
        json={
            "email": f"task-{uuid4().hex}@example.com",
            "password": "mot-de-passe-solide",
            "name": "Camille",
            "family": "Les Dupont",
            "lien": "parent",
        },
    )
    assert response.status_code == 200
    result = response.json()
    return result["member"], {"Authorization": f"Bearer {result['token']}"}


def test_me_requires_a_valid_bearer_token():
    # Refuse une requête sans en-tête Authorization.
    missing_header_response = client.get("/api/me")
    assert missing_header_response.status_code == 401

    # Refuse un token Bearer qui ne correspond à aucun membre.
    invalid_token_response = client.get(
        "/api/me",
        headers={"Authorization": "Bearer token-invalide"},
    )
    assert invalid_token_response.status_code == 401


def test_authentication_flow():
    # Utilise une adresse unique pour pouvoir relancer le test avec la base SQLite existante.
    email = f"auth-{uuid4().hex}@example.com"
    signup_data = {
        "email": email,
        "password": "mot-de-passe-solide",
        "name": "Camille",
        "family": "Les Dupont",
        "lien": "parent",
    }

    signup_response = client.post("/api/signup", json=signup_data)
    assert signup_response.status_code == 200
    signup_result = signup_response.json()
    assert signup_result["token"]
    assert signup_result["member"]["is_admin"] is True
    assert "password_hash" not in signup_result["member"]

    token = signup_result["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_response = client.get("/api/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
    assert "password_hash" not in me_response.json()

    login_response = client.post(
        "/api/login",
        json={"email": email, "password": signup_data["password"]},
    )
    assert login_response.status_code == 200
    new_token = login_response.json()["token"]
    assert new_token != token

    wrong_login_response = client.post(
        "/api/login",
        json={"email": email, "password": "mauvais-mot-de-passe"},
    )
    assert wrong_login_response.status_code == 401
    assert wrong_login_response.json()["detail"] == "Email ou mot de passe incorrect"

    logout_response = client.post(
        "/api/logout",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["ok"] is True

    expired_response = client.get(
        "/api/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert expired_response.status_code == 401


def test_create_and_list_tasks():
    member, headers = create_account()

    # Crée une nouvelle tâche avec un titre simple.
    response = client.post(
        "/api/tasks",
        params={"title": "Sortir les poubelles"},
        headers=headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Sortir les poubelles"
    assert data["done"] is False
    assert data["member_id"] == member["id"]
    assert "id" in data

    # Vérifie ensuite qu'elle apparaît dans la liste.
    response = client.get("/api/tasks", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert any(task["title"] == "Sortir les poubelles" for task in tasks)


def test_toggle_and_delete_task():
    _, headers = create_account()

    # Crée une tâche puis la bascule comme terminée.
    response = client.post(
        "/api/tasks",
        params={"title": "Faire la vaisselle"},
        headers=headers,
    )
    task_id = response.json()["id"]

    response = client.patch(f"/api/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["done"] is True

    # Supprime ensuite la tâche créée.
    response = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_urgent_task():
    _, headers = create_account()
    response = client.post(
        "/api/tasks",
        params={"title": "Appeler le médecin", "urgent": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Appeler le médecin"
    assert data["urgent"] is True


def test_empty_title_is_rejected():
    _, headers = create_account()

    # Refuse un titre vide avec une erreur explicite.
    response = client.post("/api/tasks", params={"title": "   "}, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "Le titre ne peut pas être vide"


def test_missing_task_returns_not_found():
    _, headers = create_account()

    # Renvoie une erreur claire pour une tâche absente lors d'une modification.
    response = client.patch("/api/tasks/999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche introuvable"

    # Renvoie la même erreur claire lors d'une suppression.
    response = client.delete("/api/tasks/999999999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche introuvable"


def test_family_tasks_are_admin_only():
    _, headers = create_account()
    client.post("/api/tasks", params={"title": "Tâche familiale"}, headers=headers)

    response = client.get("/api/tasks/famille", headers=headers)

    assert response.status_code == 200
    assert any(task["title"] == "Tâche familiale" for task in response.json())
