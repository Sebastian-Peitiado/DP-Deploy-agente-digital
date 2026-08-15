FROM python:3.11-slim

WORKDIR /app

# Evitar generación de bytecode y forzar logs inmediatos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar utilidades básicas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente de la aplicación
COPY . .

# Exponer el puerto configurado (Render asignará PORT automáticamente)
EXPOSE 8000

# Comando para ejecutar FastAPI con Uvicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
