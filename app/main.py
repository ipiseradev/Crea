from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.game.router import router as city_router
from app.habits.router import router as habits_router

app = FastAPI(title="Crea API", description="Construí tu ciudad, construí tu mejor versión.")

app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(city_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
