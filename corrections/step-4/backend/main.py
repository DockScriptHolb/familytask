import os
import hashlib  # Module standard Python pour dériver les mots de passe (PBKDF2)
import hmac  # Module standard Python pour comparer des hash en temps constant
import secrets  # Module standard Python pour générer des chaînes aléatoires sécurisées (codes, tokens, sels)
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import EmailStr, field_validator


# --- Configuration de la base de données ---

# URL de connexion à la base : utilise la variable d'environnement DATABASE_URL si définie,
# sinon retombe sur une base SQLite locale (pratique en dev sans dépendance externe)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///familytask.db")

# SQLite a besoin de cet argument pour autoriser l'accès depuis plusieurs threads
# (nécessaire car FastAPI/Uvicorn traite les requêtes de façon asynchrone)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Création du moteur de connexion à la base de données
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


# Restreint les permissions du fichier SQLite local pour qu'il ne soit lisible/modifiable
# que par le propriétaire du processus, et non par tout utilisateur du système.
def secure_sqlite_file_permissions():
    if not DATABASE_URL.startswith("sqlite:///"):
        return

    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if os.path.exists(db_path):
        os.chmod(db_path, 0o600)


# Dependency FastAPI : ouvre une session DB par requête, et la ferme proprement à la fin
def get_session():
    with Session(engine) as session:
        yield session


# --- Modèles ---

# Modèle représentant une tâche, à la fois schéma Pydantic et table SQL
class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)  # Clé primaire, générée automatiquement par la base
    title: str  # Titre de la tâche (texte obligatoire)
    done: bool = Field(default=False)  # État de la tâche, False par défaut (non terminée)
    scheduled_date: Optional[str] = None  # Date optionnelle de planification (format "AAAA-MM-JJ")
    urgent: bool = Field(default=False)  # Indique si la tâche doit être mise en avant visuellement

    # Validateur exécuté automatiquement à chaque création/validation d'un Task
    @field_validator("title")
    @classmethod
    def title_non_vide(cls, value: str) -> str:
        # .strip() supprime les espaces avant/après, pour détecter aussi "   " comme vide
        if not value.strip():
            raise ValueError("Le titre de la tâche ne peut pas être vide")
        return value


# Modèle utilisé pour la mise à jour partielle d'une tâche (tous les champs optionnels)
class TaskUpdate(SQLModel):
    title: Optional[str] = None
    done: Optional[bool] = None
    scheduled_date: Optional[str] = None
    urgent: Optional[bool] = None


# Modèle représentant un membre de la famille, à la fois schéma Pydantic et table SQL
class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)  # Clé primaire, générée automatiquement par la base
    email: str = Field(unique=True, index=True)  # Email unique (contrainte en base) et indexé (recherche rapide)
    name: str  # Nom affiché du membre
    lien: str  # Lien de parenté ou relation dans la famille (ex. "Maman", "Fils")
    family_name: str  # Nom de la famille saisi à l'inscription (ex. "Dupont")
    is_admin: bool = Field(default=False)  # Rôle admin ou non, faux par défaut
    family_code: str = Field(index=True)  # Code de la famille, indexé pour retrouver rapidement tous les membres d'une même famille
    password_hash: str  # Empreinte salée du mot de passe (jamais le mot de passe en clair)
    token: Optional[str] = Field(default=None, index=True)  # Jeton de session/authentification, optionnel (absent tant que le membre n'est pas connecté)


# Modèle représentant les données envoyées lors de l'inscription
class SignupRequest(SQLModel):
    email: EmailStr
    password: str
    name: str
    family: str  # Nom de la famille, stocké dans Member.family_name et utilisé pour générer le family_code
    lien: str

    # Vérifie que le mot de passe respecte une longueur minimale raisonnable.
    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caractères")
        return value


# Modèle représentant les données envoyées lors de la connexion
class LoginRequest(SQLModel):
    email: EmailStr
    password: str


# Modèle de réponse pour /api/me : exclut délibérément password_hash et token
class MemberPublic(SQLModel):
    id: int
    email: str
    name: str
    lien: str
    family_name: str
    is_admin: bool
    family_code: str


# --- Fonctions utilitaires ---

# Nombre d'itérations PBKDF2 ; ralentit volontairement le calcul pour freiner la force brute.
PBKDF2_ITERATIONS = 600_000


