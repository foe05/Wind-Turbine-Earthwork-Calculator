FROM python:3.11-slim

# Install GDAL and dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Note: /shared is mounted as a volume in docker-compose.yml

# Expose port
EXPOSE 8003

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
