from fastapi import FastAPI

from app.auth.router import router as auth_router

app = FastAPI(title="Crea API", description="Construí tu ciudad, construí tu mejor versión.")

app.include_router(auth_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
