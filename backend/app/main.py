from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import (
    academic,
    admin,
    ai,
    assignments,
    auth,
    clubs,
    events,
    hostel,
    notices,
    placement,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="CampusOS API",
    description="AI-powered campus operating system with RBAC — HackOn Amazon",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js dev server and Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler — never expose stack traces
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    import uuid as _uuid

    correlation_id = str(_uuid.uuid4())
    print(f"[ERROR] correlation_id={correlation_id}\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "correlation_id": correlation_id,
        },
    )


# ── Routers ──────────────────────────────────────────────────────────────── #
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(academic.router, prefix=PREFIX)
app.include_router(hostel.router, prefix=PREFIX)
app.include_router(placement.router, prefix=PREFIX)
app.include_router(clubs.router, prefix=PREFIX)
app.include_router(notices.router, prefix=PREFIX)
app.include_router(events.router, prefix=PREFIX)
app.include_router(assignments.router, prefix=PREFIX)
app.include_router(ai.router, prefix=PREFIX)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "campusos-api", "version": "2.0.0"}

