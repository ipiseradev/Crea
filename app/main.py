from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.game.router import router as city_router
from app.habits.router import router as habits_router
from app.stats.router import router as stats_router
from app.sync.router import router as sync_router

app = FastAPI(title="Crea API", description="Construí tu ciudad, construí tu mejor versión.")

app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(city_router)
app.include_router(sync_router)
app.include_router(stats_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
