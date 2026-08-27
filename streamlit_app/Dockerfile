FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev \
    libpango-1.0-0 libpangoft2-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhängigkeiten kommen aus dem Lockfile (uv pip compile, hash-gepinnt), damit
# ein Rebuild dieselben Versionen liefert. Neu erzeugen mit:
#   uv pip compile pyproject.toml --python-version 3.12 --generate-hashes -o requirements.lock
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

# Projekt selbst ohne Resolver installieren – die Deps stehen schon.
RUN pip install --no-cache-dir --no-deps -e .

COPY app ./app

# Schema-Migrationen: `alembic upgrade head` laeuft im Container.
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8501

CMD ["streamlit", "run", "app/Home.py", "--server.address=0.0.0.0", "--server.port=8501"]
