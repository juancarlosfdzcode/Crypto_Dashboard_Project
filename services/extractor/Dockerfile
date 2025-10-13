FROM python:3.11-slim

WORKDIR /app

# Añadir esta línea:
ENV PYTHONPATH=/app/src

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY src/ ./src/

# Comando por defecto
CMD ["python", "src/cryptoPipeline.py"]