# Calcule et renvoie le hash salé d'un mot de passe, au format "salt_hex$hash_hex".
def hash_password(pw: str) -> str:
    # Génère un sel aléatoire de 16 octets, différent à chaque appel.
    salt = secrets.token_bytes(16)

    # Dérive le mot de passe avec SHA-256 via PBKDF2, en utilisant le sel généré.
    derived = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, PBKDF2_ITERATIONS)

    # Stocke le sel et le hash ensemble, séparés par "$", pour pouvoir revérifier plus tard.
    return f"{salt.hex()}${derived.hex()}"


# Vérifie qu'un mot de passe en clair correspond bien au hash stocké, en recalculant avec le même sel.
def verify_password(pw: str, password_hash: str) -> bool:
    # Sépare le sel et le hash stockés ; refuse tout format inattendu (ex. anciens hash non salés).
    try:
        salt_hex, hash_hex = password_hash.split("$", 1)
    except ValueError:
        return False

    # Reconstitue le sel en octets à partir de sa représentation hexadécimale.
    salt = bytes.fromhex(salt_hex)

    # Recalcule le hash du mot de passe fourni avec le même sel et le même nombre d'itérations.
    derived = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, PBKDF2_ITERATIONS)

    # Compare les hash en temps constant pour ne pas révéler d'information par le timing.
    return hmac.compare_digest(derived.hex(), hash_hex)


# Dépendance FastAPI : identifie le membre connecté à partir du token envoyé dans l'en-tête "Authorization: Bearer <token>"
def get_current_member(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Member:
    # On vérifie que l'en-tête est présent et commence bien par "Bearer ", sinon le format est invalide.
    # Header optionnel avec valeur par défaut None : ainsi une absence d'en-tête déclenche notre 401,
    # au lieu du 422 générique que FastAPI renverrait avec un Header(...) obligatoire.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentification requise")

    # On extrait uniquement le token, en retirant le préfixe "Bearer " (7 caractères)
    token = authorization.removeprefix("Bearer ")

    # Refuse un token vide avant même d'interroger la base.
    if not token:
        raise HTTPException(status_code=401, detail="Authentification requise")

    # On récupère le membre dont le token en base correspond exactement à celui envoyé
    member = session.exec(select(Member).where(Member.token == token)).first()

    # Si aucun membre ne correspond (token invalide, absent, ou déjà déconnecté), on refuse l'accès
    if not member:
        raise HTTPException(status_code=401, detail="Authentification requise")

    return member


# Fonction qui crée toutes les tables définies par les modèles SQLModel si elles n'existent pas déjà
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Applique les permissions restreintes une fois le fichier garanti d'exister.
    secure_sqlite_file_permissions()


# --- Application ---

app = FastAPI(title="FamilyTask")  # Instance principale de l'application FastAPI
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # Autorise toutes les origines, méthodes et en-têtes


# Événement exécuté automatiquement au démarrage de l'application
@app.on_event("startup")
def on_startup():
    create_db_and_tables()  # On crée les tables dès que le serveur démarre


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Routes Task ---

# GET /api/tasks : renvoie la liste de toutes les tâches enregistrées en base
@app.get("/api/tasks", response_model=list[Task])
def list_tasks(session: Session = Depends(get_session)):
    tasks = session.exec(select(Task)).all()  # SELECT * FROM task
    return tasks


# GET /api/tasks/{task_id} : renvoie une tâche précise par son id, ou 404 si elle n'existe pas
@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: int, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)  # Recherche par clé primaire
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return task


# POST /api/tasks : crée une nouvelle tâche à partir du JSON envoyé dans le corps de la requête
@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(task: Task, session: Session = Depends(get_session)):
    task.id = None  # On s'assure que l'id est généré par la base, pas fourni par le client
    session.add(task)     # On prépare l'insertion
    session.commit()      # On valide la transaction (écrit réellement en base)
    session.refresh(task)  # On recharge l'objet pour récupérer l'id généré
    return task


