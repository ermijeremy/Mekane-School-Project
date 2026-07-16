from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CONFIG
from db.connection import pool
from student import routes as student_router
from teacher import routes as teacher_router
import auth
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()

    yield
    await pool.close()

app = FastAPI(lifespan=lifespan, title="MekaneSchool API")

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:8000,http://localhost:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(auth.router, prefix="/auth")
app.include_router(student_router.router, prefix="/student")
app.include_router(teacher_router.router, prefix="/teacher")

@app.get("/health")
async def health():
    return {"status": "ok"}