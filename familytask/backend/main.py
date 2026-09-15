# Importe le système de fichiers pour gérer le chemin de la base et ses permissions.
import os

# Importe le type Optionnel pour autoriser l'ID à être absent lors de la création d'une tâche.
from pathlib import Path
from typing import Optional

# Importe les classes FastAPI nécessaires pour créer l'API, gérer les dépendances et renvoyer des erreurs HTTP.
from fastapi import Depends, FastAPI, HTTPException

# Importe le middleware CORS pour autoriser les requêtes du frontend vers le backend.
from fastapi.middleware.cors import CORSMiddleware

# Importe les outils SQLModel pour créer le modèle, la session et la base de données.
from sqlmodel import Field, Session, SQLModel, create_engine, select


# Déclare la table Task qui représente une tâche à faire dans l'application.
class Task(SQLModel, table=True):
    # Déclare l'identifiant entier de la tâche, clé primaire et auto-généré par SQLite.
    id: Optional[int] = Field(default=None, primary_key=True)

    # Déclare le titre de la tâche, qui doit être du texte.
    title: str

    # Déclare l'état de la tâche, avec False comme valeur par défaut.
    done: bool = False

    # Déclare une date optionnelle pour planifier l'exécution de la tâche.
    scheduled_date: Optional[str] = None


# Définit le chemin absolu de la base SQLite dans le dossier du backend.
database_path = Path(__file__).resolve().parent / "familytask.db"

# Prévient les erreurs de permission en rendant le fichier de base modifiable par l'utilisateur courant.
if database_path.exists():
    # Ajuste les droits de lecture/écriture du fichier si nécessaire.
    os.chmod(database_path, 0o666)

# Construit l'URL SQLite à partir du chemin absolu pour éviter les confusions de répertoire.
sqlite_url = f"sqlite:///{database_path}"

# Configure SQLite pour autoriser les accès concurrents depuis FastAPI.
connect_args = {"check_same_thread": False}

# Crée le moteur SQLModel qui établit la connexion avec la base de données.
engine = create_engine(sqlite_url, connect_args=connect_args)


# Crée toutes les tables SQL définies par les modèles du projet.
def create_db_and_tables():
    # S'assure que le fichier de base existe avant de créer les tables.
    database_path.touch(exist_ok=True)

    # Ajuste les permissions pour éviter un blocage d'écriture si le fichier a été créé par un autre utilisateur.
    os.chmod(database_path, 0o666)

    # Exécute la création des tables si elles n'existent pas encore.
    SQLModel.metadata.create_all(engine)

    # Ajoute la colonne de planification aux bases créées avant cette fonctionnalité.
    with engine.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(task)").fetchall()
        column_names = {column[1] for column in columns}
        if "scheduled_date" not in column_names:
            connection.exec_driver_sql("ALTER TABLE task ADD COLUMN scheduled_date VARCHAR")
            connection.commit()


# Crée immédiatement les tables au chargement du module pour éviter les erreurs de table absente avant le premier appel.
create_db_and_tables()


# Fournit une session SQLModel à chaque route qui a besoin d'accéder à la base.
def get_session():
    # Ouvre une session de base de données pour la durée de la requête.
    with Session(engine) as session:
        # Rend la session disponible à la route appelante.
        yield session


# Crée l'application FastAPI avec le titre visible dans la documentation Swagger.
app = FastAPI(title="FamilyTask")

# Autorise les requêtes provenant du frontend et les méthodes HTTP standard.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Exécute la création des tables au démarrage de l'application.
@app.on_event("startup")
def on_startup():
    # Appelle la fonction qui crée les tables dans la base SQLite.
    create_db_and_tables()


# Déclare une route GET pour vérifier que le backend répond correctement.
@app.get("/api/health")
def health():
    # Retourne un objet JSON indiquant que le service est en ligne.
    return {"status": "ok"}


# Déclare une route GET pour lister toutes les tâches enregistrées.
@app.get("/api/tasks")
def list_tasks(session: Session = Depends(get_session)):
    # Exécute une requête SQL pour récupérer toutes les tâches dans l'ordre par défaut.
    return session.exec(select(Task)).all()


# Déclare une route POST pour créer une nouvelle tâche.
@app.post("/api/tasks")
def add_task(title: str, scheduled_date: Optional[str] = None, session: Session = Depends(get_session)):
    # Vérifie que le titre n'est pas vide ou composé uniquement d'espaces.
    if not title.strip():
        # Lève une erreur HTTP 422 pour signaler que les données envoyées sont invalides.
        raise HTTPException(status_code=422, detail="Le titre ne peut pas être vide")

    # Crée un objet Task avec le titre fourni sans espaces en trop et une date optionnelle.
    task = Task(title=title.strip(), scheduled_date=scheduled_date)

    # Ajoute la tâche à la session de base de données.
    session.add(task)

    # Enregistre la nouvelle tâche dans la base.
    session.commit()

    # Rafraîchit l'objet pour avoir l'ID généré par SQLite.
    session.refresh(task)

    # Renvoie la tâche créée au client.
    return task


# Déclare une route PATCH pour inverser l'état d'une tâche (à faire / terminée).
@app.patch("/api/tasks/{task_id}")
def toggle_task(task_id: int, session: Session = Depends(get_session)):
    # Cherche la tâche correspondant à l'ID demandé.
    task = session.get(Task, task_id)

    # Vérifie si la tâche n'existe pas, pour renvoyer une erreur claire.
    if task is None:
        # Lève une erreur HTTP 404 si la tâche est introuvable.
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    # Inverse l'état actuel de la tâche : True devient False et inversement.
    task.done = not task.done

    # Enregistre la modification dans la base de données.
    session.add(task)
    session.commit()
    session.refresh(task)

    # Retourne la tâche mise à jour au client.
    return task


# Déclare une route DELETE pour supprimer une tâche existante.
@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    # Cherche la tâche à supprimer dans la base.
    task = session.get(Task, task_id)

    # Vérifie que la tâche demandée existe avant de la supprimer.
    if task is None:
        # Lève une erreur HTTP 404 si l'élément demandé est absent.
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    # Supprime la tâche de la session.
    session.delete(task)

    # Valide la suppression dans la base de données.
    session.commit()

    # Renvoie un message simple de confirmation au frontend.
    return {"ok": True}
