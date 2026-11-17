# Production image (staging/production). Hosting provider is decided in backlog 000023.

# --- 1. Build the SPA / PWA ---------------------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- 2. Django API + static hosting ----------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gettext && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /frontend/dist ./frontend/dist
# Build-time only values; real ones are injected at runtime.
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:///build.db python manage.py compilemessages --ignore=frontend \
 && DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:///build.db python manage.py collectstatic --noinput \
 && rm -f build.db

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
