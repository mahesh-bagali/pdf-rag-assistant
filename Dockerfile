
# Use Python 3.12
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY generation.py .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
