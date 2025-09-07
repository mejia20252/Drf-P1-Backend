# ---- Stage 1: build ----
FROM python:3.12-slim AS builder

# Ajustes básicos de Python y pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de compilación (solo en build stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Virtualenv aislado para copiar a la imagen final
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Instala dependencias de la app (asegurate de tener requirements.txt)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install gunicorn

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Copiamos el venv ya construido
COPY --from=builder /venv /venv

# Crea usuario no-root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Copia el código de la app
COPY --chown=appuser:appuser . .

# (Opcional) Si usas archivos estáticos:
# Establece tu módulo de settings antes de descomentar la siguiente línea
# ENV DJANGO_SETTINGS_MODULE=tu_proyecto.settings
# RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Reemplaza "tu_proyecto.wsgi:application" por tu módulo WSGI real
CMD ["gunicorn", "drf_p1_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
