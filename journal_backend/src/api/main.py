import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# =============================================================================
# App and Settings
# =============================================================================

# PUBLIC_INTERFACE
def get_settings() -> dict:
    """Returns application settings sourced from environment variables.

    Required environment variables:
    - DATABASE_URL: SQLAlchemy connection URL for PostgreSQL (e.g., postgresql+psycopg://user:pass@host:port/db)
    - JWT_SECRET_KEY: Secret key for signing JWT tokens
    - JWT_ALGORITHM: Algorithm used to sign JWT (default: HS256)
    - ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration in minutes (default: 60)
    """
    return {
        "DATABASE_URL": os.environ.get("DATABASE_URL", "sqlite:///./journal.db"),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY", "CHANGE_ME"),
        "JWT_ALGORITHM": os.environ.get("JWT_ALGORITHM", "HS256"),
        "ACCESS_TOKEN_EXPIRE_MINUTES": int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        # FRONTEND CORS origins can be configured via env, comma-separated
        "CORS_ALLOW_ORIGINS": os.environ.get("CORS_ALLOW_ORIGINS", "*"),
    }


settings = get_settings()

app = FastAPI(
    title="Personal Journal API",
    description=(
        "API for a personal journal application. Supports user registration/login "
        "and CRUD for journal entries."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and metadata"},
        {"name": "auth", "description": "User authentication and registration"},
        {"name": "journals", "description": "Journal entries CRUD operations"},
        {"name": "admin", "description": "Administrative and seed operations"},
    ],
)
app.__doc__ = (
    "FastAPI application entrypoint for the Personal Journal backend.\n\n"
    "Provides routes for health checks, authentication, and journal CRUD operations.\n"
    "Environment-driven configuration is loaded via get_settings().\n"
    "JWT handling uses 'from jose import JWTError, jwt' provided by the python-jose package."
)

# CORS
allow_origins = (
    ["*"] if settings["CORS_ALLOW_ORIGINS"] == "*"
    else [o.strip() for o in settings["CORS_ALLOW_ORIGINS"].split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Database Setup (SQLAlchemy)
# =============================================================================
DATABASE_URL = settings["DATABASE_URL"]
# Create engine. If using sqlite for local dev, needed connect_args
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model representing application users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    journals = relationship("JournalEntry", back_populates="owner", cascade="all, delete-orphan")


class JournalEntry(Base):
    """JournalEntry model representing a user's journal entry."""
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="journals")


def init_db():
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


# Dependency to get DB session per request
def get_db():
    """Yields a database session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Security and Auth helpers
# =============================================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET_KEY = settings["JWT_SECRET_KEY"]
JWT_ALGORITHM = settings["JWT_ALGORITHM"]
ACCESS_TOKEN_EXPIRE_MINUTES = settings["ACCESS_TOKEN_EXPIRE_MINUTES"]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with an expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Fetch a user by email."""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by verifying credentials."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get the currently authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub: str = payload.get("sub")  # user email used as subject
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, sub)
    if user is None:
        raise credentials_exception
    return user


# =============================================================================
# Schemas (Pydantic)
# =============================================================================
class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Type of token, typically 'bearer'")


class UserCreate(BaseModel):
    email: str = Field(..., description="User email for registration/login")
    password: str = Field(..., min_length=6, description="Password for the user")


class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class JournalCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the journal entry")
    content: str = Field(..., min_length=1, description="Content/body of the journal entry")


class JournalUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title")
    content: Optional[str] = Field(None, description="Updated content")


