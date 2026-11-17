import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _parse_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "")
CORS_ALLOWED_ORIGINS = _parse_origins()

app = FastAPI(title="School Management System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "databaseConfigured": bool(DATABASE_URL),
    }


@app.get("/api/health")
def api_health() -> dict[str, object]:
    return health()
