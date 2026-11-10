FROM python:3.12.10-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY services/worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12.10-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 10001 nextrade && \
    useradd --uid 10001 --gid nextrade --create-home --shell /usr/sbin/nologin nextrade

COPY --from=builder /opt/venv /opt/venv
COPY --chown=nextrade:nextrade services/worker/worker_app ./worker_app

USER nextrade

CMD ["celery", "-A", "worker_app.main.celery_app", "worker", "--loglevel=info"]

