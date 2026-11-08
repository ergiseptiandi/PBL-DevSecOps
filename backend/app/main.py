"""Task Manager API — backend blue/green untuk praktikum DevSecOps.

Secure coding yang diterapkan (lihat README bagian Security):
- Validasi input ketat (Pydantic v2, StrictBool, whitelist karakter).
- Query via ORM SQLAlchemy = parameterized secara otomatis.
- Rate limiting per-IP (slowapi).
- Security headers di setiap response.
- CORS whitelist eksplisit (bukan '*').
- Error response tidak membocorkan stack trace / detail internal.
- Konfigurasi & kredensial via environment variable, bukan hardcode.
"""

import logging

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .db import Base, engine, get_db
from .schemas import TaskCreate, TaskOut, TaskUpdate, VersionOut
from .security import SecurityHeadersMiddleware, limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("taskmanager")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=None,      # matikan Swagger UI di production
    redoc_url=None,
    openapi_url=None,   # matikan schema publik
)

app.state.limiter = limiter
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Terlalu banyak request, coba lagi sebentar lagi."},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {"field": ".".join(str(loc) for loc in err.get("loc", [])), "message": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Input tidak valid.", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


@app.get("/api/health")
@limiter.limit(settings.RATE_LIMIT)
def health(request: Request) -> dict[str, str]:
    return {"status": "ok", "color": settings.APP_COLOR, "version": settings.APP_VERSION}


@app.get("/api/version", response_model=VersionOut)
@limiter.limit(settings.RATE_LIMIT)
def version(request: Request) -> VersionOut:
    return VersionOut(
        app=settings.APP_NAME, version=settings.APP_VERSION, color=settings.APP_COLOR
    )


@app.get("/api/tasks", response_model=list[TaskOut])
@limiter.limit(settings.RATE_LIMIT)
def list_tasks(request: Request, db: Session = Depends(get_db)) -> list[models.Task]:
    return (
        db.query(models.Task)
        .order_by(models.Task.created_at.desc())
        .limit(200)
        .all()
    )


@app.post("/api/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT)
def create_task(
    payload: TaskCreate, request: Request, db: Session = Depends(get_db)
) -> models.Task:
    task = models.Task(title=payload.title)
    db.add(task)
    db.commit()
    db.refresh(task)
    logger.info("task_created id=%s", task.id)
    return task


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
@limiter.limit(settings.RATE_LIMIT)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Task:
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task tidak ditemukan.",
        )
    task.completed = payload.completed
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT)
def delete_task(
    task_id: int, request: Request, db: Session = Depends(get_db)
) -> Response:
    task = db.get(models.Task, task_id)
    if task is not None:
        db.delete(task)
        db.commit()
        logger.info("task_deleted id=%s", task_id)
    # 204 baik untuk id yang ada maupun tidak ada (tidak membocorkan eksistensi)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
