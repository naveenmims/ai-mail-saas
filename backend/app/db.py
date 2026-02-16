import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import Engine

load_dotenv()

# Default SQLite DB file in backend root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_mail.db")

# Use DATABASE_URL from .env if present, else fallback to ai_mail.db
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DB_PATH}"

# SQLite needs this for multi-thread/multi-worker
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_reset_on_return="rollback",
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    # ONLY apply pragmas to SQLite
    if not str(DATABASE_URL).startswith("sqlite"):
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()
    except Exception:
        pass


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()

def test_db_connection():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
def init_db():
    """
    Create tables from SQLAlchemy models (safe no-op if already created).
    Alembic is preferred in production; this is for dev convenience.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
