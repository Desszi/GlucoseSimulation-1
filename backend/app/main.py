from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import init_db
from .api.routes import auth, patients, meals, simulation, chat

app = FastAPI(title=settings.APP_NAME)

# Allow local frontend (Vite default port 5173) and any future dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(meals.router)
app.include_router(simulation.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"status": "ok"}
