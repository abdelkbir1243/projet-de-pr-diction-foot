# Image unique de la plateforme Goalgebra : application Streamlit, API (FastAPI) et worker (pipeline de données).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TZ=Europe/Paris
RUN apt-get update && apt-get install -y --no-install-recommends tzdata curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-plateforme.txt ./
RUN pip install -r requirements-plateforme.txt

COPY footpred ./footpred
COPY appui ./appui
COPY plateforme ./plateforme
COPY app.py ./
COPY .streamlit/config.toml ./.streamlit/config.toml
COPY web/data ./web/data
COPY results ./results
COPY docs ./docs

# utilisateur sans privilèges ; seuls /srv/data (données partagées) et /app/data (caches) sont modifiables
RUN useradd --create-home --uid 10001 goalgebra && mkdir -p /srv/data /app/data && chown -R goalgebra:goalgebra /srv/data /app/data
USER goalgebra

EXPOSE 8501 8000
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
