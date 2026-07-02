import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db

router = APIRouter(tags=["health"])

logger = logging.getLogger(__name__)


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/health/live")
def live():
    """Liveness: the process is up and serving requests."""
    return {"status": "alive"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: the service can reach its database."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("readiness check failed")
        return JSONResponse(status_code=503, content={"status": "not ready"})
    return {"status": "ready"}
