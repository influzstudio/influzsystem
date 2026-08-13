import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./influz.db")

# Handle Render PostgreSQL URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    _auto_migrate()


def _auto_migrate():
    """
    Lightweight auto-migration: adds any model columns missing from the live
    DB table (Postgres on Render persists across deploys, so create_all alone
    won't add new columns to existing tables). Safe no-op if already in sync.
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)

    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing_cols = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            col_type = col.type.compile(dialect=engine.dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}'
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                print(f"[migrate] added column {table.name}.{col.name}")
            except Exception as e:
                print(f"[migrate] skip {table.name}.{col.name}: {e}")