# PUT /api/tasks/{task_id} : met à jour une tâche existante (partiellement) ou renvoie 404
@app.put("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskUpdate, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    # On ne met à jour que les champs réellement envoyés par le client
    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# DELETE /api/tasks/{id} : supprime une tâche existante et renvoie un message de confirmation
@app.delete("/api/tasks/{id}")
def delete_task(id: int, session: Session = Depends(get_session)):
    # Recherche de la tâche par sa clé primaire
    task = session.get(Task, id)

    # Si aucune tâche ne correspond à cet id, on renvoie une erreur 404
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    session.delete(task)  # On marque la tâche pour suppression
    session.commit()      # On valide la transaction (suppression réelle en base)

    # On renvoie un message de confirmation en JSON plutôt qu'une réponse vide
    return {"message": f"Tâche {id} supprimée avec succès"}


# PATCH /api/tasks/{id} : inverse l'état "done" d'une tâche existante (true -> false, false -> true)
@app.patch("/api/tasks/{id}", response_model=Task)
def toggle_task(id: int, session: Session = Depends(get_session)):
    # Recherche de la tâche par sa clé primaire
    task = session.get(Task, id)

    # Si aucune tâche ne correspond à cet id, on renvoie une erreur 404
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    # On inverse simplement la valeur booléenne actuelle
    task.done = not task.done

    session.add(task)      # On prépare la mise à jour
    session.commit()       # On valide la transaction (écrit réellement en base)
    session.refresh(task)  # On recharge l'objet pour être sûr d'avoir la valeur à jour

    return task  # FastAPI sérialise automatiquement la tâche modifiée en JSON


# --- Routes Member (authentification) ---

# POST /api/signup : crée le tout premier membre d'une nouvelle famille (admin par défaut)
# Pas de response_model ici : on doit renvoyer le token en plus des infos publiques du membre,
# et MemberPublic ne contient volontairement pas ce champ (il servirait sinon à autre chose que /api/me).
@app.post("/api/signup", status_code=201)
def signup(data: SignupRequest, session: Session = Depends(get_session)):
    # On normalise l'email pour éviter les doublons du type "a@b.com" / "A@B.com"
    email = str(data.email).strip().lower()

    # On vérifie qu'aucun membre n'existe déjà avec cet email, pour éviter les doublons de compte
    existing = session.exec(select(Member).where(Member.email == email)).first()
    if existing:
        raise HTTPException(status_code=422, detail="Un compte existe déjà avec cet email")

    # Génération d'un code de famille aléatoire et lisible (ex. "3F9A2C")
    family_code = secrets.token_hex(3).upper()

    # Génération d'un token d'authentification aléatoire et sécurisé
    token = secrets.token_hex(32)

    # Création du membre : premier de la famille, donc administrateur par défaut
    member = Member(
        email=email,
        name=data.name.strip(),
        lien=data.lien.strip(),
        family_name=data.family.strip(),
        is_admin=True,
        family_code=family_code,
        password_hash=hash_password(data.password),  # On ne stocke jamais le mot de passe en clair
        token=token,
    )

    session.add(member)
    session.commit()
    session.refresh(member)

    # Renvoie le token (nécessaire pour que le frontend connecte automatiquement le nouveau membre)
    # ainsi que ses informations publiques.
    return {"token": token, "member": MemberPublic.model_validate(member)}


# POST /api/login : authentifie un membre existant et lui génère un nouveau token
@app.post("/api/login")
def login(data: LoginRequest, session: Session = Depends(get_session)):
    # Recherche du membre par email, normalisé de la même manière qu'à l'inscription
    email = str(data.email).strip().lower()
    member = session.exec(select(Member).where(Member.email == email)).first()

    # Message volontairement neutre : on ne précise pas si c'est l'email ou le mot de passe qui est faux,
    # pour ne pas donner d'indice à quelqu'un qui tenterait de deviner des comptes existants.
    # verify_password recalcule le hash avec le même sel et compare en temps constant.
    if not member or not verify_password(data.password, member.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    # Génération d'un nouveau token à chaque connexion (invalide l'ancien)
    member.token = secrets.token_hex(32)
    session.add(member)
    session.commit()
    session.refresh(member)

    return {"token": member.token, "member": MemberPublic.model_validate(member)}


# GET /api/me : renvoie les informations du membre actuellement connecté (sans données sensibles)
@app.get("/api/me", response_model=MemberPublic)
def get_me(current_member: Member = Depends(get_current_member)):
    return current_member


# POST /api/logout : déconnecte le membre en supprimant son token en base
@app.post("/api/logout")
def logout(current_member: Member = Depends(get_current_member), session: Session = Depends(get_session)):
    current_member.token = None  # Le token n'est plus valide, toute requête future avec l'ancien token échouera
    session.add(current_member)
    session.commit()
    return {"message": "Déconnexion réussie"}
