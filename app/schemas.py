"""Objets échangés par l'API (docs/cadrage.md § 4)."""

from typing import Literal

from pydantic import BaseModel


class Sante(BaseModel):
    status: Literal["ok"] = "ok"