class JournalOut(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Routes
# =============================================================================

@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    init_db()


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Returns service health and metadata.")
def health_check():
    """Health check endpoint.

    Returns:
        dict: JSON object with status and service info.
    """
    return {"status": "ok", "service": "personal-journal-backend", "version": app.version}


# PUBLIC_INTERFACE
@app.post("/auth/register", response_model=UserOut, tags=["auth"], summary="Register a new user")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user.

    Args:
        user_in (UserCreate): Registration payload containing email and password.
        db (Session): Database session dependency.

    Returns:
        UserOut: Created user details without sensitive fields.
    """
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# PUBLIC_INTERFACE
@app.post(
    "/auth/token",
    response_model=Token,
    tags=["auth"],
    summary="Obtain JWT token",
    description="Exchange email and password for a JWT access token.",
)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login to obtain an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): OAuth2 form with username (email) and password.
        db (Session): Database session.

    Returns:
        Token: JWT access token and token type.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password.")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# PUBLIC_INTERFACE
@app.get(
    "/auth/me",
    response_model=UserOut,
    tags=["auth"],
    summary="Get current user",
    description="Returns information about the currently authenticated user.",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Get details of the current authenticated user."""
    return current_user


# PUBLIC_INTERFACE
@app.post(
    "/journals",
    response_model=JournalOut,
    tags=["journals"],
    summary="Create a journal entry",
    description="Create a new journal entry for current user.",
)
def create_journal(entry_in: JournalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a journal entry for the authenticated user."""
    entry = JournalEntry(user_id=current_user.id, title=entry_in.title, content=entry_in.content)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# PUBLIC_INTERFACE
@app.get(
    "/journals",
    response_model=List[JournalOut],
    tags=["journals"],
    summary="List journal entries",
    description="List all journal entries for the current user, sorted by updated_at desc.",
)
def list_journals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List journal entries for current user."""
    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == current_user.id)
        .order_by(JournalEntry.updated_at.desc())
        .all()
    )
    return entries


# PUBLIC_INTERFACE
@app.get(
    "/journals/{entry_id}",
    response_model=JournalOut,
    tags=["journals"],
    summary="Get a journal entry",
)
def get_journal(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific journal entry by ID for the current user."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    return entry


# PUBLIC_INTERFACE
@app.put(
    "/journals/{entry_id}",
    response_model=JournalOut,
    tags=["journals"],
    summary="Update a journal entry",
)
def update_journal(
    entry_id: int,
    entry_in: JournalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a specific journal entry by ID."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    if entry_in.title is not None:
        entry.title = entry_in.title
    if entry_in.content is not None:
        entry.content = entry_in.content
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# PUBLIC_INTERFACE
@app.delete(
    "/journals/{entry_id}",
    status_code=204,
    tags=["journals"],
    summary="Delete a journal entry",
)
def delete_journal(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a specific journal entry by ID."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found.")
    db.delete(entry)
    db.commit()
    return None


# PUBLIC_INTERFACE
@app.post(
    "/admin/seed",
    tags=["admin"],
    summary="Seed initial data",
    description="Seeds a demo user and sample entries. Requires header X-Seed-Key matching env SEED_KEY."
)
def seed(
    db: Session = Depends(get_db),
    x_seed_key: Optional[str] = Header(default=None, convert_underscores=False, alias="X-Seed-Key"),
):
    """Seed database with a demo user and entries.

    Set environment variable SEED_KEY to a custom value, and pass it in header X-Seed-Key to authorize seeding.
    """
    seed_key_env = os.environ.get("SEED_KEY", "devseed")
    if x_seed_key != seed_key_env:
        raise HTTPException(status_code=401, detail="Unauthorized seed operation.")

    email = "demo@example.com"
    user = get_user_by_email(db, email)
    if not user:
        user = User(email=email, hashed_password=get_password_hash("password123"))
        db.add(user)
        db.commit()
        db.refresh(user)

    # Add sample entries if none
    existing_count = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).count()
    if existing_count == 0:
        samples = [
            ("Welcome", "This is your first journal entry in the Ocean Professional app."),
            ("Ideas", "1) Build a journaling habit. 2) Reflect weekly."),
        ]
        for title, content in samples:
            entry = JournalEntry(user_id=user.id, title=title, content=content)
            db.add(entry)
            db.commit()
    return {"status": "seeded", "user": user.email}
