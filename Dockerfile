# Production image (staging/production). Hosting provider is decided in backlog 000023.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gettext && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Build-time only values; real ones are injected at runtime.
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:///build.db python manage.py compilemessages \
 && DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:///build.db python manage.py collectstatic --noinput \
 && rm -f build.db

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
