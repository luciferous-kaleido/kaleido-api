# ---- build stage ----
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.23-python3.14-alpine /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 依存定義だけ先に入れてレイヤーキャッシュを効かせる
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime stage ----
FROM python:3.14-slim AS runtime

# keep-id:uid=1000,gid=1000 とそろえるため UID/GID を固定
RUN groupadd --system --gid 1000 app \
 && useradd --system --uid 1000 --gid app --home /app app \
 && mkdir -p /app/data \
 && chown -R app:app /app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
