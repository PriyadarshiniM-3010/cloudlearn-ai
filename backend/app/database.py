import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

_engine = None
_SessionLocal = None
_last_db_url = None


def get_configured_db_url() -> str:
    """Read the latest DATABASE_URL from environment or backend/.env."""
    backend_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(backend_env_path):
        load_dotenv(backend_env_path, override=True)
    else:
        load_dotenv(override=True)

    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return ""

    # Adjust dialect for psycopg 3 if standard postgresql:// URL is provided
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def get_engine():
    """Returns or initializes the database engine based on the current DATABASE_URL."""
    global _engine, _SessionLocal, _last_db_url

    db_url = get_configured_db_url()
    if not db_url:
        _engine = None
        _SessionLocal = None
        _last_db_url = None
        return None

    # Re-initialize engine if URL has changed or engine is not yet created
    if _engine is None or db_url != _last_db_url:
        try:
            connect_args = {}
            if "pooler" in db_url or "neon.tech" in db_url:
                connect_args["prepare_threshold"] = None

            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args=connect_args,
            )
            _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
            _last_db_url = db_url
        except Exception as e:
            print(f"[Warning] Failed to initialize database engine: {e}")
            _engine = None
            _SessionLocal = None
            return None

    return _engine


def get_session():
    """Returns a SessionLocal instance."""
    get_engine()
    return _SessionLocal


def get_db():
    """FastAPI dependency that yields a database session and safely closes it."""
    session_factory = get_session()
    if not session_factory:
        raise RuntimeError("Database is not configured. Please set DATABASE_URL in backend/.env.")
    db = session_factory()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def check_db_connection():
    """Tests the database connection and returns (is_connected, message)."""
    db_url = get_configured_db_url()
    if not db_url:
        return False, "DATABASE_URL is not set in backend/.env"

    current_engine = get_engine()
    if not current_engine:
        return False, "Database engine could not be initialized from DATABASE_URL"

    try:
        with current_engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            if result == 1:
                return True, "Database connection successful"
            return False, f"Unexpected ping result: {result}"
    except Exception as e:
        return False, str(e)


def init_db():
    """Creates database tables and optional pgvector extension if configured."""
    current_engine = get_engine()
    if not current_engine:
        return False, "Engine not configured"

    try:
        # Import models so Base.metadata is aware of all table definitions
        from backend.app import models  # noqa: F401

        # Optionally enable pgvector extension for Neon
        with current_engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            except Exception:
                # Non-fatal if vector extension permissions are restricted
                pass

        Base.metadata.create_all(bind=current_engine)
        return True, "Tables initialized successfully"
    except Exception as e:
        return False, str(e)
