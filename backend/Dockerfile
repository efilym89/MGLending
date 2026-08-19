FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ARG APP_UID=10004
ARG APP_GID=10004
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --gid "${APP_GID}" landing-leads \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --no-create-home \
       --shell /usr/sbin/nologin landing-leads
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels annaelle-landing-leads \
    && rm -rf /wheels
COPY config ./config
USER ${APP_UID}:${APP_GID}
EXPOSE 8083
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8083/healthz', timeout=3).read()"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
