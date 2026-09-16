# Importe hashlib pour calculer le hash SHA-256 des mots de passe.
import hashlib

# Importe hmac pour comparer les hash sans divulguer d'information temporelle.
import hmac

# Importe secrets pour générer des codes familiaux et des tokens imprévisibles.
import secrets

# Importe le système de fichiers pour gérer le chemin de la base et ses permissions.
import os

# Importe le type Optionnel pour autoriser l'ID à être absent lors de la création d'une tâche.
from pathlib import Path
from typing import Optional

# Importe les classes FastAPI nécessaires pour créer l'API, gérer les dépendances et renvoyer des erreurs HTTP.
from fastapi import Body, Depends, FastAPI, Header, HTTPException

# Importe le middleware CORS pour autoriser les requêtes du frontend vers le backend.
from fastapi.middleware.cors import CORSMiddleware

# Importe les outils SQLModel pour créer le modèle, la session et la base de données.
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select


# Déclare la table Task qui représente une tâche à faire dans l'application.
class Task(SQLModel, table=True):
    # Déclare l'identifiant entier de la tâche, clé primaire et auto-généré par SQLite.
    id: Optional[int] = Field(default=None, primary_key=True)

    # Déclare le titre de la tâche, qui doit être du texte.
    title: str

    # Déclare l'état de la tâche, avec False comme valeur par défaut.
    done: bool = False

    # Déclare si la tâche est urgente et doit être mise en avant visuellement.
    urgent: bool = False

    # Déclare une date optionnelle pour planifier l'exécution de la tâche.
    scheduled_date: Optional[str] = None

    # Lie chaque tâche au membre auquel elle est assignée.
    member_id: Optional[int] = Field(default=None, foreign_key="member.id", index=True)


# Déclare la table Member qui représente un membre d'une famille.
class Member(SQLModel, table=True):
    # Déclare l'identifiant entier du membre, clé primaire et auto-généré par SQLite.
    id: Optional[int] = Field(default=None, primary_key=True)

    # Rend l'adresse email obligatoire, unique et indexée pour accélérer les recherches.
    email: str = Field(unique=True, index=True)

    # Stocke le nom affiché du membre.
    name: str

    # Stocke le lien ou le rôle du membre dans la famille.
    lien: str

    # Indique si le membre dispose des droits administrateur.
    is_admin: bool = False

    # Indexe le code familial pour retrouver rapidement les membres d'une même famille.
    family_code: str = Field(index=True)

    # Stocke uniquement le hash du mot de passe, jamais le mot de passe en clair.
    password_hash: str

    # Stocke le jeton associé au membre, ou une chaîne vide après déconnexion.
    token: str = ''


# Calcule et renvoie le hash SHA-256 d'un mot de passe fourni en texte.
def hash_password(pw: str) -> str:
    # Encode le mot de passe en UTF-8 avant de calculer son empreinte hexadécimale.
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()


# Décrit les données attendues lors de la création du premier membre d'une famille.
class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    family: str
    lien: str


# Décrit les identifiants nécessaires pour ouvrir une session.
class LoginRequest(BaseModel):
    email: str
    password: str


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
        if "urgent" not in column_names:
            connection.exec_driver_sql("ALTER TABLE task ADD COLUMN urgent BOOLEAN DEFAULT 0")
        if "member_id" not in column_names:
            connection.exec_driver_sql("ALTER TABLE task ADD COLUMN member_id INTEGER")
        connection.commit()


# Crée immédiatement les tables au chargement du module pour éviter les erreurs de table absente avant le premier appel.
create_db_and_tables()


# Fournit une session SQLModel à chaque route qui a besoin d'accéder à la base.
def get_session():
    # Ouvre une session de base de données pour la durée de la requête.
    with Session(engine) as session:
        # Rend la session disponible à la route appelante.
        yield session


# Renvoie les informations publiques d'un membre sans exposer son hash de mot de passe.
def public_member(member: Member) -> dict:
    # Exclut explicitement le hash avant de renvoyer les données au client.
    return member.model_dump(exclude={'password_hash'})


