"""Configures the database and runs migrations at app startup. The only
place the UI touches Alembic/engine setup directly."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from sophie.config import get_settings
from sophie.db import base as db_base

_REPO_ROOT = Path(__file__).resolve().parents[4]


def bootstrap_database() -> None:
    settings = get_settings()
    db_base.configure(settings.database_url)

    alembic_ini = _REPO_ROOT / "alembic.ini"
    if alembic_ini.exists():
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
