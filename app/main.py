import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import get_settings
from .db import engine
from .logging_config import setup_logging
from .metrics import RequestMetricsMiddleware, register_db_pool_collector
from .routers.analytics import router as analytics_router
from .routers.events import router as events_router
from .routers.health import router as health_router

settings = get_settings()
setup_logging(settings.log_level)
register_db_pool_collector(engine)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application started", extra={"app": settings.app_name})
    yield
    engine.dispose()
    logger.info("application stopped")


app = FastAPI(title="Event Analytics API", lifespan=lifespan)

app.add_middleware(RequestMetricsMiddleware)

app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(health_router)


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
