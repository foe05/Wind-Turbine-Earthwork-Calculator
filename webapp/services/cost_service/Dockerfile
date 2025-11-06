FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Note: /shared is mounted as a volume in docker-compose.yml

# Expose port
EXPOSE 8004

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
