from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings, load_schema
from .kommo import KommoClient
from .meta import MetaClient
from .models import LeadSubmission, SubmitResponse
from .security import PayloadCipher, is_valid_fernet_key
from .service import LeadService
from .storage import Storage


def build_service(settings: Settings) -> LeadService:
    encryption_key = settings.data_encryption_key.get_secret_value()
    if not is_valid_fernet_key(encryption_key):
        raise ValueError("DATA_ENCRYPTION_KEY must be a Fernet key")
    schema = load_schema(settings.schema_path)
    storage = Storage(settings.database_path)
    storage.initialize()
    return LeadService(
        settings=settings,
        schema=schema,
        storage=storage,
        cipher=PayloadCipher(encryption_key),
        kommo=KommoClient(
            domain=settings.kommo_domain,
            token=settings.kommo_long_lived_token.get_secret_value(),
            schema=schema,
            timeout_seconds=settings.kommo_timeout_seconds,
        ),
        meta=MetaClient(
            dataset_id=settings.meta_website_dataset_id,
            access_token=settings.meta_website_access_token.get_secret_value(),
            api_version=settings.meta_graph_api_version,
            test_event_code=settings.meta_test_event_code,
            timeout_seconds=settings.meta_timeout_seconds,
        ),
    )


def create_app(settings: Settings | None = None, service: LeadService | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_service = service or build_service(resolved_settings)
    stop_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        worker = asyncio.create_task(resolved_service.worker_loop(stop_event))
        yield
        stop_event.set()
        await worker

    app = FastAPI(
        title="Annaelle Landing Leads",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.service = resolved_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(resolved_settings.origin_set),
        allow_credentials=False,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Idempotency-Key", "X-Submission-Id"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_guards(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > resolved_settings.max_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "REQUEST_TOO_LARGE"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/healthz")
    async def health() -> dict[str, object]:
        return {"status": "ok", "queue": resolved_service.storage.health()}

    @app.post("/v1/leads", response_model=SubmitResponse, status_code=201)
    async def submit_lead(submission: LeadSubmission, request: Request) -> SubmitResponse:
        origin = request.headers.get("origin", "").rstrip("/")
        if origin not in resolved_settings.origin_set:
            raise HTTPException(status_code=403, detail="ORIGIN_NOT_ALLOWED")
        header_id = request.headers.get("idempotency-key") or request.headers.get("x-submission-id")
        if header_id != submission.submission_id:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_MISMATCH")
        client_ip = request.headers.get("x-real-ip") or (
            request.client.host if request.client else "0.0.0.0"
        )
        user_agent = request.headers.get("user-agent", "unknown")[:1024]
        return await resolved_service.submit(
            submission,
            client_ip=client_ip,
            client_user_agent=user_agent,
        )

    return app


def create_production_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return create_app(settings)


app = create_production_app()
