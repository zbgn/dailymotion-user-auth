FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	UV_PROJECT_ENVIRONMENT=/opt/venv \
	PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --group test --no-install-project

COPY app ./app
COPY tests ./tests
COPY postgres-entrypoint-initdb.d ./postgres-entrypoint-initdb.d

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
