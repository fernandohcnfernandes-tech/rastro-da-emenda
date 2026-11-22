FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/backend

COPY backend/pyproject.toml ./
COPY backend/rastro ./rastro
RUN pip install .

# docs/ recebe os relatórios gerados pelos jobs (relatórios de CNPJ e da atualização semanal)
RUN mkdir -p /app/docs/relatorios /app/dados
RUN useradd --create-home rastro && chown -R rastro /app
USER rastro

EXPOSE 8000
# Aplica schema e migrações pendentes (idempotente) e sobe a API.
CMD ["sh", "-c", "python -m rastro.db.migrar && uvicorn rastro.api.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers"]
