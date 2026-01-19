from fastapi import FastAPI

from .routers.events import router as events_router
from .routers.analytics import router as analytics_router

app = FastAPI(title="Event Analytics API")

app.include_router(events_router)
app.include_router(analytics_router)

@app.get("/health")
def health():
    return {"ok": True}
