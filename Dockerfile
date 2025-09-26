# ---- Stage 1: build ----
FROM python:3.12-slim AS builder

# Ajustes básicos de Python y pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias de compilación para Python packages AND WeasyPrint system dependencies
# Install system dependencies needed for WeasyPrint at build time (some might be linked by cffi)
# and also those needed at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    libffi-dev \
    shared-mime-info \
    libharfbuzz-dev \
    libicu-dev \
    libgirepository-1.0-1 \
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
    PORT=8080 

WORKDIR /app

# Install ONLY the runtime system dependencies for WeasyPrint
# No need for -dev packages here, just the libraries themselves.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi8 \
    shared-mime-info \
    libharfbuzz0b \
    libicu-dev \
    libgirepository-1.0-1 \
 # Ensure fonts are available for rendering
    fonts-dejavu \
    fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

# Copiamos el venv ya construido
COPY --from=builder /venv /venv

# Crea usuario no-root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Copia el código de la app
COPY --chown=appuser:appuser . .

# Copy and set up the entrypoint script
COPY --chown=appuser:appuser ./entrypoint.sh /usr/src/app/
RUN chmod +x /usr/src/app/entrypoint.sh

EXPOSE 8080 

# Use the entrypoint script instead of the direct CMD
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]