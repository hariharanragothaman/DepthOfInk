import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.logging_config import request_id_var, setup_logging
from app.rate_limit import limiter
from app.api.routes import books, characters, chat

setup_logging()
logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for log correlation."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(rid)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            logger.info(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
            )
            return response
        finally:
            request_id_var.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    logger.info("DepthOfInk started (log_format=%s)", settings.log_format)
    yield


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(characters.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    checks: dict[str, str] = {}

    for label, path in [
        ("data_dir", settings.data_dir),
        ("uploads_dir", settings.uploads_dir),
        ("chroma_dir", settings.chroma_dir),
    ]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".health_probe"
            probe.write_text("ok")
            probe.unlink()
            checks[label] = "ok"
        except Exception as e:
            checks[label] = f"error: {e}"

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path=str(settings.chroma_dir / "_health"),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        client.heartbeat()
        checks["chromadb"] = "ok"
    except Exception as e:
        checks["chromadb"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={"status": overall, "checks": checks},
        status_code=status_code,
    )
