import os
from pathlib import Path

from sqlalchemy import Index, Integer, String, Text, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get("AUTH_DB_PATH", str(DB_DIR / "auth.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    email: Mapped[str | None] = mapped_column(nullable=True, default=None)
    phone: Mapped[str | None] = mapped_column(nullable=True, default=None)
    alert_threshold_flood_pct: Mapped[float | None] = mapped_column(
        nullable=True,
        default=None,
    )
    alerts_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_pluvial_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_fluvial_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_heatwave_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_snow_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_threshold_pluvial_pct: Mapped[float | None] = mapped_column(
        nullable=True,
        default=None,
    )
    alert_threshold_fluvial_pct: Mapped[float | None] = mapped_column(
        nullable=True,
        default=None,
    )
    alert_threshold_heatwave_humidex: Mapped[float | None] = mapped_column(
        nullable=True,
        default=None,
    )
    alert_threshold_snow_pct: Mapped[float | None] = mapped_column(
        nullable=True,
        default=None,
    )
    alert_via_sms: Mapped[bool] = mapped_column(default=True, nullable=False)
    alert_via_email: Mapped[bool] = mapped_column(default=False, nullable=False)
    alert_frequency_hours: Mapped[int | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_flood_alert_sent_at: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_pluvial_alert_sent_at: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_fluvial_alert_sent_at: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_heatwave_alert_sent_at: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None,
    )
    last_snow_alert_sent_at: Mapped[str | None] = mapped_column(
        nullable=True,
        default=None,
    )
    partner_city: Mapped[str | None] = mapped_column(
        String(16), nullable=True, default=None
    )


class UserActionJournal(Base):
    __tablename__ = "user_action_journal"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(nullable=False)
    log_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    route: Mapped[str | None] = mapped_column(String(200), nullable=True)

    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_user_action_journal_log_date_user", "log_date", "user_id"),
    )


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

if "sqlite" in DATABASE_URL:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _add_user_columns_if_missing()
    _migrate_alert_v2_sqlite()
    _add_user_action_journal_columns_if_missing()


def _add_user_columns_if_missing() -> None:
    if "sqlite" not in DATABASE_URL:
        return
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(users)"))
        rows = r.fetchall()
    columns = {row[1] for row in rows}
    with engine.connect() as conn:
        if "email" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN email TEXT"))
            conn.commit()
        if "phone" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone TEXT"))
            conn.commit()
        if "alert_threshold_flood_pct" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_threshold_flood_pct REAL")
            )
            conn.commit()
        if "alerts_enabled" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alerts_enabled INTEGER DEFAULT 0")
            )
            conn.commit()
        if "alert_via_sms" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_via_sms INTEGER DEFAULT 1")
            )
            conn.commit()
        if "alert_via_email" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_via_email INTEGER DEFAULT 0")
            )
            conn.commit()
        if "alert_frequency_hours" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_frequency_hours INTEGER")
            )
            conn.commit()
        if "last_flood_alert_sent_at" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_flood_alert_sent_at TEXT")
            )
            conn.commit()
        if "alert_pluvial_enabled" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN alert_pluvial_enabled "
                    "INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        if "alert_fluvial_enabled" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN alert_fluvial_enabled "
                    "INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        if "alert_heatwave_enabled" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN alert_heatwave_enabled "
                    "INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        if "alert_snow_enabled" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN alert_snow_enabled INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        if "alert_threshold_pluvial_pct" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_threshold_pluvial_pct REAL")
            )
            conn.commit()
        if "alert_threshold_fluvial_pct" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_threshold_fluvial_pct REAL")
            )
            conn.commit()
        if "alert_threshold_heatwave_humidex" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN alert_threshold_heatwave_humidex REAL"
                )
            )
            conn.commit()
        if "alert_threshold_snow_pct" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN alert_threshold_snow_pct REAL")
            )
            conn.commit()
        if "last_pluvial_alert_sent_at" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_pluvial_alert_sent_at TEXT")
            )
            conn.commit()
        if "last_fluvial_alert_sent_at" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_fluvial_alert_sent_at TEXT")
            )
            conn.commit()
        if "last_heatwave_alert_sent_at" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_heatwave_alert_sent_at TEXT")
            )
            conn.commit()
        if "last_snow_alert_sent_at" not in columns:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN last_snow_alert_sent_at TEXT")
            )
            conn.commit()
        if "partner_city" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN partner_city TEXT"))
            conn.commit()


def _migrate_alert_v2_sqlite() -> None:
    if "sqlite" not in DATABASE_URL:
        return
    with engine.connect() as conn:
        current = conn.execute(text("PRAGMA user_version")).scalar() or 0
        if current >= 2:
            return
        conn.execute(
            text(
                """
                UPDATE users SET
                  alert_pluvial_enabled = alerts_enabled,
                  alert_threshold_pluvial_pct = alert_threshold_flood_pct,
                  last_pluvial_alert_sent_at = last_flood_alert_sent_at
                """
            )
        )
        conn.execute(text("PRAGMA user_version = 2"))
        conn.commit()


def sync_legacy_alert_fields(user: User) -> None:
    user.alerts_enabled = (
        user.alert_pluvial_enabled
        or user.alert_fluvial_enabled
        or user.alert_heatwave_enabled
        or user.alert_snow_enabled
    )
    user.alert_threshold_flood_pct = user.alert_threshold_pluvial_pct


def _add_user_action_journal_columns_if_missing() -> None:
    if "sqlite" not in DATABASE_URL:
        return
    with engine.connect() as conn:
        r = conn.execute(text("PRAGMA table_info(user_action_journal)"))
        rows = r.fetchall()
    if not rows:
        return
    columns = {row[1] for row in rows}
    with engine.connect() as conn:
        if "payload_json" not in columns:
            conn.execute(
                text("ALTER TABLE user_action_journal ADD COLUMN payload_json TEXT")
            )
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional():
    """Yields None when auth is disabled so endpoints avoid touching the DB."""
    from app.constants.feature_flags import auth_disabled

    if auth_disabled():
        yield None
        return
    yield from get_db()
