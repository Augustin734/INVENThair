from fastapi import APIRouter

from app.schemas import Sante

router = APIRouter(tags=["Santé"])


@router.get("/health", response_model=Sante, summary="Ping")
def health() -> Sante:
    return Sante()