# Retrouve le membre associé au token Bearer envoyé dans l'en-tête Authorization.
def current_member(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Member:
    # Vérifie que l'en-tête respecte le format standard "Bearer <token>".
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail='Authentification requise')

    # Récupère uniquement la valeur du token après le préfixe Bearer.
    token = authorization[7:].strip()
    member = session.exec(select(Member).where(Member.token == token)).first()

    # Refuse les tokens absents, vides ou inconnus.
    if not token or member is None:
        raise HTTPException(status_code=401, detail='Authentification requise')

    return member


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


# Déclare la route d'inscription du premier membre d'une nouvelle famille.
@app.post('/api/signup')
def signup(
    data: Optional[SignupRequest] = Body(default=None),
    email: Optional[str] = None,
    password: Optional[str] = None,
    name: Optional[str] = None,
    family: Optional[str] = None,
    lien: Optional[str] = None,
    session: Session = Depends(get_session),
):
    # Accepte aussi les paramètres d'URL pour rester compatible avec les routes existantes.
    data = data or SignupRequest(
        email=email or '',
        password=password or '',
        name=name or '',
        family=family or '',
        lien=lien or '',
    )

    # Nettoie l'adresse email avant de vérifier son unicité.
    email = data.email.strip().lower()

    # Refuse les données indispensables absentes ou composées uniquement d'espaces.
    if not email or not data.password or not data.name.strip() or not data.family.strip() or not data.lien.strip():
        raise HTTPException(status_code=422, detail='Les informations sont incomplètes')

    # Vérifie qu'aucun membre n'utilise déjà cette adresse email.
    existing_member = session.exec(select(Member).where(Member.email == email)).first()
    if existing_member is not None:
        raise HTTPException(status_code=409, detail='Cette adresse email est déjà utilisée')

    # Génère un code familial indépendant de l'adresse email du membre.
    family_code = secrets.token_urlsafe(9)

    # Génère le token de session remis au membre après son inscription.
    token = secrets.token_urlsafe(32)
    member = Member(
        email=email,
        name=data.name.strip(),
        lien=data.lien.strip(),
        is_admin=True,
        family_code=family_code,
        password_hash=hash_password(data.password),
        token=token,
    )

    # Enregistre le premier membre de la famille dans la base.
    session.add(member)
    session.commit()
    session.refresh(member)

    # Renvoie le token de session et les informations publiques du membre créé.
    return {'token': token, 'member': public_member(member)}


# Déclare la route de connexion d'un membre existant.
@app.post('/api/login')
def login(
    data: Optional[LoginRequest] = Body(default=None),
    email: Optional[str] = None,
    password: Optional[str] = None,
    session: Session = Depends(get_session),
):
    # Accepte aussi les paramètres d'URL pour rester compatible avec les clients existants.
    data = data or LoginRequest(email=email or '', password=password or '')

    # Normalise l'email de la même manière qu'à l'inscription.
    email = data.email.strip().lower()
    member = session.exec(select(Member).where(Member.email == email)).first()

    # Utilise un message identique pour un email inconnu ou un mot de passe incorrect.
    if member is None or not hmac.compare_digest(member.password_hash, hash_password(data.password)):
        raise HTTPException(status_code=401, detail='Email ou mot de passe incorrect')

    # Remplace l'ancien token par un nouveau token de session.
    member.token = secrets.token_urlsafe(32)
    session.add(member)
    session.commit()
    session.refresh(member)

    # Renvoie le nouveau token et les informations publiques du membre.
    return {'token': member.token, 'member': public_member(member)}


# Déclare la route qui renvoie le membre authentifié courant.
@app.get('/api/me')
def me(member: Member = Depends(current_member)):
    # Ne renvoie jamais le hash du mot de passe au client.
    return public_member(member)


