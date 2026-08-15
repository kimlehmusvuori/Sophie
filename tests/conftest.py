from __future__ import annotations

from collections.abc import Iterator

import pytest

from sophie.db import base as db_base
from sophie.db.models import Base


@pytest.fixture()
def db_session() -> Iterator[object]:
    db_base.configure("sqlite:///:memory:")
    Base.metadata.create_all(db_base.get_engine())
    with db_base.session_scope() as session:
        yield session
