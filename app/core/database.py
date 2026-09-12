from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = "sqlite:///./travel.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def ensure_legacy_schema():
    """Add new nullable columns to the development SQLite database safely.

    There is no migration framework in this project. Existing trips remain
    intact and unowned until a future data migration assigns their user_id.
    """
    inspector = inspect(engine)
    if "trips" not in inspector.get_table_names():
        return

    trip_columns = {
        column["name"] for column in inspector.get_columns("trips")
    }

    with engine.begin() as connection:
        if "user_id" not in trip_columns:
            connection.execute(
                text("ALTER TABLE trips ADD COLUMN user_id INTEGER")
            )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_trips_user_id "
                "ON trips (user_id)"
            )
        )
        if "ai_plan" not in trip_columns:
            connection.execute(
                text("ALTER TABLE trips ADD COLUMN ai_plan JSON")
            )


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()