# Déclare la route qui invalide le token de session courant.
@app.post('/api/logout')
def logout(member: Member = Depends(current_member), session: Session = Depends(get_session)):
    # Efface le token en base afin qu'il ne puisse plus être utilisé.
    stored_member = session.get(Member, member.id)
    stored_member.token = ''
    session.add(stored_member)
    session.commit()

    # Confirme la fermeture de la session au client.
    return {'ok': True, 'message': 'Déconnexion réussie'}


# Déclare une route GET pour lister les tâches du membre connecté.
@app.get("/api/tasks")
def list_tasks(member: Member = Depends(current_member), session: Session = Depends(get_session)):
    # Une tâche ne peut être consultée que par le membre auquel elle est assignée.
    return session.exec(select(Task).where(Task.member_id == member.id)).all()


# Déclare une route réservée aux administrateurs pour voir toute leur famille.
@app.get("/api/tasks/famille")
def list_family_tasks(member: Member = Depends(current_member), session: Session = Depends(get_session)):
    if not member.is_admin:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")

    family_member_ids = select(Member.id).where(Member.family_code == member.family_code)
    return session.exec(select(Task).where(Task.member_id.in_(family_member_ids))).all()


# Déclare une route POST pour créer une nouvelle tâche.
@app.post("/api/tasks")
def add_task(
    title: str,
    scheduled_date: Optional[str] = None,
    urgent: bool = False,
    member_id: Optional[int] = None,
    member: Member = Depends(current_member),
    session: Session = Depends(get_session),
):
    # Vérifie que le titre n'est pas vide ou composé uniquement d'espaces.
    if not title.strip():
        # Lève une erreur HTTP 422 pour signaler que les données envoyées sont invalides.
        raise HTTPException(status_code=422, detail="Le titre ne peut pas être vide")

    assigned_member_id = member.id
    if member_id is not None:
        if not member.is_admin:
            raise HTTPException(status_code=403, detail="Seul un administrateur peut affecter une tâche")

        assigned_member = session.get(Member, member_id)
        if assigned_member is None or assigned_member.family_code != member.family_code:
            raise HTTPException(status_code=404, detail="Membre introuvable dans votre famille")
        assigned_member_id = assigned_member.id

    # Crée la tâche pour le membre connecté ou le membre de famille choisi par l'admin.
    task = Task(
        title=title.strip(),
        scheduled_date=scheduled_date,
        urgent=urgent,
        member_id=assigned_member_id,
    )

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
def toggle_task(
    task_id: int,
    member: Member = Depends(current_member),
    session: Session = Depends(get_session),
):
    # Cherche la tâche correspondant à l'ID demandé.
    task = session.get(Task, task_id)

    # Vérifie si la tâche n'existe pas, pour renvoyer une erreur claire.
    if task is None:
        # Lève une erreur HTTP 404 si la tâche est introuvable.
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    if task.member_id != member.id:
        assigned_member = session.get(Member, task.member_id) if task.member_id is not None else None
        if not member.is_admin or assigned_member is None or assigned_member.family_code != member.family_code:
            raise HTTPException(status_code=403, detail="Accès interdit à cette tâche")

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
def delete_task(
    task_id: int,
    member: Member = Depends(current_member),
    session: Session = Depends(get_session),
):
    # Cherche la tâche à supprimer dans la base.
    task = session.get(Task, task_id)

    # Vérifie que la tâche demandée existe avant de la supprimer.
    if task is None:
        # Lève une erreur HTTP 404 si l'élément demandé est absent.
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    if task.member_id != member.id:
        assigned_member = session.get(Member, task.member_id) if task.member_id is not None else None
        if not member.is_admin or assigned_member is None or assigned_member.family_code != member.family_code:
            raise HTTPException(status_code=403, detail="Accès interdit à cette tâche")

    # Supprime la tâche de la session.
    session.delete(task)

    # Valide la suppression dans la base de données.
    session.commit()

    # Renvoie un message simple de confirmation au frontend.
    return {"ok": True}
