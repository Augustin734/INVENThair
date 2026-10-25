from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session

from app.database import creer_moteur, initialiser_base
from app.main import creer_app


@pytest.fixture
def chemin_base(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def client(chemin_base: Path) -> Iterator[TestClient]:
    with TestClient(creer_app(chemin_base)) as c:
        yield c


@pytest.fixture
def moteur(chemin_base: Path) -> Iterator[Engine]:
    m = creer_moteur(chemin_base)
    initialiser_base(m)
    yield m
    m.dispose()


@pytest.fixture
def session(moteur: Engine) -> Iterator[Session]:
    with Session(moteur) as s:
        yield s
